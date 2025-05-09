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
from celery.exceptions import Ignore # Import Ignore
import traceback
import requests
from urllib.parse import urlparse
import shutil
from PIL import Image
import io
import re # For parsing XML endpoint
import boto3 # Add boto3 import
from botocore.exceptions import ClientError # For boto3 error handling

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
            photo_path = None # Will be path to local downloaded file
            final_audio_path_for_generator = None # Will be path to local audio for generator

            # --- PHOTO DOWNLOAD ---
            if photo_url:
                parsed_url = urlparse(photo_url)
                filename = os.path.basename(parsed_url.path)
                if not filename:  # Handle cases like "bucket/" or if path is just "/"
                    timestamp = int(time.time())
                    filename = f"downloaded_photo_{timestamp}" # Add timestamp for uniqueness
                
                _, ext = os.path.splitext(filename)
                if not ext: # Ensure there's an extension
                    # Try to get extension from the photo_url path itself if filename part had none
                    _, url_ext = os.path.splitext(parsed_url.path)
                    if url_ext and len(url_ext) <= 5 : # Basic check for a valid-looking extension
                         filename += url_ext
                    else:
                         filename += ".jpg" # Default if no extension found or looks invalid
                        
                local_photo_file_path = os.path.join(temp_dir, filename)

                if use_s3: # Global flag indicating if S3 URLs should be treated as S3
                    print(f"Attempting S3 download for photo: {photo_url}")
                    aws_region_worker = os.getenv("AWS_REGION")
                    aws_access_key_id_worker = os.getenv("AWS_ACCESS_KEY_ID")
                    aws_secret_access_key_worker = os.getenv("AWS_SECRET_ACCESS_KEY")
                    
                    if not all([aws_region_worker, aws_access_key_id_worker, aws_secret_access_key_worker]):
                        raise ValueError("Worker S3 photo download: AWS credentials/region not configured in worker environment.")

                    s3_bucket_name = None
                    s3_object_key = None

                    if parsed_url.hostname and '.s3.' in parsed_url.hostname: # Standard virtual-hosted style or path-style URL
                        s3_bucket_name = parsed_url.hostname.split('.')[0]
                        s3_object_key = parsed_url.path.lstrip('/')
                    elif parsed_url.scheme == 's3': # s3://bucket/key format
                        s3_bucket_name = parsed_url.netloc
                        s3_object_key = parsed_url.path.lstrip('/')
                    
                    # If bucket name couldn't be reliably parsed from URL (e.g. path-style S3 access, though less common for new buckets)
                    # or if key is empty, this might indicate an issue or a need for S3_BUCKET_NAME env var as a fallback.
                    # For this implementation, we'll rely on bucket being in hostname or s3:// scheme.
                    if not s3_bucket_name and os.getenv("S3_BUCKET_NAME"): # Fallback if needed and available
                        s3_bucket_name = os.getenv("S3_BUCKET_NAME")
                        # In this case, the full photo_url path might be the key
                        if not s3_object_key: s3_object_key = parsed_url.path.lstrip('/')


                    if not s3_bucket_name or not s3_object_key:
                        raise ValueError(f"Could not determine S3 bucket/key for photo URL: {photo_url}")

                    try:
                        s3_client = boto3.client(
                            's3',
                            aws_access_key_id=aws_access_key_id_worker,
                            aws_secret_access_key=aws_secret_access_key_worker,
                            region_name=aws_region_worker
                        )
                        print(f"Downloading s3://{s3_bucket_name}/{s3_object_key} to {local_photo_file_path}")
                        s3_client.download_file(s3_bucket_name, s3_object_key, local_photo_file_path)
                        photo_path = local_photo_file_path
                        print(f"S3 Photo Download successful: {photo_path}")
                    except ClientError as e:
                        print(f"S3 Photo Download Error for {photo_url} (Key: s3://{s3_bucket_name}/{s3_object_key}): {e}")
                        raise
                    except Exception as e:
                        print(f"Unexpected error during S3 photo download setup for {photo_url}: {e}")
                        raise
                else: # Not using S3, assume photo_url is a direct downloadable URL
                    print(f"Attempting direct HTTP download for photo: {photo_url}")
                    try:
                        response = requests.get(photo_url, stream=True, timeout=60)
                        response.raise_for_status()
                        
                        content_type = response.headers.get('Content-Type', '')
                        final_url_accessed = response.url
                        print(f"Direct Photo Download: Status {response.status_code}, Content-Type='{content_type}', Final URL='{final_url_accessed}'")

                        if not content_type.startswith('image/'):
                            # Try to get a preview of the content if it's text-based
                            preview_text = ""
                            try:
                                if "text" in content_type or "xml" in content_type or "json" in content_type :
                                     preview_text = response.text[:200] # Get first 200 chars
                                else:
                                     preview_text = "(binary content)"
                            except Exception:
                                preview_text = "(could not read preview)"
                            raise ValueError(f"Invalid Content-Type '{content_type}' from photo URL {final_url_accessed}. Expected 'image/...'. Preview: {preview_text}")
                        
                        with open(local_photo_file_path, 'wb') as f:
                            for chunk in response.iter_content(chunk_size=8192):
                                f.write(chunk)
                        photo_path = local_photo_file_path
                        print(f"Direct HTTP Photo Download successful: {photo_path}")
                    except requests.exceptions.RequestException as e:
                        print(f"Direct HTTP Photo Download Error for {photo_url}: {e}")
                        raise
            
            if photo_path and os.path.exists(photo_path):
                print(f"Processing downloaded photo: {photo_path}")
                try:
                    # Use an alias for PIL.Image to avoid potential conflicts if Image is used elsewhere
                    from PIL import Image as PILImage, ImageFile as PILImageFile
                    PILImageFile.LOAD_TRUNCATED_IMAGES = True # Allow loading truncated images
                    
                    img = PILImage.open(photo_path)
                    # Convert to RGBA for consistency, save as PNG (OpenAI prefers PNG)
                    png_filename = os.path.splitext(os.path.basename(photo_path))[0] + "_standardized.png"
                    png_path = os.path.join(temp_dir, png_filename)
                    
                    if img.mode != 'RGBA':
                        img = img.convert('RGBA')
                    img.save(png_path, "PNG")
                    photo_path = png_path # Update photo_path to the standardized PNG
                    print(f"Photo standardized to PNG: {photo_path}")
                except Exception as e_img_proc:
                    print(f"Warning: Error processing/converting downloaded photo {photo_path} to PNG: {e_img_proc}. Using original download.")
                    # photo_path remains the initially downloaded file. This might fail later if not a good image.
            
            # --- AUDIO DOWNLOAD ---
            downloaded_audio_file_path = None # Path to the audio file downloaded in this task run
            if audio_url:
                parsed_audio_url = urlparse(audio_url)
                audio_filename = os.path.basename(parsed_audio_url.path)
                if not audio_filename:
                    timestamp = int(time.time())
                    audio_filename = f"downloaded_audio_{timestamp}"

                _, audio_ext = os.path.splitext(audio_filename)
                if not audio_ext: # Ensure it has an extension
                    _, url_audio_ext = os.path.splitext(parsed_audio_url.path)
                    if url_audio_ext and len(url_audio_ext) <=5:
                        audio_filename += url_audio_ext
                    else:
                        audio_filename += ".mp3" # Default audio extension
                        
                local_audio_file_path = os.path.join(temp_dir, audio_filename)

                if use_s3: # Global flag for S3
                    print(f"Attempting S3 download for audio: {audio_url}")
                    aws_region_worker = os.getenv("AWS_REGION")
                    aws_access_key_id_worker = os.getenv("AWS_ACCESS_KEY_ID")
                    aws_secret_access_key_worker = os.getenv("AWS_SECRET_ACCESS_KEY")

                    if not all([aws_region_worker, aws_access_key_id_worker, aws_secret_access_key_worker]):
                        print("Worker S3 audio download: AWS credentials/region not configured. Skipping S3 audio.")
                    else:
                        s3_audio_bucket_name = None
                        s3_audio_object_key = None

                        if parsed_audio_url.hostname and '.s3.' in parsed_audio_url.hostname:
                            s3_audio_bucket_name = parsed_audio_url.hostname.split('.')[0]
                            s3_audio_object_key = parsed_audio_url.path.lstrip('/')
                        elif parsed_audio_url.scheme == 's3':
                            s3_audio_bucket_name = parsed_audio_url.netloc
                            s3_audio_object_key = parsed_audio_url.path.lstrip('/')
                        
                        if not s3_audio_bucket_name and os.getenv("S3_BUCKET_NAME"):
                             s3_audio_bucket_name = os.getenv("S3_BUCKET_NAME")
                             if not s3_audio_object_key: s3_audio_object_key = parsed_audio_url.path.lstrip('/')

                        if not s3_audio_bucket_name or not s3_audio_object_key:
                            print(f"Could not determine S3 bucket/key for audio URL: {audio_url}. Skipping S3 audio.")
                        else:
                            try:
                                s3_client_audio = boto3.client('s3', aws_access_key_id=aws_access_key_id_worker, aws_secret_access_key=aws_secret_access_key_worker, region_name=aws_region_worker)
                                print(f"Downloading s3://{s3_audio_bucket_name}/{s3_audio_object_key} to {local_audio_file_path}")
                                s3_client_audio.download_file(s3_audio_bucket_name, s3_audio_object_key, local_audio_file_path)
                                downloaded_audio_file_path = local_audio_file_path
                                print(f"S3 Audio Download successful: {downloaded_audio_file_path}")
                            except ClientError as e:
                                print(f"S3 Audio Download Error for {audio_url} (Key: s3://{s3_audio_bucket_name}/{s3_audio_object_key}): {e}. Proceeding without this audio.")
                            except Exception as e:
                                print(f"Unexpected error during S3 audio download for {audio_url}: {e}. Proceeding without this audio.")
                else: # Not S3, direct URL for audio
                    print(f"Attempting direct HTTP download for audio: {audio_url}")
                    try:
                        response_audio = requests.get(audio_url, stream=True, timeout=30)
                        response_audio.raise_for_status()
                        # Optionally, add audio content-type check here if strict validation is needed
                        with open(local_audio_file_path, 'wb') as f:
                            for chunk in response_audio.iter_content(chunk_size=8192):
                                f.write(chunk)
                        downloaded_audio_file_path = local_audio_file_path
                        print(f"Direct HTTP Audio Download successful: {downloaded_audio_file_path}")
                    except requests.exceptions.RequestException as e:
                        print(f"Direct HTTP Audio Download Error for {audio_url}: {e}. Proceeding without this audio.")
            
            # Determine final audio_path for the ChibiClipGenerator
            if downloaded_audio_file_path and os.path.exists(downloaded_audio_file_path):
                final_audio_path_for_generator = downloaded_audio_file_path
            elif action == "birthday-dance": # Fallback to default birthday song
                project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
                default_birthday_song_path = os.path.join(project_root, "birthday_song.mp3")
                if os.path.exists(default_birthday_song_path):
                    final_audio_path_for_generator = default_birthday_song_path
                    print(f"Using default birthday song: {final_audio_path_for_generator}")
                else:
                    print("Default birthday_song.mp3 not found. Proceeding without audio.")
            else: # No custom audio downloaded, not birthday-dance action
                print("No custom audio. Proceeding without audio.")
            
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
                audio_path=final_audio_path_for_generator,
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
            
    except ValueError as ve: # Specific handling for ValueErrors (e.g., bad input, non-image file)
        error_message = f"Task process_clip failed due to invalid input or data: {str(ve)}"
        print(error_message)
        print(traceback.format_exc())
        # Update task state to FAILURE and do not retry for ValueErrors
        self.update_state(state='FAILURE', meta={
            'exc_type': type(ve).__name__,
            'exc_message': str(ve),
            'traceback': traceback.format_exc()
        })
        raise Ignore() # Tell Celery to ignore this task, no more retries
    except Exception as exc:
        # Log the error
        print(f"Task process_clip failed with an unexpected exception: {str(exc)}")
        print(traceback.format_exc())
        
        # Retry the task up to 3 times, with exponential backoff for other exceptions
        self.retry(exc=exc, countdown=2 ** self.request.retries) 