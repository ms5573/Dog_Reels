import os
import requests
import json
import time
import base64
from io import BytesIO
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload, MediaIoBaseDownload
import argparse
import cloudinary
import cloudinary.uploader
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail

class ProductMarketingAutomation:
    def __init__(self, openai_api_key=None, google_credentials_path=None, imgbb_api_key=None, runway_api_key=None, cloudinary_cloud_name=None, cloudinary_api_key=None, cloudinary_api_secret=None, sendgrid_api_key=None):
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
        
        # Initialize Google Drive if credentials provided
        self.drive_service = None
        if google_credentials_path or os.environ.get("GOOGLE_CREDENTIALS_PATH"):
            self._init_google_drive(google_credentials_path)
    
    def _init_google_drive(self, credentials_path=None):
        """
        Initialize Google Drive API client using credentials file
        """
        creds_path = credentials_path or os.environ.get("GOOGLE_CREDENTIALS_PATH")
        try:
            with open(creds_path, 'r') as f:
                creds_data = json.load(f)
                
            creds = Credentials.from_authorized_user_info(creds_data)
            self.drive_service = build('drive', 'v3', credentials=creds)
            print("Successfully connected to Google Drive")
        except Exception as e:
            print(f"Error connecting to Google Drive: {e}")
            print("Google Drive functionality will be disabled")
    
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

    def upload_to_drive(self, file_path, file_name, folder_id=None):
        """
        Upload file to Google Drive
        """
        if not self.drive_service:
            raise ValueError("Google Drive is not configured")
        
        print(f"Uploading {file_name} to Google Drive")
        file_metadata = {'name': file_name}
        if folder_id:
            file_metadata['parents'] = [folder_id]
            
        media = MediaFileUpload(file_path, resumable=True)
        file = self.drive_service.files().create(
            body=file_metadata,
            media_body=media,
            fields='id'
        ).execute()
        
        file_id = file.get('id')
        print(f"File uploaded to Google Drive with ID: {file_id}")
        return file_id
    
    def download_from_drive(self, file_id):
        """
        Download file from Google Drive
        """
        if not self.drive_service:
            raise ValueError("Google Drive is not configured")
            
        print(f"Downloading file {file_id} from Google Drive")
        request = self.drive_service.files().get_media(fileId=file_id)
        file_content = BytesIO()
        downloader = MediaIoBaseDownload(file_content, request)
        
        done = False
        while not done:
            _, done = downloader.next_chunk()
            
        file_content.seek(0)
        print("File successfully downloaded from Google Drive")
        return file_content
    
    def edit_image_with_openai(self, image_content, prompt):
        """
        Use OpenAI's image editing API
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
            'model': (None, 'gpt-image-1') # Assuming this model is still desired/valid
        }
        
        try:
            response = requests.post("https://api.openai.com/v1/images/edits", headers=headers, files=files)
            response.raise_for_status()
            print("Image successfully edited with OpenAI")
            return response.json()["data"][0]["b64_json"]
        except requests.exceptions.RequestException as e:
            print(f"Error editing image: {e}")
            if hasattr(e, 'response') and e.response and e.response.text:
                print(f"Response error: {e.response.text}")
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
    
    def wait_for_runway_video(self, task_id, initial_wait=60, poll_interval=10, max_attempts=30): # Increased poll_interval and max_attempts
        """
        Poll Runway API until video is ready, with configurable waits
        """
        print(f"Waiting {initial_wait} seconds before first Runway status check...")
        time.sleep(initial_wait)
        
        attempts = 0
        while attempts < max_attempts:
            attempts += 1
            print(f"Checking Runway video status (attempt {attempts}/{max_attempts})...")
            
            task_status = self.check_runway_task_status(task_id)
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
        
        print(f"Runway video generation timed out after {max_attempts} attempts.")
        raise Exception(f"Runway video generation timed out after {max_attempts} attempts")
    
    def send_video_email(self, to_email, product_title, cloudinary_video_url):
        """
        Send email with the link to the Cloudinary video using SendGrid.
        """
        if not self.sendgrid_enabled:
            print(f"SendGrid is not enabled. Skipping email to {to_email}.")
            return False
        
        # Ensure you have a verified sender email with SendGrid
        from_email = os.environ.get("MAIL_DEFAULT_SENDER", "noreply@example.com") 
        if from_email == "noreply@example.com":
            print("Warning: MAIL_DEFAULT_SENDER is not set. Using placeholder. Email might fail or go to spam.")

        subject = f"🎉 Your Birthday Video for {product_title} is Ready!"
        html_content = f"""
        <html>
            <body>
                <h2>Hooray! Your video is ready!</h2>
                <p>The special birthday video for <strong>{product_title}</strong> has been generated.</p>
                <p>You can view and download your video here:</p>
                <p><a href="{cloudinary_video_url}" style="padding: 12px 20px; background-color: #007bff; color: white; text-decoration: none; border-radius: 5px; font-size: 16px;">Watch Your Video</a></p>
                <p>Or copy and paste this link into your browser: {cloudinary_video_url}</p>
                <br>
                <p>We hope you enjoy it!</p>
                <p>Best,</p>
                <p>The Dog Reels Team</p>
            </body>
        </html>
        """
        message = Mail(
            from_email=from_email,
            to_emails=to_email,
            subject=subject,
            html_content=html_content
        )
        try:
            sg = SendGridAPIClient(self.sendgrid_api_key)
            response = sg.send(message)
            print(f"Email sent to {to_email}. Status Code: {response.status_code}")
            if response.status_code >= 200 and response.status_code < 300:
                return True
            else:
                print(f"SendGrid error: {response.body}")
                return False
        except Exception as e:
            print(f"Error sending email via SendGrid: {e}")
            return False

    def process_product(self, product_photo_path, product_title, product_description, user_email, # Added user_email
                       upload_to_drive=True, folder_id=None): # Removed smtp_settings
        """
        Process product through the entire workflow
        """
        print(f"\n=== Starting process for: {product_title} for user {user_email} ===\n")
        results = {
            "product_title": product_title,
        }
        
        # (Optional) Upload original to Google Drive 
        file_id = None
        if upload_to_drive and self.drive_service:
            try:
                file_id = self.upload_to_drive(
                    product_photo_path, 
                    f"{product_title}_{time.strftime('%Y%m%d-%H%M%S')}_original", # Unique name
                    folder_id
                )
                results["drive_file_id"] = file_id
            except Exception as e:
                print(f"Failed to upload original to Drive: {e}")
        
        # Generate AI prompt for image editing
        ai_prompt = self.generate_ai_prompt(product_title, product_description)
        results["ai_prompt"] = ai_prompt
        print(f"Generated AI editing prompt: {ai_prompt[:100]}...")
        
        # Load image content
        # For simplicity, assuming product_photo_path is always a local file path
        with open(product_photo_path, 'rb') as f:
            image_content_bytes = f.read() # Read as bytes
        
        # Edit image with OpenAI (expects bytes or BytesIO)
        edited_image_b64 = self.edit_image_with_openai(image_content_bytes, ai_prompt)
        
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

        print(f"\n=== Processing complete for: {product_title} ===\n")
        return results


def main():
    parser = argparse.ArgumentParser(description="Automate product marketing material generation.")
    parser.add_argument("photo_path", help="Path to the product photo (e.g., product_photo.jpg)")
    parser.add_argument("product_title", help="Title of the product (e.g., 'Chibi Dog Illustration')")
    parser.add_argument("product_description", help="Description of the product.")
    parser.add_argument("--email", help="User's email address to send the final video link.", required=False) # Make email optional for now
    parser.add_argument("--upload_to_drive", action='store_true', help="Upload original photo to Google Drive.")
    parser.add_argument("--drive_folder_id", help="Google Drive folder ID to upload to.", default=None)
    
    args = parser.parse_args()

    from dotenv import load_dotenv
    dotenv_path = os.path.join(os.path.dirname(__file__), '.env')
    load_dotenv(dotenv_path=dotenv_path, verbose=True, override=True)
    
    config = {
        "openai_api_key": os.environ.get("OPENAI_API_KEY"),
        "google_credentials_path": os.environ.get("GOOGLE_CREDENTIALS_PATH"), # For GDrive
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
            google_credentials_path=config["google_credentials_path"],
            imgbb_api_key=config["imgbb_api_key"],
            runway_api_key=config["runway_api_key"],
            cloudinary_cloud_name=config["cloudinary_cloud_name"],
            cloudinary_api_key=config["cloudinary_api_key"],
            cloudinary_api_secret=config["cloudinary_api_secret"],
            sendgrid_api_key=config["sendgrid_api_key"]
        )
        
        result = automation.process_product(
            product_photo_path=args.photo_path,
            product_title=args.product_title,
            product_description=args.product_description,
            user_email=args.email, 
            upload_to_drive=args.upload_to_drive,
            folder_id=args.drive_folder_id
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