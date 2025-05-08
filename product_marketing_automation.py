import os
import requests
import json
import time
import base64
from io import BytesIO
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload, MediaIoBaseDownload
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

class ProductMarketingAutomation:
    def __init__(self, openai_api_key=None, google_credentials_path=None, imgbb_api_key=None, runway_api_key=None):
        """
        Initialize with API keys or load from environment variables if not provided
        """
        # Load API keys from environment variables if not provided
        self.openai_api_key = openai_api_key or os.environ.get("OPENAI_API_KEY")
        self.imgbb_api_key = imgbb_api_key or os.environ.get("IMGBB_API_KEY")
        self.runway_api_key = runway_api_key or os.environ.get("RUNWAY_API_KEY")
        
        # Check for required credentials
        if not self.openai_api_key:
            raise ValueError("OpenAI API key is required")
        if not self.imgbb_api_key:
            raise ValueError("ImgBB API key is required")
        if not self.runway_api_key:
            raise ValueError("Runway API key is required")
        
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
        print(f"Generating fixed style AI prompt (product: {product_title})") # Title still useful for logging
        
        # System message defines the desired output style
        style_prompt = "Charming vector illustration of a chibi-style dog with flat pastel, bold black outlines, subtle cel-shading and natural soft shadows, centered on a clean light-beige background with a faint oval ground shadow, minimalistic and playful design."
        
        # The user message to OpenAI's chat completion can be simple or just reiterate the style for image editing.
        # For image editing, the main prompt is passed separately to the image API.
        # Here, we are just using the chat completion to perhaps refine or confirm the style description if needed,
        # but for direct image editing, this step might be simplified to just return style_prompt directly.
        # For now, let's assume the original structure was for a more complex prompt generation.
        # We will return the style_prompt directly for the image editing.

        # headers = {
        #     "Content-Type": "application/json",
        #     "Authorization": f"Bearer {self.openai_api_key}"
        # }
        # payload = {
        #     "model": "gpt-4.1",
        #     "messages": [
        #         {"role": "system", "content": style_prompt},
        #         {"role": "user", "content": f"Ensure the style is captured for an image of a {product_title}."} # Simpler user content
        #     ]
        # }
        
        # try:
        #     response = requests.post("https://api.openai.com/v1/chat/completions", headers=headers, json=payload)
        #     response.raise_for_status()
        #     # The actual prompt for image editing should be the style_prompt itself.
        #     # The response from chat completion might be a confirmation or a slightly rephrased version.
        #     # For simplicity and directness for image editing, we will return the raw style_prompt.
        #     # return response.json()["choices"][0]["message"]["content"]
        #     return style_prompt 
        # except requests.exceptions.RequestException as e:
        #     print(f"Error generating AI prompt: {e}")
        #     if hasattr(e, 'response') and e.response and e.response.text:
        #         print(f"Response error: {e.response.text}")
        #     raise
        return style_prompt # Directly return the style prompt
    
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
        
        # Use bytes directly if it's already a BytesIO object
        if isinstance(image_content, BytesIO):
            image_bytes = image_content.getvalue()
        else:
            image_bytes = image_content
            
        files = {
            'image': ('image.png', image_bytes, 'image/png'),
            'prompt': (None, prompt),
            'model': (None, 'gpt-image-1')
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
        Upload image to ImgBB hosting
        """
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
            raise
    
    def generate_runway_video(self, image_url):
        """
        Generate video from image using Runway API
        """
        print("Generating video with Runway")
        headers = {
            "Authorization": f"Bearer {self.runway_api_key}",
            "X-Runway-Version": "2024-11-06",
            "Content-Type": "application/json"
        }
        
        payload = {
            "promptImage": image_url,
            "model": "gen4_turbo",
            "promptText": "Seamless looped 2D animation of the chibi-style spaniel-mix puppy running in place—flat pastel orange and cream fur with bold black outlines, teal collar, smooth leg and ear motion, subtle cel-shading, on a clean light-beige background with a soft oval ground shadow, minimalistic children's storybook style, continuous playful motion without cuts or zooms.",
            "duration": 5,  # Changed from string "5" to integer 5
            "ratio": "960:960"
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
            "X-Runway-Version": "2024-11-06"
        }
        
        url = f"https://api.dev.runwayml.com/v1/tasks/{task_id}"
        try:
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"Error checking Runway task status: {e}")
            raise
    
    def wait_for_runway_video(self, task_id, initial_wait=60, poll_interval=5, max_attempts=20):
        """
        Poll Runway API until video is ready, with configurable waits
        """
        print(f"Waiting {initial_wait} seconds before first status check...")
        time.sleep(initial_wait)
        
        attempts = 0
        while attempts < max_attempts:
            attempts += 1
            print(f"Checking video status (attempt {attempts}/{max_attempts})...")
            
            task_status = self.check_runway_task_status(task_id)
            status = task_status.get("status")
            
            if status == "COMPLETED":
                print(f"Video generation completed after {attempts} checks!")
                return task_status
            elif status == "SUCCEEDED":
                print(f"Video generation SUCCEEDED after {attempts} checks!")
                return task_status
            elif status == "FAILED":
                raise Exception(f"Video generation failed: {task_status.get('error', 'Unknown error')}")
            elif status in ["RUNNING", "PENDING"]:
                print(f"Video still generating (status: {status}). Waiting {poll_interval} seconds...")
                time.sleep(poll_interval)
            else:
                print(f"Unknown status: {status}. Waiting {poll_interval} seconds...")
                time.sleep(poll_interval)
        
        raise Exception(f"Timed out after {max_attempts} attempts")
    
    def send_email(self, to_email, product_title, image_url, video_url, smtp_settings=None):
        """
        Send email with marketing materials
        """
        if not smtp_settings:
            smtp_settings = {
                "server": os.environ.get("SMTP_SERVER", "smtp.gmail.com"),
                "port": int(os.environ.get("SMTP_PORT", 587)),
                "username": os.environ.get("SMTP_USERNAME"),
                "password": os.environ.get("SMTP_PASSWORD")
            }
            
            if not smtp_settings["username"] or not smtp_settings["password"]:
                raise ValueError("SMTP credentials not provided")
        
        print(f"Sending email to {to_email}")
        msg = MIMEMultipart()
        msg["From"] = smtp_settings["username"]
        msg["To"] = to_email
        msg["Subject"] = f"Marketing Materials: {product_title}"
        
        body = f"""
        Hey there,
        
        Here are the requested marketing materials for your {product_title}:
        
        Image: {image_url}
        
        Video: {video_url}
        
        Cheers!
        """
        
        msg.attach(MIMEText(body, "plain"))
        
        try:
            server = smtplib.SMTP(smtp_settings["server"], smtp_settings["port"])
            server.starttls()
            server.login(smtp_settings["username"], smtp_settings["password"])
            server.send_message(msg)
            server.quit()
            print("Email sent successfully")
        except Exception as e:
            print(f"Error sending email: {e}")
            raise
    
    def process_product(self, product_photo_path, product_title, product_description, email, 
                       upload_to_drive=True, folder_id=None, smtp_settings=None):
        """
        Process product through the entire workflow
        """
        print(f"\n=== Starting process for: {product_title} ===\n")
        results = {
            "product_title": product_title,
            # "email": email, # Email parameter no longer used for sending
        }
        
        # Upload to Google Drive (optional)
        file_id = None
        if upload_to_drive and self.drive_service:
            file_id = self.upload_to_drive(
                product_photo_path, 
                f"{product_title} (Original)",
                folder_id
            )
            results["drive_file_id"] = file_id
        
        # Generate AI prompt
        ai_prompt = self.generate_ai_prompt(product_title, product_description)
        results["ai_prompt"] = ai_prompt
        print(f"Generated prompt: {ai_prompt[:100]}...")
        
        # Load image content - either from Google Drive or directly from file
        if file_id and self.drive_service:
            image_content = self.download_from_drive(file_id)
        else:
            with open(product_photo_path, 'rb') as f:
                image_content = BytesIO(f.read())
        
        # Edit image with OpenAI
        edited_image_b64 = self.edit_image_with_openai(image_content, ai_prompt)
        
        # Upload to ImgBB
        img_url = self.upload_to_imgbb(edited_image_b64)
        results["image_url"] = img_url
        
        # Generate video with Runway
        task_id = self.generate_runway_video(img_url)
        
        # Wait for video to complete
        video_result = self.wait_for_runway_video(task_id)
        video_url = video_result["output"][0]
        results["video_url"] = video_url
        
        # Send email with results
        # if email: # Email sending is disabled
        #     self.send_email(email, product_title, img_url, video_url, smtp_settings)
        
        print(f"\n=== Processing complete for: {product_title} ===\n")
        return results


# Example usage with more flexible configuration
def main():
    # Load configuration from environment or .env file
    from dotenv import load_dotenv
    # Explicitly specify the path to .env in the same directory as the script
    dotenv_path = os.path.join(os.path.dirname(__file__), '.env')
    load_dotenv(dotenv_path=dotenv_path, verbose=True, override=True) # Keep verbose and override for now, remove print lines
    
    # Example of how to configure the automation with detailed options
    config = {
        # API Keys (can be loaded from environment variables)
        "openai_api_key": os.environ.get("OPENAI_API_KEY"),
        "google_credentials_path": os.environ.get("GOOGLE_CREDENTIALS_PATH"),
        "imgbb_api_key": os.environ.get("IMGBB_API_KEY"),
        "runway_api_key": os.environ.get("RUNWAY_API_KEY"),
        
        # Email settings (not used for sending in this version, but kept for structure)
        "smtp_settings": {
            "server": os.environ.get("SMTP_SERVER", "smtp.gmail.com"),
            "port": int(os.environ.get("SMTP_PORT", 587)),
            "username": os.environ.get("SMTP_USERNAME"),
            "password": os.environ.get("SMTP_PASSWORD")
        }
    }
    
    # Create automation instance
    try:
        automation = ProductMarketingAutomation(
            openai_api_key=config["openai_api_key"],
            google_credentials_path=config["google_credentials_path"],
            imgbb_api_key=config["imgbb_api_key"],
            runway_api_key=config["runway_api_key"]
        )
        
        # Process a product
        product_title_for_run = "Chibi Dog Illustration"
        result = automation.process_product(
            product_photo_path="product_photo.jpg", # Ensure this file exists
            product_title=product_title_for_run,
            product_description="A charming chibi-style dog illustration created from an uploaded photo.",
            email=None, # Email set to None as it's not being sent
            # smtp_settings=config["smtp_settings"] # Not needed if email is None
        )
        
        # Print results
        print("\n=== Results ===")
        print(f"Static Image URL: {result['image_url']}")
        print(f"Animated Video URL: {result['video_url']}")

        # Download and save the video
        if result.get('video_url'):
            video_url = result['video_url']
            # Create a filename for the video
            safe_title = "".join(c if c.isalnum() else "_" for c in product_title_for_run)
            video_filename = f"{safe_title}_video.mp4"
            
            print(f"Downloading video from {video_url} to {video_filename}...")
            try:
                video_response = requests.get(video_url, stream=True)
                video_response.raise_for_status() # Check if the request was successful
                with open(video_filename, 'wb') as f:
                    for chunk in video_response.iter_content(chunk_size=8192):
                        f.write(chunk)
                print(f"Video saved successfully as {video_filename}")
            except requests.exceptions.RequestException as e:
                print(f"Error downloading video: {e}")
            except IOError as e:
                print(f"Error saving video file: {e}")
        
    except Exception as e:
        print(f"Error in automation: {e}")

if __name__ == "__main__":
    main() 