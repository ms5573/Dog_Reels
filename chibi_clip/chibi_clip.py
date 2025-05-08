import os
import requests
import json
import time
import base64
from io import BytesIO
import urllib.request
import tempfile
from PIL import Image
# Import specific modules from moviepy
from moviepy.video.io.VideoFileClip import VideoFileClip
from moviepy.audio.io.AudioFileClip import AudioFileClip
from moviepy.video.compositing.CompositeVideoClip import concatenate_videoclips
from moviepy.audio.AudioClip import AudioClip
# Import these directly from the moviepy package
import moviepy
# argparse and random will be imported in their respective scopes
import uuid

# Step 6: Runway helpers (constants)
RATIO_MAP = {
    "9:16": "720:1280",
    "16:9": "1280:720",
    "1:1":  "960:960"  # fallback square
}

# Define image size mapping for OpenAI based on video ratios
# OpenAI supports: 1024x1024, 1024x1536, 1536x1024, and auto
# Let's map our video ratios to the closest OpenAI supported dimensions
IMAGE_SIZE_MAP = {
    "9:16": "1024x1536",   # portrait/vertical
    "16:9": "1536x1024",   # landscape
    "1:1":  "1024x1024"    # square
}

DUR_ALLOWED = (5, 10)

class ChibiClipGenerator:
    # Step 2: Rename & slim the class constructor
    def __init__(self, openai_api_key, imgbb_api_key, runway_api_key, *, verbose=True, output_dir=None):
        self.verbose = verbose
        self.openai_api_key = openai_api_key
        self.imgbb_api_key  = imgbb_api_key
        self.runway_api_key = runway_api_key
        
        # Set up output directory for local storage
        if output_dir is None:
            # Default to 'Output' directory in the project root
            project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            self.output_dir = os.path.join(project_root, "Output")
        else:
            self.output_dir = output_dir
            
        # Create the output directory if it doesn't exist
        if not os.path.exists(self.output_dir):
            if self.verbose:
                print(f"Creating output directory: {self.output_dir}")
            os.makedirs(self.output_dir, exist_ok=True)

        missing = [k for k,v in {"OpenAI":openai_api_key,
                                 "Runway":runway_api_key}.items() if not v]
        if missing:
            raise ValueError(f"Missing API key(s): {', '.join(missing)}")
        
        # ImgBB is now optional as we have local storage fallback
        if not imgbb_api_key:
            if self.verbose:
                print("Warning: ImgBB API key not provided. Will use local storage only.")
                print("Note: When ImgBB is unavailable, data URIs will be used for Runway API compatibility.")
        
        if self.verbose:
            print("ChibiClipGenerator initialized.")
            
    # New method to save images locally
    def save_image_locally(self, image_base64: str) -> str:
        """
        Saves a base64 encoded image to the local output directory.
        Returns the local file path and a URL that can be used by the application.
        """
        if self.verbose:
            print("Saving image to local storage...")
            
        try:
            # Decode the base64 image
            image_data = base64.b64decode(image_base64)
            
            # Generate a unique filename
            filename = f"{uuid.uuid4().hex}.png"
            file_path = os.path.join(self.output_dir, filename)
            
            # Save the image file
            with open(file_path, "wb") as f:
                f.write(image_data)
                
            # Create a URL that can be used by the application
            # For local development, use a file:// URL
            file_url = f"file://{os.path.abspath(file_path)}"
            
            if self.verbose:
                print(f"Image saved locally: {file_path}")
                print(f"Local URL: {file_url}")
                
            return {"url": file_url, "path": file_path, "filename": filename}
        except Exception as e:
            error_message = f"Error saving image locally: {e}"
            if self.verbose:
                print(error_message)
            raise RuntimeError(error_message) from e
                
    # Step 3: Prompt generator
    def generate_ai_prompt(self, action="running"):
        if action == "birthday-dance":
            base = ("Charming vector illustration of a chibi‑style dog with flat pastel colors, "
                    "bold black outlines, subtle cel‑shading and soft shadows, centered on a clean "
                    "light‑beige background with a faint oval ground shadow, minimalistic and playful. "
                    "The dog is wearing a colorful party hat and has a happy celebratory expression.")
            prompt = f"{base} The dog is dancing joyfully for a birthday celebration."
        else:
            base = ("Charming vector illustration of a chibi‑style dog with flat pastel colors, "
                    "bold black outlines, subtle cel‑shading and soft shadows, centered on a clean "
                    "light‑beige background with a faint oval ground shadow, minimalistic and playful.")
            prompt = f"{base} The dog is {action} in place."
        
        if self.verbose:
            print(f"Generated AI prompt for OpenAI: '{prompt}'")
        return prompt

    # Helper method to preprocess image for OpenAI
    def _preprocess_image_for_openai(self, image_content: BytesIO, max_size_mb=3.5) -> BytesIO:
        """
        Preprocesses an image to make it compatible with OpenAI's API.
        Resizes and compresses if needed to stay under the size limit.
        """
        if self.verbose:
            print("Preprocessing image for OpenAI API...")
        
        # Get the original size in MB
        original_size = len(image_content.getvalue()) / (1024 * 1024)
        
        if self.verbose:
            print(f"Original image size: {original_size:.2f} MB")
        
        # If image is already small enough, return as is
        if original_size <= max_size_mb:
            if self.verbose:
                print("Image already under size limit, no preprocessing needed.")
            # Reset the position to the beginning of the buffer
            image_content.seek(0)
            return image_content
        
        # Load the image with PIL
        image_content.seek(0)
        img = Image.open(image_content)
        
        # Calculate the scale factor to reduce size
        scale_factor = (max_size_mb / original_size) ** 0.5
        new_width = int(img.width * scale_factor)
        new_height = int(img.height * scale_factor)
        
        if self.verbose:
            print(f"Resizing image from {img.width}x{img.height} to {new_width}x{new_height}")
        
        # Resize the image
        img = img.resize((new_width, new_height), Image.LANCZOS)
        
        # Convert to RGB if it's RGBA (some PNG files)
        if img.mode == 'RGBA':
            if self.verbose:
                print("Converting from RGBA to RGB")
            img = img.convert('RGB')
        
        # Save to a new BytesIO buffer with compression
        processed_buffer = BytesIO()
        img.save(processed_buffer, format='JPEG', quality=85)
        processed_buffer.seek(0)
        
        # Mark this buffer as containing JPEG
        processed_buffer._is_jpeg = True
        
        processed_size = len(processed_buffer.getvalue()) / (1024 * 1024)
        if self.verbose:
            print(f"Preprocessed image size: {processed_size:.2f} MB")
            
        return processed_buffer

    # Step 4: OpenAI image-editing wrapper (updated to support dimensions and retries)
    def edit_image_with_openai(self, image_content: BytesIO, prompt: str, image_size: str = "1024x1024") -> str:
        if self.verbose:
            print(f"Editing image with OpenAI using prompt: \"{prompt}\" with size {image_size}")
        
        # Validate image_size is supported by OpenAI
        valid_sizes = ["1024x1024", "1024x1536", "1536x1024", "auto"]
        if image_size not in valid_sizes:
            if self.verbose:
                print(f"Warning: Image size {image_size} not supported by OpenAI. Defaulting to 1024x1024.")
            image_size = "1024x1024"
        
        # Preprocess the image to ensure it's not too large
        processed_image = self._preprocess_image_for_openai(image_content)
        
        headers = {
            "Authorization": f"Bearer {self.openai_api_key}"
        }
        
        image_bytes = processed_image.getvalue()
        
        # Determine proper content type based on preprocessing
        content_type = 'image/jpeg' if hasattr(processed_image, '_is_jpeg') else 'image/png'
        extension = '.jpg' if content_type == 'image/jpeg' else '.png'
        
        if self.verbose:
            print(f"Using image format: {content_type}")
            
        files = {
            'image': (f'image{extension}', image_bytes, content_type),
            'prompt': (None, prompt),
            'model': (None, 'gpt-image-1'),
            'size': (None, image_size)  # Added size parameter
        }

        # Retry parameters
        max_retries = 3
        timeout_value = 120  # Increased from 60 to 120 seconds
        backoff_factor = 2
        
        for attempt in range(max_retries):
            try:
                if self.verbose:
                    print(f"OpenAI API request attempt {attempt+1}/{max_retries}...")
                
                response = requests.post(
                    "https://api.openai.com/v1/images/edits", 
                    headers=headers, 
                    files=files, 
                    timeout=timeout_value
                )
                response.raise_for_status()
                b64_json = response.json()["data"][0]["b64_json"]
                
                if self.verbose:
                    print("Image successfully edited with OpenAI.")
                return b64_json
                
            except requests.exceptions.Timeout:
                wait_time = backoff_factor ** attempt
                if self.verbose:
                    print(f"Timeout on attempt {attempt+1}/{max_retries}. Waiting {wait_time}s before retrying...")
                
                if attempt < max_retries - 1:
                    time.sleep(wait_time)
                else:
                    error_message = f"Error editing image with OpenAI: Timeout after {max_retries} attempts"
                    if self.verbose:
                        print(error_message)
                    raise RuntimeError(error_message)
                    
            except requests.exceptions.RequestException as e:
                error_message = f"Error editing image with OpenAI: {e}"
                if hasattr(e, 'response') and e.response is not None:
                    try:
                        error_details = e.response.json()
                        error_message += f" - Details: {error_details}"
                    except json.JSONDecodeError:
                        error_message += f" - Response content: {e.response.text}"
                
                if self.verbose:
                    print(error_message)
                
                # For connection errors, retry with backoff
                if isinstance(e, (requests.exceptions.ConnectionError, requests.exceptions.ReadTimeout)):
                    wait_time = backoff_factor ** attempt
                    if self.verbose:
                        print(f"Connection error on attempt {attempt+1}/{max_retries}. Waiting {wait_time}s before retrying...")
                    
                    if attempt < max_retries - 1:
                        time.sleep(wait_time)
                        continue
                
                raise RuntimeError(error_message) from e

    # Step 5: ImgBB upload (modified to include local fallback)
    def upload_to_imgbb(self, image_base64: str, use_local_fallback=True) -> str:
        if not self.imgbb_api_key:
            if self.verbose:
                print("No ImgBB API key provided. Using local storage.")
            if use_local_fallback:
                result = self.save_image_locally(image_base64)
                return result["url"]
            else:
                raise ValueError("ImgBB API key not provided and local fallback disabled.")
        
        if self.verbose:
            print("Uploading image to ImgBB...")
        url = "https://api.imgbb.com/1/upload"
        payload = {
            'key': self.imgbb_api_key,
            'image': image_base64
        }
        try:
            response = requests.post(url, data=payload, timeout=30)
            response.raise_for_status()
            img_url = response.json()["data"]["url"]
            if self.verbose:
                print(f"Image uploaded to ImgBB: {img_url}")
            return img_url
        except requests.exceptions.RequestException as e:
            error_message = f"Error uploading to ImgBB: {e}"
            if hasattr(e, 'response') and e.response is not None:
                try:
                    error_details = e.response.json()
                    error_message += f" - Details: {error_details}"
                except json.JSONDecodeError:
                    error_message += f" - Response content: {e.response.text}"
            if self.verbose:
                print(error_message)
            
            # Fall back to local storage if enabled
            if use_local_fallback:
                if self.verbose:
                    print("Falling back to local storage...")
                result = self.save_image_locally(image_base64)
                return result["url"]
            else:
                raise RuntimeError(error_message) from e

    # Step 6a: Runway Kick-off call
    def generate_runway_video(self, img_url: str, action: str, ratio: str, duration: int) -> str:
        if ratio not in RATIO_MAP:
            raise ValueError(f"Invalid ratio '{ratio}'. Must be one of {list(RATIO_MAP.keys())}")
        if duration not in DUR_ALLOWED:
            raise ValueError(f"Invalid duration {duration}. Must be one of {DUR_ALLOWED}")

        if self.verbose:
            print(f"Starting Runway video generation for image: {img_url} (action: {action}, ratio: {ratio}, duration: {duration}s)")
        
        # Check if the image URL is a local file:// URL
        if img_url.startswith("file://"):
            if self.verbose:
                print("Image URL is a local file. Runway requires HTTPS URLs or data URIs.")
                
            # Extract the file path
            local_path = img_url[7:]  # Remove file:// prefix
            if self.verbose:
                print(f"Loading local image from: {local_path}")
            
            # Read the image data
            try:
                with open(local_path, "rb") as f:
                    image_data = f.read()
                # Convert to base64
                image_base64 = base64.b64encode(image_data).decode('utf-8')
                
                # First try ImgBB if we have an API key
                if self.imgbb_api_key:
                    try:
                        if self.verbose:
                            print("Attempting to upload to ImgBB for Runway compatibility...")
                        
                        url = "https://api.imgbb.com/1/upload"
                        payload = {
                            'key': self.imgbb_api_key,
                            'image': image_base64
                        }
                        response = requests.post(url, data=payload, timeout=30)
                        response.raise_for_status()
                        img_url = response.json()["data"]["url"]
                        
                        if self.verbose:
                            print(f"Image uploaded to ImgBB for Runway: {img_url}")
                    except Exception as e:
                        if self.verbose:
                            print(f"ImgBB upload failed: {e}")
                            print("Trying data URI approach...")
                        
                        # Determine the file extension and appropriate MIME type
                        file_ext = os.path.splitext(local_path)[1].lower()
                        mime_type = "image/jpeg"  # Default
                        if file_ext == ".png":
                            mime_type = "image/png"
                        elif file_ext in [".jpg", ".jpeg"]:
                            mime_type = "image/jpeg"
                        
                        # Create a data URI directly
                        img_url = f"data:{mime_type};base64,{image_base64}"
                        
                        if self.verbose:
                            print(f"Using data URI for Runway (length: {len(img_url)} characters)")
                else:
                    # No ImgBB key, use data URI directly
                    # Determine the file extension and appropriate MIME type
                    file_ext = os.path.splitext(local_path)[1].lower()
                    mime_type = "image/jpeg"  # Default
                    if file_ext == ".png":
                        mime_type = "image/png"
                    elif file_ext in [".jpg", ".jpeg"]:
                        mime_type = "image/jpeg"
                    
                    # Create a data URI directly
                    img_url = f"data:{mime_type};base64,{image_base64}"
                    
                    if self.verbose:
                        print(f"Using data URI for Runway (length: {len(img_url)} characters)")
            except Exception as e:
                error_message = f"Error processing local image for Runway: {e}"
                if self.verbose:
                    print(error_message)
                raise RuntimeError(error_message) from e

        headers = {
            "Authorization": f"Bearer {self.runway_api_key}",
            "X-Runway-Version": "2024-11-06",
            "Content-Type": "application/json",
        }
        
        # Customize the prompt text based on the action
        if action == "birthday-dance":
            prompt_text = ("Seamless looped 2D animation of a chibi‑style puppy dancing happily with a birthday hat — "
                          "smooth, bouncy dance movements, joyful expression, flat pastel colours, "
                          "bold black outlines, subtle cel‑shading, clean light‑beige background, confetti falling, no cuts.")
        else:
            prompt_text = (f"Seamless looped 2D animation of a chibi‑style puppy {action} in place — "
                           "flat pastel colours, bold black outlines, smooth limb and ear motion, "
                           "subtle cel‑shading, clean light‑beige background, no cuts.")
        
        payload = {
            "promptImage": img_url,
            "model":       "gen4_turbo",
            "promptText":  prompt_text,
            "duration":    duration,
            "ratio":       RATIO_MAP[ratio],
        }
        if self.verbose:
            # Don't print the full data URI as it can be very long
            if img_url.startswith("data:"):
                display_url = f"{img_url[:30]}...{img_url[-10:]}"
                payload_display = payload.copy()
                payload_display["promptImage"] = display_url
                print(f"Runway payload: {json.dumps(payload_display, indent=2)}")
            else:
                print(f"Runway payload: {json.dumps(payload, indent=2)}")

        try:
            resp = requests.post(
                "https://api.dev.runwayml.com/v1/image_to_video", 
                headers=headers,
                json=payload,
                timeout=30,
            )
            resp.raise_for_status()
            task_id = resp.json()["id"]
            if self.verbose:
                print(f"Runway video generation task started. Task ID: {task_id}")
            return task_id
        except requests.exceptions.RequestException as e:
            error_message = f"Error starting Runway video generation: {e}"
            if hasattr(e, 'response') and e.response is not None:
                try:
                    error_details = e.response.json()
                    error_message += f" - Details: {error_details}"
                except json.JSONDecodeError:
                    error_message += f" - Response content: {e.response.text}"
            if self.verbose:
                print(error_message)
            raise RuntimeError(error_message) from e

    # Step 6b: Runway Status poller
    def check_runway_task_status(self, task_id: str) -> dict:
        if self.verbose:
            print(f"Checking Runway task status for ID: {task_id}")
        headers = {
            "Authorization": f"Bearer {self.runway_api_key}",
            "X-Runway-Version": "2024-11-06", 
        }
        url = f"https://api.dev.runwayml.com/v1/tasks/{task_id}" 
        try:
            resp = requests.get(url, headers=headers, timeout=15)
            resp.raise_for_status()
            status_data = resp.json()
            if self.verbose:
                print(f"Runway task status: {status_data.get('status', 'N/A')}")
            return status_data
        except requests.exceptions.RequestException as e:
            error_message = f"Error checking Runway task status for {task_id}: {e}"
            if hasattr(e, 'response') and e.response is not None:
                try:
                    error_details = e.response.json()
                    error_message += f" - Details: {error_details}"
                except json.JSONDecodeError:
                    error_message += f" - Response content: {e.response.text}"
            if self.verbose:
                print(error_message)
            raise RuntimeError(error_message) from e

    def wait_for_runway_video(self, task_id: str, first_wait: int = 30, poll: int = 5, max_tries: int = 40) -> dict:
        if self.verbose:
            print(f"Waiting for Runway video (task ID: {task_id}). Initial wait: {first_wait}s, poll interval: {poll}s, max tries: {max_tries}.")
        time.sleep(first_wait)
        for i in range(max_tries):
            if self.verbose:
                print(f"Polling Runway task {task_id} (attempt {i+1}/{max_tries})...")
            try:
                data = self.check_runway_task_status(task_id)
            except RuntimeError as e: 
                if self.verbose:
                    print(f"Polling attempt {i+1} failed: {e}. Retrying after {poll}s.")
                time.sleep(poll)
                continue 

            status = data.get("status")
            if status in ("SUCCEEDED", "COMPLETED"): 
                if self.verbose:
                    print(f"Runway task {task_id} {status}.")
                # Return the entire data object to extract URL later
                return data
            if status == "FAILED":
                error_details = data.get("error", "Runway task failed with no specific error message.")
                if self.verbose:
                    print(f"Runway task {task_id} FAILED. Details: {error_details}")
                raise RuntimeError(f"Runway task {task_id} failed: {error_details}")
            
            if self.verbose:
                print(f"Runway task {task_id} status: {status}. Waiting {poll} seconds...")
            time.sleep(poll)
        
        timeout_msg = f"Runway task {task_id} timed out after {max_tries} attempts."
        if self.verbose: print(timeout_msg)
        raise TimeoutError(timeout_msg)

    # New method to add music to a video
    def add_music_to_video(self, video_url, audio_path, output_path=None, total_duration=45):
        if self.verbose:
            print(f"Adding music from {audio_path} to video at {video_url}")
            print(f"Target total duration: {total_duration} seconds")
        
        if not os.path.exists(audio_path):
            error_msg = f"Audio file not found at path: {audio_path}"
            if self.verbose:
                print(error_msg)
            raise FileNotFoundError(error_msg)
        
        try:
            # Create temporary directory to store downloaded video
            with tempfile.TemporaryDirectory() as temp_dir:
                # Download the video if it's a URL
                video_path = os.path.join(temp_dir, "temp_video.mp4")
                if self.verbose:
                    print(f"① Loading video from {video_url}")
                    print(f"  Downloading to {video_path}")
                urllib.request.urlretrieve(video_url, video_path)
                
                # Load the video and audio using editor module for better compatibility
                if self.verbose:
                    print(f"② Loading video with VideoFileClip")
                video_clip = VideoFileClip(video_path)
                
                if self.verbose:
                    print(f"③ Loading audio from {audio_path}")
                audio_clip = AudioFileClip(audio_path)
                
                original_duration = video_clip.duration
                if self.verbose:
                    print(f"④ Original clip duration: {original_duration:.2f} seconds")
                
                # Calculate how many times we need to repeat the clip
                repeat_count = int(total_duration / original_duration) + 1
                if self.verbose:
                    print(f"⑤ Will repeat clip {repeat_count} times to reach target duration")
                    
                # Create the looped video by concatenating the clip with itself
                if self.verbose:
                    print(f"⑥ Creating looped video by concatenating {repeat_count} copies...")
                    
                # Use a more controlled approach to reach the target duration
                target_repeats = []
                current_duration = 0
                while current_duration < total_duration:
                    target_repeats.append(video_clip)
                    current_duration += original_duration
                    
                looped_video = concatenate_videoclips(target_repeats)
                if self.verbose:
                    print(f"⑦ Created looped video with duration {looped_video.duration:.2f} seconds")
                
                # Process the audio to match the total duration
                if self.verbose:
                    print(f"⑧ Processing audio (original duration: {audio_clip.duration:.2f}s)")
                
                # For audio processing, use the editor's AudioClip for better compatibility
                try:
                    if self.verbose:
                        print(f"   Converting to editor's AudioClip for compatibility")
                    # First, export to a temporary audio file
                    temp_audio_file = os.path.join(temp_dir, "temp_audio.mp3")
                    if self.verbose:
                        print(f"   Saving audio to temporary file: {temp_audio_file}")
                    audio_clip.write_audiofile(temp_audio_file, verbose=False, logger=None)
                    
                    # Reload with editor
                    if self.verbose:
                        print(f"   Reloading with AudioFileClip")
                    audio_clip = AudioFileClip(temp_audio_file)
                    
                    if self.verbose:
                        print(f"   Setting audio duration to {total_duration}s")
                    
                    # Handle duration
                    if audio_clip.duration > total_duration:
                        # Trim
                        audio_clip = audio_clip.subclip(0, total_duration)
                    elif audio_clip.duration < total_duration:
                        # Loop
                        audio_clip = audio_clip.fx(audio_clip.loop, duration=total_duration)
                    
                    if self.verbose:
                        print(f"⑨ Audio processed to duration {audio_clip.duration:.2f}s")
                        
                except Exception as e:
                    if self.verbose:
                        print(f"Warning: Error processing audio: {e}")
                        print("   Will try alternative methods")
                
                # Set the audio to the video
                if self.verbose:
                    print(f"⑩ Combining video and audio")
                
                try:
                    # Try different approaches to add audio to video
                    if hasattr(looped_video, 'set_audio'):
                        if self.verbose:
                            print("   Using set_audio method")
                        final_clip = looped_video.set_audio(audio_clip)
                    else:
                        if self.verbose:
                            print("   Using alternative method to combine audio and video")
                        # Create a new clip with MoviePy editor
                        # First save the video to a temporary file
                        temp_video_file = os.path.join(temp_dir, "temp_combined_video.mp4")
                        if self.verbose:
                            print(f"   Saving intermediate video to {temp_video_file}")
                        
                        # Write the looped video without audio
                        looped_video.write_videofile(
                            temp_video_file,
                            codec='libx264',
                            audio=False,  # No audio
                            verbose=self.verbose,
                            fps=24,
                            logger=None
                        )
                        
                        # Now read it back with MoviePy editor which has set_audio
                        if self.verbose:
                            print(f"   Loading video with VideoFileClip")
                        video_with_editor = VideoFileClip(temp_video_file)
                        
                        # Add audio
                        if self.verbose:
                            print(f"   Adding audio track")
                        final_clip = video_with_editor.set_audio(audio_clip)
                        
                except Exception as e:
                    if self.verbose:
                        print(f"Warning: Error combining audio and video: {e}")
                        print("   Writing video without audio")
                    final_clip = looped_video
                
                # Determine output path
                if output_path is None:
                    # Generate a unique filename in the current directory
                    base_filename = "chibi_clip_with_music"
                    output_path = f"{base_filename}_{int(time.time())}.mp4"
                
                # Write the result to a file
                if self.verbose:
                    print(f"⑪ Writing {total_duration:.2f} second video with music to {output_path}")
                    print(f"   This may take some time...")
                final_clip.write_videofile(
                    output_path, 
                    codec='libx264', 
                    audio_codec='aac', 
                    verbose=self.verbose,
                    fps=24,  # Explicit fps value
                    logger=None  # Disable logger to avoid extra output
                )
                
                # Close the clips to release resources
                if self.verbose:
                    print(f"⑫ Closing video and audio resources")
                video_clip.close()
                audio_clip.close()
                if 'looped_video' in locals(): looped_video.close()
                if 'final_clip' in locals(): final_clip.close()
                if 'video_with_editor' in locals() and 'video_with_editor' in vars(): video_with_editor.close()
                
                if self.verbose:
                    print(f"✅ Video with music saved to {output_path}")
                return output_path
        except Exception as e:
            error_message = f"Error adding music to video: {e}"
            if self.verbose:
                print(error_message)
            raise RuntimeError(error_message) from e

    # Step 7: High-level orchestrator (Updated to handle local file URLs)
    def process_clip(self, photo_path: str, action: str = "running", ratio: str = "9:16", duration: int = 5, audio_path: str = None, extended_duration: int = 45, use_local_storage=False):
        if self.verbose:
            print(f"▶ Generating clip (source: {photo_path}, action: {action}, ratio: {ratio}, duration: {duration}s)…")

        try:
            prompt = self.generate_ai_prompt(action)
            
            if self.verbose:
                print(f"Reading photo from: {photo_path}")
            with open(photo_path, "rb") as f:
                image_content = BytesIO(f.read())
            
            # Get appropriate image size based on selected ratio
            image_size = IMAGE_SIZE_MAP.get(ratio, "1024x1024")
            if self.verbose:
                print(f"Using image size {image_size} for ratio {ratio}")

            edited_b64 = self.edit_image_with_openai(image_content, prompt, image_size)
            
            # Use local storage or ImgBB based on user preference
            if use_local_storage:
                # Save image locally and get URL
                local_result = self.save_image_locally(edited_b64)
                img_url = local_result["url"]
                local_image_path = local_result["path"]
            else:
                # Try ImgBB with fallback to local storage if it fails
                img_url = self.upload_to_imgbb(edited_b64, use_local_fallback=True)
                local_image_path = None
                
                # Check if the result is a local file URL
                if img_url.startswith("file://"):
                    local_image_path = img_url[7:]  # Remove file:// prefix
            
            task_id    = self.generate_runway_video(img_url, action, ratio, duration)
            task_result = self.wait_for_runway_video(task_id)
            
            # Extract the video URL from the task_result correctly
            if "output" not in task_result or not task_result["output"]:
                raise RuntimeError(f"No output found in Runway task result: {task_result}")
            
            video_url = task_result["output"][0]
            
            # Add music to the video if an audio path is provided
            local_video_path = None
            if audio_path and os.path.exists(audio_path):
                if self.verbose:
                    print(f"Adding music from {audio_path} to video")
                local_video_path = self.add_music_to_video(video_url, audio_path, total_duration=extended_duration)
            
            result = {"image_url": img_url, "video_url": video_url}
            if local_image_path:
                result["local_image_path"] = local_image_path
            if local_video_path:
                result["local_video_path"] = local_video_path
                result["extended_duration"] = extended_duration
            
            if self.verbose:
                print(f"✅ Clip processing complete. Image: {img_url}, Video: {video_url}")
                if local_image_path:
                    print(f"Local image saved to: {local_image_path}")
                if local_video_path:
                    print(f"Extended video with music ({extended_duration}s) saved to: {local_video_path}")
            
            return result

        except FileNotFoundError:
            if self.verbose: print(f"Error: Input photo_path '{photo_path}' not found.")
            raise
        except ValueError as ve: 
            if self.verbose: print(f"Configuration or Parameter Error: {ve}")
            raise
        except RuntimeError as re: 
            if self.verbose: print(f"Runtime Error during clip processing: {re}")
            raise
        except TimeoutError as te:
            if self.verbose: print(f"Timeout Error during clip processing: {te}")
            raise
        except Exception as e: 
            if self.verbose: print(f"An unexpected error occurred: {e}")
            raise

# Step 9: CLI entry point (Updated to include local storage option)
if __name__ == "__main__":
    import argparse 
    # json is already imported at the top
    # os is already imported at the top

    try:
        from dotenv import load_dotenv
        script_dir = os.path.dirname(os.path.abspath(__file__))
        dotenv_path_script = os.path.join(script_dir, '.env')
        dotenv_path_cwd = os.path.join(os.getcwd(), '.env')

        if os.path.exists(dotenv_path_script):
            load_dotenv(dotenv_path=dotenv_path_script, override=True)
            if os.getenv("VERBOSE_DOTENV") == 'true': print(f"Loaded .env from {dotenv_path_script}")
        elif os.path.exists(dotenv_path_cwd):
            load_dotenv(dotenv_path=dotenv_path_cwd, override=True)
            if os.getenv("VERBOSE_DOTENV") == 'true': print(f"Loaded .env from {dotenv_path_cwd}")
        elif load_dotenv(override=True):
            if os.getenv("VERBOSE_DOTENV") == 'true': print("Loaded .env from standard search path.")
        else:
            if os.getenv("VERBOSE_DOTENV") == 'true': print("No .env file found. Relying on environment variables.")
    except ImportError:
        if os.getenv("VERBOSE_DOTENV") == 'true': print("python-dotenv not installed. Skipping .env file loading.")

    ap = argparse.ArgumentParser(description="ChibiClip Generator: Create animated video clips from photos.")
    ap.add_argument("photo", help="Path to the input photo of the dog.")
    ap.add_argument("--action", default="running", 
                    choices=["running", "tail-wagging", "jumping", "birthday-dance"], 
                    help="Action the dog should perform in the animation.")
    ap.add_argument("--ratio", default="9:16", choices=["9:16", "16:9", "1:1"],
                    help="Aspect ratio for the output video.")
    ap.add_argument("--duration", default=5, type=int, choices=[5, 10],
                    help="Duration of the video in seconds (5 or 10).")
    ap.add_argument("--audio", help="Path to an audio file to add to the video.")
    ap.add_argument("--extended-duration", type=int, default=45,
                    help="Total duration in seconds for the extended video with music (default: 45)")
    ap.add_argument("--verbose", action="store_true", help="Enable verbose logging.")
    ap.add_argument("--use-local-storage", action="store_true",
                    help="Save images locally instead of uploading to ImgBB")
    ap.add_argument("--output-dir", help="Directory to save locally stored images and videos")
    args = ap.parse_args()

    try:
        gen = ChibiClipGenerator(
            openai_api_key=os.getenv("OPENAI_API_KEY"),
            imgbb_api_key=os.getenv("IMGBB_API_KEY"),
            runway_api_key=os.getenv("RUNWAY_API_KEY"),
            verbose=args.verbose,
            output_dir=args.output_dir
        )
        
        res = gen.process_clip(
            photo_path=args.photo, 
            action=args.action, 
            ratio=args.ratio, 
            duration=args.duration,
            audio_path=args.audio,
            extended_duration=args.extended_duration,
            use_local_storage=args.use_local_storage
        )
        
        print("\n✨ Clip Generation Result ✨") 
        print(json.dumps(res, indent=2, ensure_ascii=False))

        if res.get("video_url"):
             print(f"\nVideo is available at: {res['video_url']}")
        if res.get("image_url"):
            print(f"Edited image is available at: {res['image_url']}")
        if res.get("local_image_path"):
            print(f"Local image saved to: {res['local_image_path']}")
        if res.get("local_video_path"):
            print(f"Extended video with music ({res.get('extended_duration', 45)}s) saved to: {res['local_video_path']}")

    except ValueError as e: 
        print(f"Error: {e}")
        if "Missing API key(s)" in str(e):
            print("Please ensure OPENAI_API_KEY and RUNWAY_API_KEY are set in your .env file or environment.")
            print("ImgBB API key is optional if using local storage.")
    except FileNotFoundError:
        print(f"Error: Input photo file not found at '{args.photo}'")
    except RuntimeError as e:
        print(f"An error occurred during processing: {e}")
    except TimeoutError as e:
        print(f"A timeout error occurred: {e}")
    except Exception as e: 
        print(f"An unexpected critical error occurred: {e}")
        import traceback
        traceback.print_exc() 