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
                    
                    # First save the raw downloaded file
                    with open(photo_path, 'wb') as f:
                        for chunk in response.iter_content(chunk_size=8192):
                            f.write(chunk)
                    
                    # Ensure it's a valid PNG for OpenAI by converting with Pillow
                    try:
                        # Create a standardized PNG version
                        png_path = os.path.join(temp_dir, "photo_standardized.png")
                        with Image.open(photo_path) as img:
                            # Convert to RGB or RGBA mode
                            if img.mode != 'RGBA':
                                img = img.convert('RGBA')
                            img.save(png_path, format="PNG")
                        
                        # Replace original path with standardized version
                        photo_path = png_path
                        print(f"Converted image to standardized PNG format: {photo_path}")
                    except Exception as e:
                        print(f"Error converting image to PNG: {e}")
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