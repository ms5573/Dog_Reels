from celery import Celery
import os
import time
from dotenv import load_dotenv
import sys
import logging
import ssl
import shutil

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Initialize Celery with proper SSL configuration for Heroku Redis
redis_url = os.getenv('REDIS_URL', 'redis://localhost:6379/0')
broker_use_ssl = None
redis_backend_use_ssl = None

# Configure SSL if using rediss:// (Redis with SSL)
if redis_url and redis_url.startswith('rediss://'):
    broker_use_ssl = {
        'ssl_cert_reqs': ssl.CERT_NONE
    }
    redis_backend_use_ssl = {
        'ssl_cert_reqs': ssl.CERT_NONE
    }
    logger.info("Configured Redis with SSL settings")

celery = Celery('tasks', 
                broker=redis_url, 
                backend=redis_url,
                broker_use_ssl=broker_use_ssl,
                redis_backend_use_ssl=redis_backend_use_ssl)

# Configure Celery
celery.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
    worker_concurrency=1,  # Using single concurrency to avoid memory issues
    task_time_limit=600,  # 10 minutes max task time
)

@celery.task(bind=True)
def generate_birthday_card(self, photo_path, birthday_message=None):
    logger.info(f"Starting birthday card generation for {photo_path}")
    
    try:
        # Dynamically import here to avoid circular imports
        from .chibi_clip import ChibiClipGenerator
        
        # Create various output directories to ensure they exist
        app_root = os.getcwd()
        logger.info(f"App root directory: {app_root}")
        
        output_dir = os.path.join(app_root, "Output")
        os.makedirs(output_dir, exist_ok=True)
        logger.info(f"Created/verified Output directory: {output_dir}")
        
        tasks_dir = os.path.join(output_dir, "tasks")
        os.makedirs(tasks_dir, exist_ok=True)
        
        # Verify the photo file exists
        if not os.path.exists(photo_path):
            logger.error(f"Photo file not found at {photo_path}")
            
            # Check if the path is relative to the app_root
            if not photo_path.startswith('/'):
                absolute_photo_path = os.path.join(app_root, photo_path)
                logger.info(f"Trying absolute path: {absolute_photo_path}")
                if os.path.exists(absolute_photo_path):
                    photo_path = absolute_photo_path
                    logger.info(f"Using absolute photo path: {photo_path}")
            
            if not os.path.exists(photo_path):
                # File doesn't exist at expected location. Attempt to find the file by name
                filename = os.path.basename(photo_path)
                for root, dirs, files in os.walk(app_root):
                    for file in files:
                        if file == filename:
                            found_path = os.path.join(root, file)
                            logger.info(f"Found file at alternate location: {found_path}")
                            photo_path = found_path
                            break
                    if os.path.exists(photo_path):
                        break
        
        # If we still don't have the file, we can't proceed
        if not os.path.exists(photo_path):
            raise FileNotFoundError(f"Could not find the photo file: {photo_path}")
        
        # Initialize generator
        generator = ChibiClipGenerator(
            openai_api_key=os.getenv('OPENAI_API_KEY'),
            imgbb_api_key=os.getenv('IMGBB_API_KEY'),
            runway_api_key=os.getenv('RUNWAY_API_KEY'),
            verbose=True,
            output_dir=output_dir
        )
        
        # Update task state
        self.update_state(state="PROCESSING", meta={'stage': 'Initialized generator'})
        
        # Generate the clip
        result = generator.process_clip(
            photo_path=photo_path,
            action="birthday-dance",
            birthday_message=birthday_message,
            use_local_storage=True,  # Force local storage on Heroku
            extended_duration=45
        )
        
        logger.info(f"Birthday card generation complete: {result}")
        return result
        
    except Exception as e:
        logger.error(f"Error generating birthday card: {str(e)}", exc_info=True)
        raise

if __name__ == "__main__":
    # For direct execution as a worker
    logger.info("Starting Celery worker")
    argv = [
        'worker',
        '--loglevel=info',
        '-n', 'birthday_worker@%h'
    ]
    celery.worker_main(argv) 