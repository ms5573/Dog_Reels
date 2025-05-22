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
import json

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
        # ImgBB is now optional if Cloudinary is primary for final video
        # if not self.imgbb_api_key:
        #     raise ValueError("ImgBB API key is required")
        if not self.runway_api_key:
            raise ValueError("Runway API key is required")
        if not (self.cloudinary_cloud_name and self.cloudinary_api_key and self.cloudinary_api_secret):
            print("Cloudinary credentials not fully set. Video upload to Cloudinary will be disabled.")
            self.cloudinary_enabled = False
        else:
            self.cloudinary_enabled = True
            cloudinary.config( 
                cloud_name = self.cloudinary_cloud_name, 
                api_key = self.cloudinary_api_key, 
                api_secret = self.cloudinary_api_secret,
                secure = True
            )
            print("Cloudinary configured.")

        if not self.sendgrid_api_key:
            print("SendGrid API key not set. Email notifications will be disabled.")
            self.sendgrid_enabled = False
        else:
            self.sendgrid_enabled = True
            print("SendGrid configured.")
        
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
            print(f"Processing image from URL: {image_url}")
            
            # Handle file:// protocol URLs (fallback from Cloudinary)
            if image_url.startswith('file://'):
                file_path = image_url[7:]  # Remove file:// prefix
                print(f"Using local file fallback path: {file_path}")
                
                # Check if file exists
                if not os.path.exists(file_path):
                    print(f"WARNING: Local file not found: {file_path}")
                    raise FileNotFoundError(f"Local file not found: {file_path}")
                
                # No need to download, just return the path
                return file_path
            
            # Regular URL handling
            print(f"Downloading image from remote URL: {image_url}")
            response = requests.get(image_url, stream=True)
            response.raise_for_status()  # Raise an exception for HTTP errors
            
            # Create a temporary file to save the image
            temp_image_file = tempfile.NamedTemporaryFile(delete=False, suffix=".jpg")
            temp_path = temp_image_file.name
            
            with open(temp_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            
            print(f"Image downloaded to temporary path: {temp_path}")
            return temp_path
        except Exception as e:
            print(f"Error downloading image from URL: {e}")
            raise

    def process_product(self, product_photo_path, product_title, product_description, user_email=None,
                   upload_to_drive=False, folder_id=None, is_url=False): # Added is_url parameter
        """
        Process a product through the complete workflow:
        1. Generate AI prompt
        2. Edit the product image
        3. Upload edited image
        4. Create Runway video
        5. Upload final video to Cloudinary
        6. Send email with Cloudinary link
        7. Return the video URL
        """
        print(f"\n=== Starting process for: {product_title} for user {user_email} ===\n")
        results = {
            "product_title": product_title,
        }
        
        # Generate AI prompt for image editing
        ai_prompt = self.generate_ai_prompt(product_title, product_description)
        results["ai_prompt"] = ai_prompt
        print(f"Generated AI editing prompt: {ai_prompt[:100]}...")
        
        # Load image content
        temp_file_path = None
        try:
            # If product_photo_path is a URL, download it first
            if is_url:
                temp_file_path = self.download_image_from_url(product_photo_path)
                # Now use the temp file path as the source
                with open(temp_file_path, 'rb') as f:
                    image_content_bytes = f.read()
            else:
                # For simplicity, assuming product_photo_path is a local file path
                with open(product_photo_path, 'rb') as f:
                    image_content_bytes = f.read() # Read as bytes
            
            # Try to edit image with OpenAI (with retries)
            edited_image_b64 = None
            try:
                edited_image_b64 = self.edit_image_with_openai(image_content_bytes, ai_prompt)
            except Exception as e:
                print(f"Failed to edit image with OpenAI after retries: {e}")
                print("Using original image as fallback...")
                # Convert original image to base64 as fallback
                edited_image_b64 = base64.b64encode(image_content_bytes).decode('utf-8')
            
            # Upload edited image to ImgBB to get a URL for Runway
            # (Runway needs a URL for promptImage)
            img_url_for_runway = self.upload_to_imgbb(edited_image_b64)
            if not img_url_for_runway:
                print("Failed to upload image to ImgBB. Cannot proceed with Runway video generation.")
                raise Exception("Failed to get image URL for Runway input.")
            results["imgbb_image_url"] = img_url_for_runway
            
            # Generate video with Runway
            runway_task_id = self.generate_runway_video(img_url_for_runway)
            
            # Wait for Runway video to complete
            runway_video_result = self.wait_for_runway_video(runway_task_id)
            # Assuming the first output is always the desired video MP4
            runway_output_video_url = runway_video_result["output"][0] 
            results["runway_video_download_url"] = runway_output_video_url
            
            # Download the Runway video locally to then upload to Cloudinary
            local_runway_video_path = None
            try:
                print(f"Downloading Runway video from: {runway_output_video_url}")
                video_response = requests.get(runway_output_video_url, stream=True)
                video_response.raise_for_status()
                
                # Create a temporary file to save the video
                temp_video_file = tempfile.NamedTemporaryFile(delete=False, suffix=".mp4")
                local_runway_video_path = temp_video_file.name
                with open(local_runway_video_path, 'wb') as f_video:
                    for chunk in video_response.iter_content(chunk_size=8192):
                        f_video.write(chunk)
                print(f"Runway video downloaded to temporary path: {local_runway_video_path}")

                # Upload the downloaded Runway video to Cloudinary
                cloudinary_final_video_url = self.upload_to_cloudinary(
                    local_runway_video_path, 
                    public_id=f"{product_title.replace(' ', '_')}_video_{time.strftime('%Y%m%d%H%M%S')}"
                )
                results["cloudinary_video_url"] = cloudinary_final_video_url

                if cloudinary_final_video_url and user_email:
                    self.send_video_email(user_email, product_title, cloudinary_final_video_url)
                elif not cloudinary_final_video_url:
                    print("Video was not uploaded to Cloudinary. Email not sent.")
                elif not user_email:
                    print("No user email provided. Video uploaded to Cloudinary but email not sent.")

            except Exception as e:
                print(f"Error during Runway video download or Cloudinary upload: {e}")
                # Potentially send an error email or handle differently
            finally:
                # Clean up the temporary local video file
                if local_runway_video_path and os.path.exists(local_runway_video_path):
                    try:
                        os.remove(local_runway_video_path)
                        print(f"Cleaned up temporary video file: {local_runway_video_path}")
                    except Exception as e_clean:
                        print(f"Error cleaning up temp video file {local_runway_video_path}: {e_clean}")
        finally:
            # Clean up temporary image file if it was created
            if temp_file_path and os.path.exists(temp_file_path):
                try:
                    os.remove(temp_file_path)
                    print(f"Cleaned up temporary image file: {temp_file_path}")
                except Exception as e_clean:
                    print(f"Error cleaning up temp image file {temp_file_path}: {e_clean}")

        print(f"\n=== Processing complete for: {product_title} ===\n")
        return results

    def run_worker(self):
        """
        Run as a worker process, listening to a Redis queue for tasks
        """
        print("Starting worker mode...")
        
        # Connect to Redis (using Heroku REDIS_URL if available)
        redis_url = os.environ.get('REDIS_URL')
        if not redis_url:
            print("Error: REDIS_URL environment variable not set. Cannot run in worker mode.")
            return
        
        try:
            # Use SSL cert verification bypass for self-signed certificates
            r = redis.from_url(redis_url, ssl_cert_reqs=None)
            print(f"Connected to Redis at {redis_url}")
            
            # Define queue names
            task_queue = 'dog_video_tasks'
            result_queue = 'dog_video_results'
            
            print(f"Listening for tasks on queue: {task_queue}")
            
            while True:
                try:
                    # Check for new tasks with a timeout
                    task_data = r.blpop(task_queue, timeout=10)
                    
                    if task_data is None:
                        # No task was found, continue polling
                        print("No tasks found. Waiting...")
                        continue
                    
                    # Extract the task data
                    _, task_json = task_data
                    task = json.loads(task_json)
                    
                    task_id = task.get('task_id')
                    # Updated to look for photo_url instead of photo_path
                    photo_url = task.get('photo_url')
                    title = task.get('product_title', 'Dog Birthday Card')
                    description = task.get('product_description', 'A cute dog birthday card')
                    email = task.get('email')
                    
                    print(f"Processing task {task_id}: {title} for {email}")
                    
                    # Process the task with is_url=True since we're now using URLs
                    result = self.process_product(
                        product_photo_path=photo_url,
                        product_title=title,
                        product_description=description,
                        user_email=email,
                        is_url=True  # Indicate this is a URL, not a local path
                    )
                    
                    # Store the result in Redis
                    result['task_id'] = task_id
                    result['status'] = 'completed'
                    r.rpush(result_queue, json.dumps(result))
                    
                    print(f"Task {task_id} completed successfully.")
                    
                except KeyboardInterrupt:
                    print("Worker shutting down...")
                    break
                except Exception as e:
                    print(f"Error processing task: {e}")
                    traceback.print_exc()
                    # Try to report the error, but continue processing other tasks
                    try:
                        error_data = {
                            'task_id': task_id if 'task_id' in locals() else 'unknown',
                            'status': 'error',
                            'error': str(e)
                        }
                        r.rpush(result_queue, json.dumps(error_data))
                    except:
                        pass
        
        except Exception as e:
            print(f"Fatal worker error: {e}")
            traceback.print_exc()
            sys.exit(1)


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