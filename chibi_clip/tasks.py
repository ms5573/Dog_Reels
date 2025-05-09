"""
Background task processing using Celery.
This module handles moving the video generation process to background workers.
"""

import os
import time
import tempfile
from celery import Celery
import traceback
import shutil

# Load environment variables for Celery
from dotenv import load_dotenv
load_dotenv()

# Initialize Celery
redis_url = os.environ.get('REDIS_URL', 'redis://localhost:6379/0')
app = Celery('chibi_clip', broker=redis_url, backend=redis_url)

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

# Task to process a video clip
@app.task(bind=True, max_retries=3, name="process_clip")
def process_clip(self, photo_path, action="running", ratio="9:16", duration=5, 
                audio_path=None, extended_duration=45, use_local_storage=False, 
                birthday_message=None):
    """
    Celery task to process a video clip in the background.
    
    Args:
        photo_path: Path to the photo file
        action: Animation action to use
        ratio: Aspect ratio for the video
        duration: Duration of the video in seconds
        audio_path: Path to audio file (optional)
        extended_duration: Duration of extended video
        use_local_storage: Whether to use local storage instead of ImgBB
        birthday_message: Optional text to add to video
        
    Returns:
        Dictionary with paths and URLs to the generated content
    """
    try:
        # Initialize the generator
        generator = ChibiClipGenerator(
            openai_api_key=openai_key,
            imgbb_api_key=imgbb_key,
            runway_api_key=runway_key,
            verbose=True,
            output_dir=output_dir
        )
        
        # Initialize S3 storage if enabled
        s3_storage = None
        if use_s3:
            try:
                s3_storage = S3Storage()
                print("S3 storage initialized successfully")
            except Exception as e:
                print(f"Error initializing S3 storage: {e}")
                # Continue without S3 storage
        
        # Process the clip
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