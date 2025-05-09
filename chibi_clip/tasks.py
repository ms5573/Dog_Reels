"""
Background task processing using Celery.
This module handles moving the video generation process to background workers.

Note: This worker has been modified to support distributed deployment with Render.com
It downloads files from S3 URLs before processing, and uploads results back to S3.
"""

import os
import time
import tempfile
from celery import Celery
import traceback
import requests
from urllib.parse import urlparse
import shutil
from PIL import Image
import io

# Try to import magic but don't fail if it's not available
try:
    import magic
    MAGIC_AVAILABLE = True
except ImportError:
    print("Warning: python-magic or libmagic is not available. File type detection will be limited.")
    MAGIC_AVAILABLE = False

# Try to import subprocess for file command but don't fail if it's not available
try:
    import subprocess
    SUBPROCESS_AVAILABLE = True
except ImportError:
    print("Warning: subprocess module is not available. File command will not be used.")
    SUBPROCESS_AVAILABLE = False

# Load environment variables for Celery
from dotenv import load_dotenv
load_dotenv()

# Initialize Celery
redis_url = os.environ.get('REDIS_URL', 'redis://localhost:6379/0')
print(f"Worker initializing with Redis URL: {redis_url}")
app = Celery('chibi_clip', broker=redis_url, backend=redis_url)

# Verify Redis connection
try:
    # Force a connection check
    app.backend.client.ping()
    print("Successfully connected to Redis backend")
except Exception as e:
    print(f"WARNING: Redis connection check failed: {e}")

# Configure Celery
app.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
)

# Import generator here to avoid circular imports
from .chibi_clip import ChibiClipGenerator
# Import S3 storage
from .storage import S3Storage

# Initialize the generator with env variables
openai_key = os.getenv("OPENAI_API_KEY")
imgbb_key = os.getenv("IMGBB_API_KEY")
runway_key = os.getenv("RUNWAY_API_KEY")

# Determine if we should use S3 storage
use_s3 = os.getenv('USE_S3_STORAGE', 'false').lower() == 'true'

# Set up output directory
output_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "Output")
os.makedirs(output_dir, exist_ok=True)

# Register tasks explicitly
# Create a unique task name that will be consistent across services
@app.task(bind=True, max_retries=3, name='chibi_clip.tasks.process_clip')
def process_clip(self, photo_url, audio_url=None, action="running", ratio="9:16", duration=5, 
                extended_duration=45, use_local_storage=False, birthday_message=None):
    """
    Celery task to process a video clip in the background.
    
    Args:
        photo_url: S3 URL to the photo
        audio_url: S3 URL to the audio file (optional)
        action: Animation action to use
        ratio: Aspect ratio for the video
        duration: Duration of the video in seconds
        extended_duration: Duration of extended video
        use_local_storage: Whether to use local storage instead of ImgBB
        birthday_message: Optional text to add to video
        
    Returns:
        Dictionary with paths and URLs to the generated content
    """
    # Add debug logging at task start
    print(f"DEBUG: Task received with ID: {self.request.id}")
    print(f"DEBUG: Task parameters - photo_url={photo_url}, audio_url={audio_url}")
    print(f"DEBUG: Redis URL: {os.environ.get('REDIS_URL')}")
    print(f"DEBUG: S3 storage enabled: {use_s3}")
    
    try:
        # Create a temporary directory for processing
        with tempfile.TemporaryDirectory() as temp_dir:
            # Download photo from S3
            photo_path = None
            if photo_url:
                try:
                    # Extract filename from URL
                    parsed_url = urlparse(photo_url)
                    filename = os.path.basename(parsed_url.path)
                    photo_path = os.path.join(temp_dir, filename)
                    
                    # Download the file
                    response = requests.get(photo_url, stream=True)
                    response.raise_for_status()
                    
                    # Check content type and headers
                    content_type = response.headers.get('Content-Type', '')
                    content_length = response.headers.get('Content-Length', 'unknown')
                    print(f"S3 response headers: Content-Type={content_type}, Content-Length={content_length}")
                    
                    # Check if content type suggests this is actually an image
                    if not content_type.startswith('image/'):
                        print(f"Warning: Content-Type '{content_type}' may not be an image")
                    
                    # First save the raw downloaded file
                    raw_bytes = b''
                    download_success = False
                    file_size = 0
                    
                    # Try multiple download methods if needed
                    for download_attempt in range(3):  # Try up to 3 different methods
                        try:
                            if download_attempt == 0:
                                # Method 1: Stream with requests
                                print(f"Download attempt {download_attempt+1}: Using requests.iter_content")
                                with open(photo_path, 'wb') as f:
                                    for chunk in response.iter_content(chunk_size=8192):
                                        f.write(chunk)
                                        # Save first chunk for debugging
                                        if not raw_bytes:
                                            raw_bytes = chunk[:32]  # First 32 bytes for magic number checking
                            elif download_attempt == 1:
                                # Method 2: Direct requests content
                                print(f"Download attempt {download_attempt+1}: Using requests.content directly")
                                response = requests.get(photo_url)
                                with open(photo_path, 'wb') as f:
                                    f.write(response.content)
                                if not raw_bytes and response.content:
                                    raw_bytes = response.content[:32]
                            else:
                                # Method 3: urllib
                                print(f"Download attempt {download_attempt+1}: Using urllib")
                                import urllib.request
                                urllib.request.urlretrieve(photo_url, photo_path)
                                with open(photo_path, 'rb') as f:
                                    first_bytes = f.read(32)
                                    if first_bytes and not raw_bytes:
                                        raw_bytes = first_bytes
                            
                            # Check if file exists and has size
                            if os.path.exists(photo_path) and os.path.getsize(photo_path) > 0:
                                file_size = os.path.getsize(photo_path)
                                print(f"Downloaded file size: {file_size} bytes")
                                download_success = True
                                break  # Success, exit the loop
                            else:
                                print(f"Download attempt {download_attempt+1} resulted in empty file")
                        except Exception as download_error:
                            print(f"Download attempt {download_attempt+1} failed: {download_error}")
                    
                    if not download_success:
                        raise ValueError(f"All download attempts failed for {photo_url}")
                    
                    if raw_bytes:
                        print(f"Downloaded file header bytes: {raw_bytes.hex()}")
                    
                    # Verify file type and convert if needed
                    file_type_verified = False
                    
                    # Try various methods to verify and convert if needed
                    try:
                        # Method 1: Try PIL directly
                        try:
                            from PIL import Image, ImageFile
                            # Allow loading truncated images
                            ImageFile.LOAD_TRUNCATED_IMAGES = True
                            
                            with Image.open(photo_path) as img:
                                img_format = img.format
                                img_mode = img.mode
                                img_size = img.size
                                print(f"Successfully verified image with PIL: format={img_format}, mode={img_mode}, size={img_size}")
                                
                                # If format is unexpected, convert to PNG
                                if img_format not in ('JPEG', 'PNG'):
                                    print(f"Converting {img_format} to PNG for better compatibility")
                                    png_path = os.path.join(temp_dir, "photo_verified.png")
                                    img = img.convert('RGBA' if img_mode != 'RGBA' else img_mode)
                                    img.save(png_path, format="PNG")
                                    if os.path.exists(png_path) and os.path.getsize(png_path) > 0:
                                        photo_path = png_path
                                        print(f"Converted to PNG: {photo_path}")
                                
                                file_type_verified = True
                        except Exception as pil_error:
                            print(f"PIL verification failed: {pil_error}")
                            
                            # Method 2: Try magic if available
                            if MAGIC_AVAILABLE:
                                try:
                                    mime = magic.Magic(mime=True)
                                    detected_type = mime.from_file(photo_path)
                                    print(f"Detected MIME type: {detected_type}")
                                    
                                    if detected_type.startswith('image/'):
                                        file_type_verified = True
                                    else:
                                        print(f"File doesn't appear to be an image. Detected as: {detected_type}")
                                except Exception as magic_error:
                                    print(f"Magic verification failed: {magic_error}")
                            
                            # Method 3: Try file command if available
                            if SUBPROCESS_AVAILABLE and not file_type_verified:
                                try:
                                    result = subprocess.run(['file', photo_path], capture_output=True, text=True)
                                    output = result.stdout
                                    print(f"File command output: {output}")
                                    
                                    # Check if output suggests it's an image
                                    if any(img_type in output.lower() for img_type in ['image', 'png', 'jpeg', 'jpg']):
                                        file_type_verified = True
                                    else:
                                        print("File command doesn't recognize this as an image")
                                except Exception as file_cmd_error:
                                    print(f"File command verification failed: {file_cmd_error}")
                            
                    except Exception as verify_error:
                        print(f"Error during file verification: {verify_error}")
                    
                    # Final check - if we couldn't verify, but file exists and has decent size, proceed with caution
                    if not file_type_verified and file_size > 100:  # Arbitrary minimum size
                        print("Warning: Could not verify file type, but proceeding with caution")
                    elif not file_type_verified:
                        raise ValueError(f"Could not verify that downloaded file is a valid image: {photo_path}")
                    
                    # Ensure it's a valid PNG for OpenAI by converting with Pillow
                    try:
                        # Create a standardized PNG version
                        png_path = os.path.join(temp_dir, "photo_standardized.png")
                        
                        # Open with explicit error handling
                        try:
                            img = Image.open(photo_path)
                            print(f"Original image format: {img.format}, mode: {img.mode}, size: {img.size}")
                        except Exception as img_error:
                            print(f"Failed to open image file: {img_error}")
                            # Try to debug the file content
                            with open(photo_path, 'rb') as f:
                                file_start = f.read(20)  # Read first 20 bytes
                                print(f"File header bytes: {file_start.hex()}")
                            raise
                        
                        # Convert to RGB or RGBA mode
                        if img.mode != 'RGBA':
                            img = img.convert('RGBA')
                        
                        # Save with explicit format
                        img.save(png_path, format="PNG")
                        
                        # Verify the converted file
                        if os.path.exists(png_path) and os.path.getsize(png_path) > 0:
                            # Additional verification by reopening
                            verify_img = Image.open(png_path)
                            print(f"Converted PNG format: {verify_img.format}, mode: {verify_img.mode}, size: {verify_img.size}")
                            verify_img.close()
                            
                            # Replace original path with standardized version
                            photo_path = png_path
                            print(f"Converted image to standardized PNG format: {photo_path}")
                        else:
                            print(f"Warning: Converted PNG file is empty or missing: {png_path}")
                            # Continue with original file
                    except Exception as e:
                        print(f"Error converting image to PNG: {e}")
                        print(traceback.format_exc())
                        # Continue with original file if conversion fails
                    
                    print(f"Downloaded photo from S3: {photo_url} to {photo_path}")
                except Exception as e:
                    print(f"Error downloading photo from S3: {e}")
                    raise
            
            # Download audio from S3 if provided
            audio_path = None
            if audio_url:
                try:
                    # Extract filename from URL
                    parsed_url = urlparse(audio_url)
                    filename = os.path.basename(parsed_url.path)
                    audio_path = os.path.join(temp_dir, filename)
                    
                    # Download the file
                    response = requests.get(audio_url, stream=True)
                    response.raise_for_status()
                    with open(audio_path, 'wb') as f:
                        for chunk in response.iter_content(chunk_size=8192):
                            f.write(chunk)
                    print(f"Downloaded audio from S3: {audio_url} to {audio_path}")
                except Exception as e:
                    print(f"Error downloading audio from S3: {e}")
                    # Continue without audio if download fails
            elif action == "birthday-dance":
                # Use default birthday song from the project
                project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
                audio_path = os.path.join(project_root, "birthday_song.mp3")
                if not os.path.exists(audio_path):
                    print("Default birthday_song.mp3 not found")
            
            if not photo_path:
                raise ValueError("No photo path available for processing")
                
            # Initialize the generator
            generator = ChibiClipGenerator(
                openai_api_key=openai_key,
                imgbb_api_key=imgbb_key,
                runway_api_key=runway_key,
                verbose=True,
                output_dir=output_dir
            )
            
            # Initialize S3 storage
            s3_storage = None
            if use_s3:
                try:
                    s3_storage = S3Storage()
                    print("S3 storage initialized successfully")
                except Exception as e:
                    print(f"Error initializing S3 storage: {e}")
            
            # Process the clip with downloaded files
            result = generator.process_clip(
                photo_path=photo_path,
                action=action,
                ratio=ratio,
                duration=duration,
                audio_path=audio_path,
                extended_duration=extended_duration,
                use_local_storage=True,  # Always use local storage in processing
                birthday_message=birthday_message
            )
            
            # If S3 is enabled, upload the generated files
            if s3_storage:
                print("Uploading output files to S3...")
                
                # Upload the generated image if available
                if "local_image_path" in result:
                    try:
                        # Upload image to S3
                        s3_image_url, s3_image_key = s3_storage.upload_file(
                            result["local_image_path"], 
                            key_prefix="images"
                        )
                        # Update result with S3 URL
                        result["image_url"] = s3_image_url
                        result["s3_image_key"] = s3_image_key
                        print(f"Uploaded image to S3: {s3_image_url}")
                    except Exception as e:
                        print(f"Error uploading image to S3: {e}")
                
                # Upload the generated video if available
                if "local_video_path" in result:
                    try:
                        # Upload video to S3
                        s3_video_url, s3_video_key = s3_storage.upload_file(
                            result["local_video_path"], 
                            key_prefix="videos"
                        )
                        # Update result with S3 URL
                        result["video_url"] = s3_video_url
                        result["s3_video_key"] = s3_video_key
                        print(f"Uploaded video to S3: {s3_video_url}")
                    except Exception as e:
                        print(f"Error uploading video to S3: {e}")
            
            return result
            
    except Exception as exc:
        # Log the error
        print(f"Task process_clip failed: {str(exc)}")
        print(traceback.format_exc())
        
        # Retry the task up to 3 times, with exponential backoff
        self.retry(exc=exc, countdown=2 ** self.request.retries) 