import os
import requests
import json
import time
import base64
from io import BytesIO
import argparse
import cloudinary
import cloudinary.uploader
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail
import tempfile
import redis
import sys
import traceback
import logging # Import standard logging

# Attempt to import ChibiClipGenerator
try:
    from chibi_clip.chibi_clip import ChibiClipGenerator
    CHIBI_GENERATOR_AVAILABLE = True
    logging.info("Successfully imported ChibiClipGenerator.")
except ImportError as e:
    CHIBI_GENERATOR_AVAILABLE = False
    logging.error(f"Failed to import ChibiClipGenerator: {e}. Birthday card functionality will be limited.")

# Configure logging for the worker
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class ProductMarketingAutomation:
    def __init__(self, openai_api_key=None, imgbb_api_key=None, runway_api_key=None, cloudinary_cloud_name=None, cloudinary_api_key=None, cloudinary_api_secret=None, sendgrid_api_key=None):
        """
        Initialize with API keys or load from environment variables if not provided
        """
        # Load API keys from environment variables if not provided
        self.openai_api_key = openai_api_key or os.environ.get("OPENAI_API_KEY")
        self.imgbb_api_key = imgbb_api_key or os.environ.get("IMGBB_API_KEY")
        self.runway_api_key = runway_api_key or os.environ.get("RUNWAY_API_KEY")
        
        self.cloudinary_cloud_name = cloudinary_cloud_name or os.environ.get("CLOUDINARY_CLOUD_NAME")
        self.cloudinary_api_key = cloudinary_api_key or os.environ.get("CLOUDINARY_API_KEY")
        self.cloudinary_api_secret = cloudinary_api_secret or os.environ.get("CLOUDINARY_API_SECRET")
        self.sendgrid_api_key = sendgrid_api_key or os.environ.get("SENDGRID_API_KEY")

        # Check for required credentials
        if not self.openai_api_key:
            raise ValueError("OpenAI API key is required")
        if not self.runway_api_key:
            raise ValueError("Runway API key is required")
        
        if not (self.cloudinary_cloud_name and self.cloudinary_api_key and self.cloudinary_api_secret):
            logger.warning("Cloudinary credentials not fully set. Video upload to Cloudinary will be disabled.")
            self.cloudinary_enabled = False
        else:
            self.cloudinary_enabled = True
            # Ensure Cloudinary config is robust, consider CLOUDINARY_URL first if available
            try:
                cloudinary_url = os.getenv('CLOUDINARY_URL')
                if cloudinary_url:
                    logger.info("Configuring Cloudinary using CLOUDINARY_URL.")
                    cloudinary.config(cloudinary_url=cloudinary_url, secure=True)
                else:
                    logger.info("CLOUDINARY_URL not found, configuring Cloudinary using individual variables.")
                    cloudinary.config( 
                        cloud_name = self.cloudinary_cloud_name, 
                        api_key = self.cloudinary_api_key, 
                        api_secret = self.cloudinary_api_secret,
                        secure = True
                    )
                logger.info(f"Cloudinary configured. Cloud name: {cloudinary.config().cloud_name}")
            except Exception as e:
                logger.error(f"Error configuring Cloudinary: {e}")
                self.cloudinary_enabled = False


        if not self.sendgrid_api_key:
            logger.warning("SendGrid API key not set. Email notifications will be disabled.")
            self.sendgrid_enabled = False
        else:
            self.sendgrid_enabled = True
            logger.info("SendGrid configured.")
        
        # Initialize ChibiClipGenerator if available
        self.chibi_generator = None
        self.output_dir_worker = None
        self.chibi_generator_initialized_successfully = False # Instance flag
        if CHIBI_GENERATOR_AVAILABLE:
            try:
                self.output_dir_worker = tempfile.mkdtemp(prefix="chibi_worker_")
                self.chibi_generator = ChibiClipGenerator(
                    openai_api_key=self.openai_api_key,
                    imgbb_api_key=self.imgbb_api_key, 
                    runway_api_key=self.runway_api_key,
                    verbose=True, 
                    output_dir=self.output_dir_worker
                )
                logger.info(f"ChibiClipGenerator initialized successfully in {self.output_dir_worker}")
                self.chibi_generator_initialized_successfully = True
            except Exception as e:
                logger.error(f"Error initializing ChibiClipGenerator: {e}. Birthday card features may not work.")
                # self.chibi_generator_initialized_successfully remains False
                if self.output_dir_worker and os.path.exists(self.output_dir_worker):
                    # Clean up temp dir if generator init failed
                    try:
                        import shutil
                        shutil.rmtree(self.output_dir_worker)
                    except Exception as e_clean:
                        logger.error(f"Error cleaning up worker temp dir after ChibiClipGenerator init failure: {e_clean}")
                self.output_dir_worker = None # Reset so it's not used later

    def generate_ai_prompt(self, product_title, product_description):
        """
        Generate creative prompt using OpenAI - now returns a fixed style prompt.
        """
        print(f"Generating fixed style AI prompt (product: {product_title})") 
        style_prompt = "Charming vector illustration of a chibi-style dog with flat pastel, bold black outlines, subtle cel-shading and natural soft shadows, centered on a clean light-beige background with a faint oval ground shadow, minimalistic and playful design."
        return style_prompt

    def upload_to_cloudinary(self, local_video_path, public_id=None, folder="dog_reels_videos"):
        if not self.cloudinary_enabled:
            print("Cloudinary is not enabled. Skipping upload.")
            return None
        try:
            print(f"Uploading {local_video_path} to Cloudinary in folder {folder}...")
            response = cloudinary.uploader.upload(
                local_video_path,
                resource_type="video",
                public_id=public_id, # Can be filename without extension
                folder=folder,
                overwrite=True,
                # Example of eager transformation for web-friendly version, optional
                # eager=[
                #    {"width": 640, "height": 360, "crop": "limit", "format": "mp4"},
                #    {"width": 320, "height": 180, "crop": "limit", "format": "webm"}
                # ]
            )
            print(f"Cloudinary upload successful. Secure URL: {response.get('secure_url')}")
            return response.get('secure_url')
        except Exception as e:
            print(f"Error uploading to Cloudinary: {e}")
            return None

    def edit_image_with_openai(self, image_content, prompt, max_retries=3, retry_delay=5):
        """
        Use OpenAI's image editing API with retry logic for handling temporary failures
        """
        print("Editing image with OpenAI")
        headers = {
            "Authorization": f"Bearer {self.openai_api_key}"
        }
        
        if isinstance(image_content, BytesIO):
            image_bytes = image_content.getvalue()
        else:
            image_bytes = image_content
            
        files = {
            'image': ('image.png', image_bytes, 'image/png'),
            'prompt': (None, prompt),
            'model': (None, 'gpt-image-1')
        }
        
        for attempt in range(max_retries):
            try:
                print(f"OpenAI API attempt {attempt + 1}/{max_retries}")
                response = requests.post("https://api.openai.com/v1/images/edits", headers=headers, files=files)
                response.raise_for_status()
                print("Image successfully edited with OpenAI")
                return response.json()["data"][0]["b64_json"]
            except requests.exceptions.RequestException as e:
                print(f"Error on attempt {attempt + 1}: {e}")
                if hasattr(e, 'response') and e.response and e.response.text:
                    print(f"Response error: {e.response.text}")
                
                # Check if we should retry
                if attempt < max_retries - 1:
                    retry_seconds = retry_delay * (2 ** attempt)  # Exponential backoff
                    print(f"Retrying in {retry_seconds} seconds...")
                    time.sleep(retry_seconds)
                else:
                    print(f"Failed after {max_retries} attempts")
                    raise
    
    def upload_to_imgbb(self, image_base64):
        """
        Upload image to ImgBB hosting (can be kept as a fallback or for intermediate images)
        """
        if not self.imgbb_api_key:
            print("ImgBB API key not provided. Skipping ImgBB upload.")
            return None # Or raise an error if ImgBB is critical for a step

        print("Uploading image to ImgBB")
        url = "https://api.imgbb.com/1/upload"
        payload = {
            'key': self.imgbb_api_key,
            'image': image_base64
        }
        
        try:
            response = requests.post(url, data=payload)
            response.raise_for_status()
            image_url = response.json()["data"]["url"]
            print(f"Image uploaded to ImgBB: {image_url}")
            return image_url
        except requests.exceptions.RequestException as e:
            print(f"Error uploading to ImgBB: {e}")
            if hasattr(e, 'response') and e.response and e.response.text:
                print(f"Response error: {e.response.text}")
            # Decide if this should raise or return None
            return None 
    
    def generate_runway_video(self, image_url):
        """
        Generate video from image using Runway API
        """
        print("Generating video with Runway")
        headers = {
            "Authorization": f"Bearer {self.runway_api_key}",
            "X-Runway-Version": "2024-11-06", # Check if this version is current
            "Content-Type": "application/json"
        }
        
        payload = {
            "promptImage": image_url,
            "model": "gen4_turbo", # Check if this model is current
            "promptText": "Seamless looped 2D animation of the chibi-style spaniel-mix puppy running in place—flat pastel orange and cream fur with bold black outlines, teal collar, smooth leg and ear motion, subtle cel-shading, on a clean light-beige background with a soft oval ground shadow, minimalistic children's storybook style, continuous playful motion without cuts or zooms.",
            "duration": 5,
            "ratio": "960:960" # Consider if this ratio is always desired
        }
        
        try:
            response = requests.post("https://api.dev.runwayml.com/v1/image_to_video", headers=headers, json=payload)
            response.raise_for_status()
            task_id = response.json()["id"]
            print(f"Video generation started with task ID: {task_id}")
            return task_id
        except requests.exceptions.RequestException as e:
            print(f"Error starting Runway video generation: {e}")
            if hasattr(e, 'response') and e.response and e.response.text:
                print(f"Response error: {e.response.text}")
            raise
    
    def check_runway_task_status(self, task_id):
        """
        Check status of Runway video generation task
        """
        headers = {
            "Authorization": f"Bearer {self.runway_api_key}",
            "X-Runway-Version": "2024-11-06" # Match version from generate_runway_video
        }
        
        url = f"https://api.dev.runwayml.com/v1/tasks/{task_id}"
        try:
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"Error checking Runway task status: {e}")
            raise
    
    def wait_for_runway_video(self, task_id, initial_wait=60, poll_interval=10, max_attempts=30):
        """
        Poll Runway API until video is ready, with configurable waits and error handling
        """
        print(f"Waiting {initial_wait} seconds before first Runway status check...")
        time.sleep(initial_wait)
        
        attempts = 0
        consecutive_errors = 0
        max_consecutive_errors = 3
        
        while attempts < max_attempts:
            attempts += 1
            try:
                print(f"Checking Runway video status (attempt {attempts}/{max_attempts})...")
                
                task_status = self.check_runway_task_status(task_id)
                consecutive_errors = 0  # Reset error counter on successful API call
                status = task_status.get("status")
                
                if status == "COMPLETED" or status == "SUCCEEDED": # Handle both success states
                    print(f"Runway video generation {status} after {attempts} checks!")
                    return task_status
                elif status == "FAILED":
                    error_message = task_status.get('error', 'Unknown error')
                    print(f"Runway video generation failed: {error_message}")
                    raise Exception(f"Runway video generation failed: {error_message}")
                elif status in ["RUNNING", "PENDING"]:
                    print(f"Runway video still generating (status: {status}). Waiting {poll_interval} seconds...")
                    time.sleep(poll_interval)
                else: # Handle unexpected statuses
                    print(f"Runway video: Unknown status '{status}'. Raw: {task_status}. Waiting {poll_interval} seconds...")
                    time.sleep(poll_interval)
                    
            except Exception as e:
                consecutive_errors += 1
                print(f"Error checking Runway status (attempt {attempts}, consecutive errors: {consecutive_errors}): {e}")
                
                if consecutive_errors >= max_consecutive_errors:
                    print(f"Too many consecutive errors ({consecutive_errors}). Giving up.")
                    raise Exception(f"Failed to check Runway video status after {consecutive_errors} consecutive errors")
                    
                # Use exponential backoff for retry delay
                retry_seconds = poll_interval * (2 ** (consecutive_errors - 1))
                print(f"Will retry in {retry_seconds} seconds...")
                time.sleep(retry_seconds)
        
        print(f"Runway video generation timed out after {max_attempts} attempts.")
        raise Exception(f"Runway video generation timed out after {max_attempts} attempts")
    
    def send_video_email(self, to_email, product_title, cloudinary_video_url):
        """
        Send an email with the video link using SendGrid API
        """
        if not self.sendgrid_enabled or not self.sendgrid_api_key:
            print("SendGrid is not enabled. Skipping email notification.")
            return False
            
        try:
            print(f"Sending video email to {to_email}")
            
            html_content = f"""
            <html>
                <head>
                    <title>Your Dog Birthday Card is Ready!</title>
                </head>
                <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px; color: #333;">
                    <div style="text-align: center; background-color: #f9f0ff; padding: 20px; border-radius: 10px;">
                        <h1 style="color: #8a2be2;">Your Dog Birthday Card is Ready! 🎉</h1>
                        <p style="font-size: 16px; line-height: 1.5;">We've created a special birthday video for your dog!</p>
                        
                        <div style="margin: 25px 0;">
                            <a href="{cloudinary_video_url}" style="background-color: #8a2be2; color: white; padding: 12px 24px; text-decoration: none; border-radius: 5px; font-weight: bold;">Watch Your Video</a>
                        </div>
                        
                        <p style="font-size: 14px; color: #666;">The link will be available for 7 days. Don't forget to download your video!</p>
                        
                        <div style="margin-top: 30px; padding-top: 20px; border-top: 1px solid #ddd; font-size: 12px; color: #888;">
                            <p>Thank you for using our Dog Birthday Card Generator!</p>
                        </div>
                    </div>
                </body>
            </html>
            """
            
            message = Mail(
                from_email='dogreel-noreply@example.com',
                to_emails=to_email,
                subject=f'Your Dog Birthday Card is Ready! 🎂🐶',
                html_content=html_content
            )
            
            sg = SendGridAPIClient(self.sendgrid_api_key)
            response = sg.send(message)
            
            print(f"Email sent successfully! Status code: {response.status_code}")
            return True
        except Exception as e:
            print(f"Error sending email: {e}")
            return False

    def download_image_from_url(self, image_url):
        """
        Download an image from a URL and return the content as bytes
        """
        try:
            logger.info(f"Downloading image from remote URL: {image_url}")
            response = requests.get(image_url, stream=True)
            response.raise_for_status()  # Raise an exception for HTTP errors
            
            # Create a temporary file to save the image
            # Suffix helps identify file type but isn't strictly necessary for tempfile
            temp_image_file = tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") 
            temp_path = temp_image_file.name
            
            with open(temp_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            
            logger.info(f"Image downloaded to temporary path: {temp_path}")
            return temp_path
        except requests.exceptions.RequestException as e:
            logger.error(f"Error downloading image from URL {image_url}: {e}")
            if hasattr(e, 'response') and e.response is not None:
                logger.error(f"Response status: {e.response.status_code}, Response text: {e.response.text}")
            raise
        except Exception as e: # Catch other potential errors
            logger.error(f"Unexpected error downloading image from URL {image_url}: {e}")
            raise

    def process_product(self, product_photo_path, product_title, product_description, user_email=None,
                   upload_to_drive=False, folder_id=None, is_url=False):
        """
        Process a product through the complete workflow.
        If CHIBI_GENERATOR_AVAILABLE and product_title is "Dog Birthday Card", uses ChibiClipGenerator.
        Otherwise, uses a generic product marketing video flow.
        """
        logger.info(f"\n=== Starting process for: '{product_title}' for user '{user_email}' (URL: {is_url}) ===\n")
        results = {"product_title": product_title}
        temp_downloaded_image_path = None # Path for image downloaded from URL
        final_video_local_path = None # Path for the final video to be uploaded

        try:
            # Step 1: Get local image path (download if URL, or use directly if local path)
            if is_url:
                temp_downloaded_image_path = self.download_image_from_url(product_photo_path)
                current_image_path = temp_downloaded_image_path
            else:
                current_image_path = product_photo_path # Assuming it's a local path already
            
            if not current_image_path or not os.path.exists(current_image_path):
                raise FileNotFoundError(f"Source image path not found or invalid: {current_image_path}")

            # Use CHIBI_GENERATOR_AVAILABLE (module-level import check) 
            # AND self.chibi_generator_initialized_successfully (instance-level init check)
            if CHIBI_GENERATOR_AVAILABLE and self.chibi_generator_initialized_successfully and product_title == "Dog Birthday Card":
                logger.info("Using ChibiClipGenerator for Dog Birthday Card.")
                
                # ChibiClipGenerator's process_clip expects a photo_path and birthday_message.
                # It handles OpenAI editing, Runway animation, music, looping, and card slate internally.
                chibi_result = self.chibi_generator.process_clip(
                    photo_path=current_image_path,
                    action="birthday-dance", # Hardcoded for this flow
                    birthday_message=product_description, # User's message
                    # extended_duration=45 # This is default in process_clip for birthday-dance
                    # use_local_storage=True # process_clip handles its own local storage via output_dir
                )
                
                if not chibi_result or not chibi_result.get('final_video_path'):
                    raise Exception("ChibiClipGenerator did not return the final video path.")
                
                final_video_local_path = chibi_result['final_video_path']
                results["chibi_generator_result"] = chibi_result # Store intermediate results if any
                logger.info(f"ChibiClipGenerator processing complete. Final video at: {final_video_local_path}")
                # Note: ChibiClipGenerator saves to its own output_dir (self.output_dir_worker)
                # We don't assign chibi_temp_dir_to_clean here as self.output_dir_worker is cleaned up at __init__ failure or could be cleaned later.

            else:
                logger.info("Using generic product marketing video flow.")
                if not (CHIBI_GENERATOR_AVAILABLE and self.chibi_generator_initialized_successfully) and product_title == "Dog Birthday Card":
                    logger.warning("ChibiClipGenerator import or initialization failed. 'Dog Birthday Card' will be processed with generic flow.")
                elif not CHIBI_GENERATOR_AVAILABLE and product_title == "Dog Birthday Card":
                    logger.warning("ChibiClipGenerator module not imported. 'Dog Birthday Card' will be generic.")
                elif not self.chibi_generator_initialized_successfully and product_title == "Dog Birthday Card":
                    logger.warning("ChibiClipGenerator instance not initialized. 'Dog Birthday Card' will be generic.")

                # Generic Flow (Original logic)
                ai_prompt = self.generate_ai_prompt(product_title, product_description)
                results["ai_prompt"] = ai_prompt
                logger.info(f"Generated AI editing prompt: {ai_prompt[:100]}...")

                with open(current_image_path, 'rb') as f:
                    image_content_bytes = f.read()
                
                edited_image_b64 = None
                try:
                    edited_image_b64 = self.edit_image_with_openai(image_content_bytes, ai_prompt)
                except Exception as e:
                    logger.error(f"Failed to edit image with OpenAI after retries: {e}")
                    logger.warning("Using original image as fallback for generic flow...")
                    edited_image_b64 = base64.b64encode(image_content_bytes).decode('utf-8')
                
                img_url_for_runway = self.upload_to_imgbb(edited_image_b64)
                if not img_url_for_runway:
                    raise Exception("Failed to get image URL from ImgBB for Runway input in generic flow.")
                results["imgbb_image_url"] = img_url_for_runway
                
                runway_task_id = self.generate_runway_video(img_url_for_runway)
                runway_video_result = self.wait_for_runway_video(runway_task_id)
                runway_output_video_url = runway_video_result["output"][0]
                results["runway_video_download_url"] = runway_output_video_url
                
                # Download the Runway video to a temporary local path for Cloudinary upload
                logger.info(f"Downloading Runway video (generic flow) from: {runway_output_video_url}")
                video_response = requests.get(runway_output_video_url, stream=True)
                video_response.raise_for_status()
                
                temp_generic_video_file = tempfile.NamedTemporaryFile(delete=False, suffix=".mp4", dir=self.output_dir_worker or None)
                final_video_local_path = temp_generic_video_file.name
                with open(final_video_local_path, 'wb') as f_video:
                    for chunk in video_response.iter_content(chunk_size=8192):
                        f_video.write(chunk)
                logger.info(f"Runway video (generic flow) downloaded to temporary path: {final_video_local_path}")

            # Common last step: Upload the final video (either from Chibi or generic flow) to Cloudinary
            if not final_video_local_path or not os.path.exists(final_video_local_path):
                raise FileNotFoundError(f"Final video for upload not found at expected path: {final_video_local_path}")

            cloudinary_final_video_url = self.upload_to_cloudinary(
                final_video_local_path, 
                public_id=f"{product_title.replace(' ', '_').replace('/', '_')}_video_{time.strftime('%Y%m%d%H%M%S')}"
            )
            results["cloudinary_video_url"] = cloudinary_final_video_url

            if cloudinary_final_video_url and user_email:
                self.send_video_email(user_email, product_title, cloudinary_final_video_url)
            elif not cloudinary_final_video_url:
                logger.warning("Video was not uploaded to Cloudinary. Email not sent.")
            elif not user_email:
                logger.info("No user email provided. Video uploaded to Cloudinary but email not sent.")

        except Exception as e:
            logger.error(f"Error in process_product for '{product_title}': {e}", exc_info=True)
            # Re-raise to be caught by run_worker for error reporting to Redis
            raise 
        finally:
            # Clean up the initially downloaded image if it was from a URL
            if temp_downloaded_image_path and os.path.exists(temp_downloaded_image_path):
                try:
                    os.remove(temp_downloaded_image_path)
                    logger.info(f"Cleaned up temporary downloaded image: {temp_downloaded_image_path}")
                except Exception as e_clean:
                    logger.error(f"Error cleaning up temp downloaded image {temp_downloaded_image_path}: {e_clean}")
            
            # Clean up the final local video (generic flow only, ChibiGenerator manages its own output dir)
            # ChibiGenerator output is in self.output_dir_worker which is cleaned up when the worker instance is done if we add a __del__ or similar
            # For generic flow, the temp_generic_video_file is created directly
            if final_video_local_path and os.path.exists(final_video_local_path) and product_title != "Dog Birthday Card":
                 try:
                    os.remove(final_video_local_path)
                    logger.info(f"Cleaned up temporary generic flow video: {final_video_local_path}")
                 except Exception as e_clean:
                    logger.error(f"Error cleaning up temp generic video {final_video_local_path}: {e_clean}")
            
            # Consider cleaning self.output_dir_worker if it was created for ChibiGenerator for this task
            # However, if multiple tasks are processed by one worker instance, this dir is shared.
            # A better approach for self.output_dir_worker is to clean it up if the worker process exits or perhaps per task if feasible.
            # For now, leaving it to be cleaned if ChibiGenerator init fails or relying on Heroku dyno's ephemeral nature.

        logger.info(f"\n=== Processing complete for: '{product_title}' ===\n")
        return results

    def run_worker(self):
        """
        Run as a worker process, listening to a Redis queue for tasks
        """
        logger.info("Starting worker mode...") # Changed print to logger.info
        
        redis_url = os.environ.get('REDIS_URL')
        if not redis_url:
            logger.error("Error: REDIS_URL environment variable not set. Cannot run in worker mode.") # Changed print to logger.error
            return
        
        r = None # Initialize r before try block
        try:
            r = redis.from_url(redis_url, ssl_cert_reqs=None)
            logger.info(f"Connected to Redis at {redis_url}") # Changed print to logger.info
            
            task_queue = 'dog_video_tasks'
            result_queue = 'dog_video_results'
            
            logger.info(f"Listening for tasks on queue: {task_queue}") # Changed print to logger.info
            
            while True:
                task_id_for_error = 'unknown' # Default for error reporting if task_id cannot be extracted
                try:
                    task_data_raw = r.blpop(task_queue, timeout=10)
                    
                    if task_data_raw is None:
                        logger.info("No tasks found. Waiting...") # Changed print to logger.info
                        continue
                    
                    _, task_json = task_data_raw
                    task = json.loads(task_json)
                    
                    task_id = task.get('task_id')
                    task_id_for_error = task_id or 'unknown' # Update for specific error reporting
                    photo_url = task.get('photo_url') # Expecting a URL (Cloudinary or other)
                    title = task.get('product_title', 'Dog Birthday Card')
                    description = task.get('product_description', 'A cute dog birthday card')
                    # email = task.get('email') # Email sending handled by ChibiGenerator or process_product
                    user_email = task.get('user_email') # Ensure this matches what server sends if needed
                    
                    logger.info(f"Processing task {task_id}: '{title}' for user '{user_email if user_email else 'N/A'}'") # Changed print to logger.info
                    
                    result = self.process_product(
                        product_photo_path=photo_url, # This is actually a URL
                        product_title=title,
                        product_description=description,
                        user_email=user_email, # Make sure server.py sends this as 'user_email' in task_data if needed by send_video_email
                        is_url=True  # Crucial: Indicate that product_photo_path is a URL
                    )
                    
                    result_payload = {
                        'task_id': task_id,
                        'status': 'completed',
                        'cloudinary_video_url': result.get('cloudinary_video_url')
                        # Add other relevant result fields if necessary
                    }
                    r.rpush(result_queue, json.dumps(result_payload))
                    
                    logger.info(f"Task {task_id} completed successfully. Result URL: {result_payload.get('cloudinary_video_url')}") # Changed print to logger.info
                    
                except KeyboardInterrupt:
                    logger.info("Worker shutting down due to KeyboardInterrupt...") # Changed print to logger.info
                    break
                except Exception as e:
                    logger.error(f"Error processing task {task_id_for_error}: {e}", exc_info=True) # Changed print to logger.error
                    try:
                        error_data = {
                            'task_id': task_id_for_error,
                            'status': 'error',
                            'error': str(e),
                            'details': traceback.format_exc()
                        }
                        if r: # Ensure Redis client is available
                           r.rpush(result_queue, json.dumps(error_data))
                        else:
                           logger.error("Redis client 'r' is None, cannot report error to queue.")
                    except Exception as report_e:
                        logger.error(f"CRITICAL: Failed to report error for task {task_id_for_error} to Redis: {report_e}", exc_info=True) # Changed print to logger.error
        
        except Exception as e:
            logger.error(f"Fatal worker error (Redis connection or main loop): {e}", exc_info=True) # Changed print to logger.error
            sys.exit(1)
        finally:
            logger.info("Worker process normally exiting or from fatal error.")
            if self.output_dir_worker and os.path.exists(self.output_dir_worker):
                try:
                    import shutil
                    shutil.rmtree(self.output_dir_worker)
                    logger.info(f"Cleaned up ChibiClipGenerator worker temp directory: {self.output_dir_worker}")
                except Exception as e_clean:
                    logger.error(f"Error cleaning up ChibiClipGenerator worker temp directory {self.output_dir_worker}: {e_clean}")


def main():
    parser = argparse.ArgumentParser(description="Automate product marketing material generation.")
    parser.add_argument("photo_path", help="Path to the product photo (e.g., product_photo.jpg)", nargs='?')
    parser.add_argument("product_title", help="Title of the product (e.g., 'Chibi Dog Illustration')", nargs='?')
    parser.add_argument("product_description", help="Description of the product.", nargs='?')
    parser.add_argument("--email", help="User's email address to send the final video link.", required=False)
    parser.add_argument("--worker", action='store_true', help="Run in worker mode, listening for tasks from Redis")
    
    args = parser.parse_args()

    from dotenv import load_dotenv
    dotenv_path = os.path.join(os.path.dirname(__file__), '.env')
    load_dotenv(dotenv_path=dotenv_path, verbose=True, override=True)
    
    config = {
        "openai_api_key": os.environ.get("OPENAI_API_KEY"),
        "imgbb_api_key": os.environ.get("IMGBB_API_KEY"), # For intermediate image for Runway
        "runway_api_key": os.environ.get("RUNWAY_API_KEY"),
        "cloudinary_cloud_name": os.environ.get("CLOUDINARY_CLOUD_NAME"),
        "cloudinary_api_key": os.environ.get("CLOUDINARY_API_KEY"),
        "cloudinary_api_secret": os.environ.get("CLOUDINARY_API_SECRET"),
        "sendgrid_api_key": os.environ.get("SENDGRID_API_KEY"),
        "mail_default_sender": os.environ.get("MAIL_DEFAULT_SENDER") # For SendGrid
    }
    
    if not config["mail_default_sender"] and args.email:
        print("Warning: MAIL_DEFAULT_SENDER environment variable is not set. Emails may fail or be marked as spam.")

    try:
        automation = ProductMarketingAutomation(
            openai_api_key=config["openai_api_key"],
            imgbb_api_key=config["imgbb_api_key"],
            runway_api_key=config["runway_api_key"],
            cloudinary_cloud_name=config["cloudinary_cloud_name"],
            cloudinary_api_key=config["cloudinary_api_key"],
            cloudinary_api_secret=config["cloudinary_api_secret"],
            sendgrid_api_key=config["sendgrid_api_key"]
        )
        
        if args.worker:
            # Run in worker mode
            automation.run_worker()
        else:
            # Run in CLI mode
            if not args.photo_path or not args.product_title or not args.product_description:
                parser.error("CLI mode requires photo_path, product_title, and product_description arguments")
            
            result = automation.process_product(
                product_photo_path=args.photo_path,
                product_title=args.product_title,
                product_description=args.product_description,
                user_email=args.email
            )
            
            print("\n=== Final Results Summary ===")
            if result.get("imgbb_image_url"):
                print(f"Edited Image URL (ImgBB for Runway): {result['imgbb_image_url']}")
            if result.get("runway_video_download_url"):
                print(f"Runway Output Video URL (raw from Runway): {result['runway_video_download_url']}")
            if result.get("cloudinary_video_url"):
                print(f"Final Video URL (Cloudinary): {result['cloudinary_video_url']}")
            else:
                print("Final video URL (Cloudinary): Not generated or uploaded.")
            
            if args.email and result.get("cloudinary_video_url"):
                print(f"An email with the video link should have been sent to {args.email}.")
            elif args.email:
                print(f"Email to {args.email} was not sent as Cloudinary URL was not available.")

    except Exception as e:
        print(f"Error in main automation execution: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main() 