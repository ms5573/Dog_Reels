from celery import Celery
import os
import time
from dotenv import load_dotenv
import sys
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Initialize Celery
redis_url = os.getenv('REDIS_URL', 'redis://localhost:6379/0')
celery = Celery('tasks', broker=redis_url, backend=redis_url)

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
        
        # Create output directory if it doesn't exist
        output_dir = os.path.join(os.getcwd(), "Output")
        os.makedirs(output_dir, exist_ok=True)
        
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