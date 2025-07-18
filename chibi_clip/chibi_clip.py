import os
import requests
import json
import time
import base64
from io import BytesIO
import urllib.request
import tempfile
import numpy as np
from PIL import Image, ImageFile, ImageDraw, ImageFont
import imghdr
# Import specific modules from moviepy
from moviepy.video.io.VideoFileClip import VideoFileClip
from moviepy.audio.io.AudioFileClip import AudioFileClip
from moviepy.video.compositing.concatenate import concatenate_videoclips
from moviepy.audio.AudioClip import AudioClip
from moviepy.audio.AudioClip import concatenate_audioclips  # Add proper import for audio concatenation
from moviepy.video.compositing.CompositeVideoClip import CompositeVideoClip # Ensure this is imported
from moviepy.video.VideoClip import ImageClip, TextClip # Import ImageClip and TextClip
# Import resize with fallback for newer PIL versions
try:
    from moviepy.video.fx.resize import resize
except Exception as e:
    # Create a custom resize function that works with newer PIL versions
    def resize(clip, width=None, height=None, newsize=None):
        """
        Resizes a clip to a new resolution.
        
        Parameters
        ----------
        clip : VideoClip
            A video clip
        width : int, optional
            New width of the clip
        height : int, optional
            New height of the clip
        newsize : tuple, optional
            New size (width, height) of the clip
            
        Returns
        -------
        clip : VideoClip
            A clip with the new resolution
        """
        from moviepy.video.fx.resize import resize_func
        from PIL import Image
        
        if newsize is not None:
            width, height = newsize
        elif width is not None:
            if height is None:
                height = int(clip.h * width / clip.w)
        elif height is not None:
            if width is None:
                width = int(clip.w * height / clip.h)
        else:
            return clip  # No resizing needed
            
        newsize = (width, height)
        
        # Get the proper resampling filter
        resample_filter = None
        # Check which PIL/Pillow constants are available
        if hasattr(Image, 'LANCZOS'):
            resample_filter = Image.LANCZOS
        elif hasattr(Image, 'Resampling') and hasattr(Image.Resampling, 'LANCZOS'):
            resample_filter = Image.Resampling.LANCZOS
        elif hasattr(Image, 'ANTIALIAS'):
            resample_filter = Image.ANTIALIAS
        else:
            # Fallback to BICUBIC
            if hasattr(Image, 'BICUBIC'):
                resample_filter = Image.BICUBIC
            elif hasattr(Image, 'Resampling') and hasattr(Image.Resampling, 'BICUBIC'):
                resample_filter = Image.Resampling.BICUBIC
                
        # Custom resize function that uses the determined resampling filter
        def resizer(pic, newsize):
            newpic = Image.fromarray(pic)
            newpic = newpic.resize(newsize[::-1], resample_filter)
            return np.array(newpic)
            
        # Apply the resize
        newclip = clip.fl_image(lambda pic: resizer(pic.astype('uint8'), newsize))
        
        if hasattr(clip, 'fps'):
            newclip.fps = clip.fps
        if hasattr(clip, 'audio'):
            newclip.audio = clip.audio
            
        return newclip

# Import these directly from the moviepy package
import moviepy
# argparse and random will be imported in their respective scopes
import uuid
import shutil

# Try to import magic and subprocess for file type detection
try:
    import magic
    MAGIC_AVAILABLE = True
except ImportError:
    print("Warning: python-magic library not found or libmagic not installed. File type detection will be limited.")
    MAGIC_AVAILABLE = False

try:
    import subprocess
    SUBPROCESS_AVAILABLE = True
except ImportError:
    print("Warning: subprocess module not found. Fallback file type detection may be limited.")
    SUBPROCESS_AVAILABLE = False

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

# Allow Pillow to load truncated images
ImageFile.LOAD_TRUNCATED_IMAGES = True

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
            
    # New helper method to convert images to PNG using ffmpeg
    def _to_png(self, src_path: str) -> str:
        """
        Converts an image file to PNG format using ffmpeg.
        Overwrites the original file with the PNG version.
        Returns the path to the (potentially) converted file.
        """
        if self.verbose:
            print(f"Attempting to convert {src_path} to PNG using ffmpeg...")
        
        # Guard: Check if src_path is a recognized image before attempting conversion
        image_type_for_conversion = imghdr.what(src_path)
        if image_type_for_conversion is None:
            # Attempt to read header for logging if conversion is aborted
            header_for_log = ""
            try:
                with open(src_path, "rb") as f_header:
                    header_for_log = f_header.read(16).hex()
            except Exception:
                header_for_log = "Could not read header"
            raise RuntimeError(
                f"{src_path} is not a recognised bitmap image – aborting conversion. "
                f"imghdr type: None. Header (first 16 bytes): {header_for_log}"
            )
        if self.verbose:
            print(f"chibi_clip._to_png: imghdr identified source as '{image_type_for_conversion}' before ffmpeg conversion.")

        # Create a temporary name for the output PNG
        temp_png_path = tempfile.mktemp(suffix=".png", prefix="converted_", dir=self.output_dir or "/tmp")
        
        try:
            # Ensure output directory exists if self.output_dir is used
            if self.output_dir and not os.path.exists(self.output_dir):
                os.makedirs(self.output_dir, exist_ok=True)

            # Command to convert to PNG using ffmpeg
            # -y: overwrite output files without asking
            # -i: input file
            # -vf "alphaextract,format=rgba,alphamerge": attempt to preserve transparency if present
            # Note: More complex alpha preservation might be needed depending on source
            # For simplicity, basic conversion first. If alpha is critical, this can be expanded.
            cmd = [
                "ffmpeg", "-y", "-i", src_path, 
                "-vf", "format=rgba", # Try to ensure RGBA for PNG output
                temp_png_path
            ]
            if self.verbose:
                print(f"Executing ffmpeg command: {' '.join(cmd)}")
            
            # Run ffmpeg
            # Use DEVNULL for stdout/stderr to avoid excessive console output unless debugging
            result = subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
            
            if self.verbose:
                print(f"ffmpeg conversion successful. Output at {temp_png_path}")
            
            # Replace the original file with the converted PNG
            shutil.move(temp_png_path, src_path)
            if self.verbose:
                print(f"Replaced {src_path} with its PNG version.")
            return src_path
        except subprocess.CalledProcessError as e:
            if self.verbose:
                print(f"ffmpeg conversion failed for {src_path}. Error: {e.stderr.decode() if e.stderr else e}")
            # Clean up temp file if conversion failed
            if os.path.exists(temp_png_path):
                try:
                    os.remove(temp_png_path)
                except OSError:
                    pass # Ignore if removal fails
            raise RuntimeError(f"Failed to convert {src_path} to PNG with ffmpeg: {e}") from e
        except FileNotFoundError: # ffmpeg not found
             if self.verbose:
                print("ffmpeg command not found. Cannot convert image. Ensure ffmpeg is installed and in PATH.")
             raise RuntimeError("ffmpeg not found. Conversion to PNG failed.")
        except Exception as e_move:
            if self.verbose:
                print(f"Error during moving/cleanup of converted file: {e_move}")
            # Clean up temp file if move failed
            if os.path.exists(temp_png_path):
                try:
                    os.remove(temp_png_path)
                except OSError:
                    pass
            raise RuntimeError(f"Error post-conversion for {src_path}: {e_move}") from e_move

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
        Preprocess image for OpenAI API by:
        1. Ensuring it's a PNG with transparency (RGBA mode)
        2. Resizing if needed to keep within size limits
        3. Ensuring proper format for OpenAI's API

        OpenAI's image-edits endpoint requires:
        - PNG format with transparency (RGBA mode)
        - Square image is best
        - File size under 4MB
        """
        if self.verbose:
            print("Preprocessing image for OpenAI API...")
        
        # Check if BytesIO contains data
        if image_content.getbuffer().nbytes == 0:
            raise ValueError("Image content is empty")
            
        # Check initial size
        initial_size = len(image_content.getvalue()) / (1024 * 1024)
        if self.verbose:
            print(f"Original image size: {initial_size:.2f} MB")
            
        # Print the first few bytes to help with debugging
        image_content.seek(0)
        header_bytes = image_content.read(20)
        if self.verbose:
            print(f"Image header bytes: {header_bytes.hex()}")
            
        # Reset the BytesIO pointer to the start
        image_content.seek(0)
        
        # Load image with PIL
        try:
            img = Image.open(image_content)
            orig_format = img.format
            if self.verbose:
                print(f"Image format: {orig_format}, Mode: {img.mode}, Size: {img.size}")
        except Exception as e:
            if self.verbose:
                print(f"Error loading image: {e}")
                
            # Try to save the contents to a file for debugging
            try:
                image_content.seek(0)
                debug_bytes = image_content.getvalue()
                debug_path = "/tmp/debug_image_error.bin"
                with open(debug_path, "wb") as f:
                    f.write(debug_bytes)
                print(f"Saved problematic image data to {debug_path} for debugging")
            except Exception as save_error:
                print(f"Failed to save debug file: {save_error}")
                
            raise ValueError(f"Could not load image: {e}")
        
        # Convert to RGBA mode (with transparency) - required for OpenAI image edits
        if img.mode != 'RGBA':
            if self.verbose:
                print(f"Converting image from {img.mode} to RGBA mode")
            img = img.convert('RGBA')
        
        # Resize if needed to reduce file size
        while True:
            # Save to a new BytesIO buffer
            processed_buffer = BytesIO()
            img.save(processed_buffer, format='PNG')
            processed_buffer.seek(0)
            
            processed_size = len(processed_buffer.getvalue()) / (1024 * 1024)
            if self.verbose:
                print(f"Processed image size: {processed_size:.2f} MB")
            
            # Check if size is within limit
            if processed_size <= max_size_mb:
                break
            
            # Resize if too large (reduce by 25% each time)
            new_width = int(img.width * 0.75)
            new_height = int(img.height * 0.75)
            if self.verbose:
                print(f"Resizing image from {img.width}x{img.height} to {new_width}x{new_height}")
            img = img.resize((new_width, new_height))
        
        if self.verbose:
            print(f"Final image mode: {img.mode}, Size: {img.size}, File size: {processed_size:.2f} MB")
        
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
        
        # Preprocess the image to ensure it's not too large and in the right format (PNG with transparency)
        processed_image = self._preprocess_image_for_openai(image_content)
        
        headers = {
            "Authorization": f"Bearer {self.openai_api_key}"
        }
        
        image_bytes = processed_image.getvalue()
        
        # Always use PNG format for image-edits endpoint
        content_type = 'image/png'
        extension = '.png'
        
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
        # If use_local_fallback is True, just return a data URI directly
        # This avoids the memory spike from multipart/form-data buffer during ImgBB upload
        if use_local_fallback:
            if self.verbose:
                print("Using data URI directly to avoid memory overhead of ImgBB upload")
            # Create a data URI from the base64 data
            return f"data:image/png;base64,{image_base64}"
        
        if not self.imgbb_api_key:
            if self.verbose:
                print("No ImgBB API key provided and local fallback disabled.")
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
                # If we only have a local file, convert it straight to a data-URI.
                # This avoids the extra memory spike of an ImgBB upload and works
                # fine with the Runway endpoint.
                with open(local_path, "rb") as f:
                    image_data = f.read()
                
                # Convert to base64
                image_base64 = base64.b64encode(image_data).decode('utf-8')
                
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
                    
                    # Check for the specific "Failed to fetch asset" error with 502 status
                    if img_url.startswith("http") and "Failed to fetch asset" in str(error_details) and "502" in str(error_details):
                        if self.verbose:
                            print(f"Runway couldn't access the image URL due to a 502 error. Trying with data URI instead.")
                        
                        try:
                            # Attempt to download the image from the URL
                            if self.verbose:
                                print(f"Downloading image from URL: {img_url}")
                            
                            # Create a temporary file to save the image
                            temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".png")
                            temp_path = temp_file.name
                            temp_file.close()
                            
                            # Use requests instead of urllib for better error handling
                            response = requests.get(img_url, timeout=30)
                            response.raise_for_status()
                            
                            # Save the image content
                            with open(temp_path, 'wb') as f:
                                f.write(response.content)
                            
                            if os.path.exists(temp_path):
                                if self.verbose:
                                    print(f"Downloaded image to temporary file: {temp_path}")
                                
                                # Read the image from the temp file
                                with open(temp_path, "rb") as f:
                                    image_data = f.read()
                                
                                # Convert to base64
                                image_base64 = base64.b64encode(image_data).decode('utf-8')
                                
                                # Default to PNG mime type since we saved as PNG
                                mime_type = "image/png"
                                
                                # Create a data URI directly
                                img_url = f"data:{mime_type};base64,{image_base64}"
                                
                                # Update payload with new data URI
                                payload["promptImage"] = img_url
                                
                                if self.verbose:
                                    display_url = f"{img_url[:30]}...{img_url[-10:]}" 
                                    print(f"Retrying with data URI (length: {len(img_url)} characters)")
                                
                                # Try again with data URI
                                resp = requests.post(
                                    "https://api.dev.runwayml.com/v1/image_to_video", 
                                    headers=headers,
                                    json=payload,
                                    timeout=30,
                                )
                                resp.raise_for_status()
                                task_id = resp.json()["id"]
                                if self.verbose:
                                    print(f"Runway video generation task started with data URI. Task ID: {task_id}")
                                
                                # Clean up temp file
                                try:
                                    os.unlink(temp_path)
                                except Exception as clean_err:
                                    if self.verbose:
                                        print(f"Warning: Could not delete temp file {temp_path}: {clean_err}")
                                    
                                return task_id
                        except Exception as download_err:
                            if self.verbose:
                                print(f"Error trying to use data URI fallback: {download_err}")
                                print("Continuing with original error")
                
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

    # Step 7b: Music addition helper method
    def add_music_to_video(self, video_url, audio_path, output_path=None, total_duration=45, birthday_message=None):
        """
        Adds music to a video, adjusting if needed to match the desired duration.
        If the video is shorter than total_duration, it's looped.
        If the audio is shorter than total_duration, it's looped.
        
        Args:
            video_url (str): URL or path to the video file
            audio_path (str): Path to the audio file
            output_path (str, optional): Path where the output will be saved
            total_duration (int, optional): Target duration in seconds. Defaults to 45.
            birthday_message (str, optional): Birthday message to add to the card slate
            
        Returns:
            str: Path to the output file
        """
        if self.verbose:
            print(f"Adding music from {audio_path} to video at {video_url}")
            print(f"Target total duration: {total_duration} seconds")
            if birthday_message:
                print(f"Birthday message to add: {birthday_message}")
        
        try:
            # Create a temp dir for working files
            temp_dir = tempfile.mkdtemp()
            video_clip_obj = None
            audio_obj = None
            final_animated_video_obj = None
            final_video_to_write = None
            
            if self.verbose:
                print(f"① Downloading video from {video_url} to {os.path.join(temp_dir, 'temp_video.mp4')}")
            
            # First, download the video file to a temp location
            video_path = os.path.join(temp_dir, "temp_video.mp4")
            
            # Handle different URL types (http, file, local path)
            if video_url.startswith(('http://', 'https://')):
                # Remote URL - use requests for better error handling and content type checking
                try:
                    r = requests.get(video_url, timeout=60, stream=True) # Added stream=True
                    r.raise_for_status() # Check for HTTP errors
                    
                    content_type = r.headers.get("Content-Type", "")
                    if self.verbose:
                        print(f"   Downloaded video content type: {content_type}")
                    if content_type.startswith("text/") or content_type.startswith("application/xml") or content_type.startswith("application/json"):
                        # Try to get some content for debugging if it's text
                        preview = ""
                        try:
                            preview = r.text[:200] # Read a bit of the text response
                        except Exception:
                            pass
                        raise RuntimeError(
                            f"Expected video, got {content_type} from {video_url}. Response preview: '{preview}...'"
                        )

                    with open(video_path, 'wb') as f:
                        for chunk in r.iter_content(chunk_size=8192): # Download in chunks
                            f.write(chunk)
                    if self.verbose:
                        print(f"   Video downloaded successfully to {video_path} using requests.")
                except requests.exceptions.RequestException as req_e:
                    raise RuntimeError(f"Error downloading video from {video_url} using requests: {req_e}") from req_e
            elif video_url.startswith('file://'):
                # Local file URL - copy the file
                local_path = video_url[7:]  # Remove file:// prefix
                shutil.copyfile(local_path, video_path)
            else:
                # Assume it's already a local file path
                if os.path.exists(video_url):
                    shutil.copyfile(video_url, video_path)
                else:
                    raise ValueError(f"Invalid video_url: {video_url}. Not a valid URL or file path.")
            
            # Load the video clip - MEMORY OPTIMIZATION: Using context manager and memory-saving parameters
            if self.verbose:
                print(f"② Loading video with VideoFileClip from: {video_path}")
            try:
                # Memory optimizations:
                # 1. audio=False: Don't load the audio track from the video, we'll add our own
                # 2. target_resolution: Downscale the video during loading to conserve memory
                # 3. Using context manager to ensure resources are cleaned up
                with VideoFileClip(video_path, audio=False, target_resolution=(480, None)) as original_clip:
                    if self.verbose:
                        print(f"   Original video dimensions: {original_clip.size}, duration: {original_clip.duration:.2f}s")
                    
                    # Get the original duration
                    original_duration = original_clip.duration
                    
                    # Create a more memory-efficient version of the clip by adjusting fps if needed
                    target_fps = min(25, original_clip.fps) if hasattr(original_clip, 'fps') and original_clip.fps > 25 else None
                    
                    if target_fps and target_fps < original_clip.fps:
                        if self.verbose:
                            print(f"   Optimizing frame rate from {original_clip.fps} to {target_fps} fps to reduce memory usage")
                        # Make a copy with lower fps
                        video_clip_obj = original_clip.set_fps(target_fps)
                    else:
                        # Create a copy of the clip to ensure we don't close the original when we close video_clip_obj
                        # We need to keep video_clip_obj separate since it will be modified further
                        video_clip_obj = original_clip.copy()
                
                if self.verbose:
                    print(f"③ Original clip duration: {original_duration:.2f} seconds")

                # If the video is shorter than target_duration, we'll loop it
                if original_duration < total_duration:
                    if self.verbose:
                        print(f"   Starting loop to create video of {total_duration}s duration.")

                    # Initialize tracking variables for the loop
                    clips_for_concatenation = []
                    accumulated_duration = 0
                    loop_count = 0
                    
                    # Process in chunks to reduce memory usage
                    try:
                        # Keep adding segments until we reach total_duration
                        while accumulated_duration < total_duration:
                            loop_count += 1
                            remaining_needed = total_duration - accumulated_duration
                            
                            # Determine the duration for this specific segment
                            duration_this_segment = min(original_duration, remaining_needed)

                            # If this segment will be a FULL loop of the original clip (i.e., not the potentially shorter final segment)
                            # AND if it's not the very last piece needed (to avoid trimming the very end)
                            # then trim a tiny fraction from the end to potentially smooth the loop transition.
                            trim_end_offset = 0.05 # Trim 50ms (adjust if needed)
                            subclip_end_time = duration_this_segment
                            
                            # Check if this segment covers most of the original duration AND if adding another full original duration wouldn't exceed the total needed.
                            if duration_this_segment >= original_duration - trim_end_offset and (accumulated_duration + original_duration < total_duration + trim_end_offset): # Added tolerance to condition
                                 subclip_end_time = original_duration - trim_end_offset
                                 if self.verbose:
                                     print(f"   Trimming end of full loop segment. Using duration: {subclip_end_time:.2f}s")
                            
                            if self.verbose:
                                print(f"   Loop {loop_count}: Creating segment. Target duration for segment: {subclip_end_time:.2f}s.")
                                
                            # Create a segment from the video clip object
                            segment = video_clip_obj.subclip(0, subclip_end_time)
                            clips_for_concatenation.append(segment)
                            accumulated_duration += segment.duration 
                            if self.verbose:
                                 print(f"   Loop {loop_count}: Segment created with duration {segment.duration:.2f}s. Accumulated: {accumulated_duration:.2f}s.")
                                 
                            # Reduce memory pressure by processing in smaller batches if we have too many segments
                            if len(clips_for_concatenation) >= 4 and accumulated_duration < total_duration:
                                if self.verbose:
                                    print(f"   Memory optimization: Concatenating intermediate batch of {len(clips_for_concatenation)} segments.")
                                # Concatenate current segments and replace the list with just this one concatenated clip
                                intermediate_concat = concatenate_videoclips(clips_for_concatenation, method="compose")
                                
                                # Clear the list and replace with the concatenated result
                                for clip in clips_for_concatenation:
                                    if hasattr(clip, 'close') and clip != video_clip_obj:
                                        clip.close()
                                
                                clips_for_concatenation = [intermediate_concat]

                        # Concatenate all segments into the final video
                        if self.verbose:
                            print(f"④ Concatenating {len(clips_for_concatenation)} video segments.")
                        final_animated_video_obj = concatenate_videoclips(clips_for_concatenation, method="compose")
                        
                        # Close segment clips to free memory
                        for clip in clips_for_concatenation:
                            if hasattr(clip, 'close') and clip != final_animated_video_obj:
                                clip.close()
                        clips_for_concatenation = []
                    
                    except MemoryError as mem_err:
                        if self.verbose:
                            print(f"Memory error during video processing: {mem_err}. Trying a more conservative approach.")
                        
                        # Cleanup existing objects
                        for clip in clips_for_concatenation:
                            if hasattr(clip, 'close'):
                                try: clip.close()
                                except: pass
                        
                        if video_clip_obj and hasattr(video_clip_obj, 'close'):
                            try: video_clip_obj.close()
                            except: pass
                        
                        # Retry with FFmpeg shell command for looping - much more memory efficient
                        ffmpeg_input = os.path.join(temp_dir, "temp_video.mp4")
                        ffmpeg_output = os.path.join(temp_dir, "looped_video.mp4")
                        
                        # Calculate loop count needed (rounded up)
                        import math
                        loop_count = math.ceil(total_duration / original_duration)
                        if self.verbose:
                            print(f"   Falling back to FFmpeg for looping: will repeat video {loop_count} times.")
                        
                        # Use FFmpeg's -stream_loop parameter to repeat the input file
                        # -stream_loop N repeats the input N+1 times, so we subtract 1
                        loop_cmd = [
                            "ffmpeg", "-y",
                            "-stream_loop", str(loop_count - 1),
                            "-i", ffmpeg_input,
                            "-c", "copy",  # Just copy, don't re-encode
                            "-t", str(total_duration),  # Limit to desired duration
                            ffmpeg_output
                        ]
                        
                        if self.verbose:
                            print(f"   Running FFmpeg command: {' '.join(loop_cmd)}")
                        
                        try:
                            subprocess.run(loop_cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                            # Now load the looped video
                            # Use conservative memory settings
                            final_animated_video_obj = VideoFileClip(
                                ffmpeg_output, 
                                audio=False,
                                target_resolution=(480, None)
                            )
                            if final_animated_video_obj.duration > total_duration:
                                final_animated_video_obj = final_animated_video_obj.subclip(0, total_duration)
                        except subprocess.CalledProcessError as e_ffmpeg:
                            if self.verbose:
                                print(f"   FFmpeg fallback failed: {e_ffmpeg}")
                            raise RuntimeError(f"Failed to loop video with FFmpeg: {e_ffmpeg}")
                        
                else:
                    # If the video is longer than target_duration, trim it
                    if self.verbose:
                        print(f"④ Trimming video from {original_duration:.2f}s to {total_duration:.2f}s")
                    final_animated_video_obj = video_clip_obj.subclip(0, total_duration)
                    # Close the original clip to free up resources
                    if video_clip_obj and video_clip_obj != final_animated_video_obj:
                        video_clip_obj.close()
                    video_clip_obj = None

                # Now handle the audio
                if audio_path:
                    # Load the audio file
                    if self.verbose:
                        print(f"⑤ Loading audio from {audio_path}")
                    audio_obj = AudioFileClip(audio_path)
                    
                    # If the audio is shorter than target_duration, loop it
                    if audio_obj.duration < total_duration:
                        if self.verbose:
                            print(f"⑥ Audio ({audio_obj.duration:.2f}s) is shorter than target ({total_duration}s). Looping with FFmpeg.")
                        temp_audio_path = os.path.join(temp_dir, "extended_audio.mp3")
                        
                        # Using -stream_loop. Number of loops for input stream. -1 means infinite. We need total_duration.
                        # FFmpeg stream_loop counts from 0. So N-1 for N loops.
                        # Simpler: use -t to set output duration and let ffmpeg handle loop internally if input is too short with -loop 1 for input file
                        # Forcing audio loop through re-encoding to a temporary file of target duration
                        cmd = [
                            "ffmpeg",
                            "-i", audio_path, # Original audio path
                            "-af", f"aloop=loop=-1:size={int(2**24)}:start=0,atrim=0:{total_duration}", # Loop and trim audio with filters
                            "-c:a", "aac", # Re-encode to AAC for compatibility
                            "-b:a", "192k",
                            "-y", temp_audio_path
                        ]
                        if self.verbose:
                            print(f"   Running FFmpeg for audio loop: {' '.join(cmd)}")
                        try:
                            subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                            audio_obj.close()
                            audio_obj = AudioFileClip(temp_audio_path)
                            if self.verbose:
                                print(f"   Looped audio created. New duration: {audio_obj.duration:.2f}s")
                        except subprocess.CalledProcessError as e:
                            if self.verbose:
                                print(f"   ERROR: FFmpeg audio looping failed. Stdout: {e.stdout.decode() if e.stdout else 'N/A'}, Stderr: {e.stderr.decode() if e.stderr else 'N/A'}")
                                print(f"   Falling back to MoviePy audio subclip/loop if possible (might be inaccurate).")
                            # Fallback to simple trim/extend if FFmpeg fails (less accurate looping)
                            if audio_obj.duration > total_duration: audio_obj = audio_obj.subclip(0, total_duration)
                            # MoviePy loop for audio is not reliable for precise duration, so FFmpeg is preferred.

                    elif audio_obj.duration > total_duration:
                        if self.verbose:
                            print(f"⑦ Trimming audio from {audio_obj.duration:.2f}s to {total_duration:.2f}s")
                        audio_obj = audio_obj.subclip(0, total_duration)
                    
                    if self.verbose:
                        print(f"⑧ Setting audio (duration: {audio_obj.duration:.2f}s) to video (duration: {final_animated_video_obj.duration:.2f}s)")
                    final_animated_video_obj = final_animated_video_obj.set_audio(audio_obj)
                
                # --- BIRTHDAY CARD SLATE LOGIC START ---
                final_video_to_write = final_animated_video_obj # Default to the animated video
                card_slate = None 
                backdrop_clip = None
                txt_clip = None

                if birthday_message and birthday_message.strip():
                    if self.verbose:
                        print(f"INFO: Creating birthday card slate with message: '{birthday_message}'")
                    try:
                        # MAJOR CHANGE: Completely bypass MoviePy's TextClip/ImageClip for the birthday card
                        # due to ImageMagick security policy issues in containerized environments
                        assets_dir = os.path.join(os.path.dirname(__file__), "assets")
                        
                        # Choose the backdrop image
                        if video_width == 720 and video_height == 1280:
                            backdrop_path = os.path.join(assets_dir, "birthday_card_backdrop_v2.png")
                            if not os.path.exists(backdrop_path):
                                backdrop_path = os.path.join(assets_dir, "birthday_card_backdrop.png")
                        else:
                            backdrop_path = os.path.join(assets_dir, "birthday_card_backdrop.png")
                        
                        if not os.path.exists(backdrop_path):
                            if self.verbose:
                                print(f"WARNING: No backdrop images found. Skipping card slate.")
                            # Just proceed with the animated clip only
                        else:
                            # Create a static image with text using PIL instead of TextClip
                            if self.verbose: print(f"INFO: Creating card slate using PIL and FFmpeg (bypassing MoviePy)")
                            
                            # 1. Open and resize the backdrop
                            backdrop_img = Image.open(backdrop_path)
                            if backdrop_img.size != (video_width, video_height):
                                if self.verbose: print(f"INFO: Resizing backdrop to {video_width}x{video_height}")
                                backdrop_img = backdrop_img.resize((video_width, video_height), Image.LANCZOS)
                            
                            # 2. Add text to the image
                            draw = ImageDraw.Draw(backdrop_img)
                            text_color = (255, 255, 255)  # White
                            
                            # Try to find a font - use system fonts or default
                            try:
                                # Look in common font locations
                                font_locations = [
                                    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",  # Linux
                                    "/usr/share/fonts/TTF/Arial.ttf",                        # Some Linux
                                    "/Library/Fonts/Arial.ttf",                              # macOS
                                    "C:\\Windows\\Fonts\\Arial.ttf",                         # Windows
                                    # Add fallbacks
                                    "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
                                    "/usr/share/fonts/truetype/freefont/FreeSansBold.ttf", 
                                ]
                                
                                font = None
                                for font_path in font_locations:
                                    if os.path.exists(font_path):
                                        if self.verbose: print(f"INFO: Using font: {font_path}")
                                        try:
                                            font = ImageFont.truetype(font_path, 70)
                                            break
                                        except Exception as font_e:
                                            if self.verbose: print(f"WARNING: Could not load font {font_path}: {font_e}")
                                
                                # If no font found, use default
                                if font is None:
                                    if self.verbose: print("INFO: Using default font")
                                    font = ImageFont.load_default()
                                    # Make default font bigger if possible
                                    if hasattr(font, 'size'):
                                        for size in [70, 60, 50, 40, 36]:
                                            try:
                                                font = ImageFont.truetype(font.path, size)
                                                break
                                            except:
                                                continue
                            
                            except Exception as font_e:
                                if self.verbose: print(f"WARNING: Font loading error: {font_e}. Using default.")
                                font = ImageFont.load_default()
                            
                            # Calculate text position - center of image
                            text_width, text_height = draw.textsize(birthday_message, font=font) if hasattr(draw, 'textsize') else (video_width//2, video_height//5)
                            text_position = ((video_width - text_width) // 2, (video_height - text_height) // 2)
                            
                            # Draw text with "stroke" by drawing the text in black with offsets
                            stroke_width = 2
                            shadow_color = (0, 0, 0)  # Black shadow/stroke
                            for dx, dy in [(x, y) for x in range(-stroke_width, stroke_width + 1) for y in range(-stroke_width, stroke_width + 1)]:
                                if dx != 0 or dy != 0:  # Skip the center position (that's for the main text)
                                    draw.text((text_position[0] + dx, text_position[1] + dy), birthday_message, font=font, fill=shadow_color)
                            
                            # Now draw the main text
                            draw.text(text_position, birthday_message, font=font, fill=text_color)
                            
                            # Save the composite image
                            card_slate_path = os.path.join(temp_dir, "birthday_card_slate.png")
                            backdrop_img.save(card_slate_path)
                            backdrop_img.close()
                            
                            # How long the slate should appear (5 seconds)
                            card_slate_duration = 5
                            
                            # Convert the static image to a video clip using FFmpeg
                            # This is MUCH more memory efficient than using MoviePy's ImageClip
                            slate_video_path = os.path.join(temp_dir, "birthday_card_slate.mp4")
                            
                            # Create a video from the static image
                            ffmpeg_slate_cmd = [
                                "ffmpeg", "-y",
                                "-loop", "1",
                                "-i", card_slate_path,
                                "-c:v", "libx264",
                                "-t", str(card_slate_duration),
                                "-pix_fmt", "yuv420p",
                                "-vf", f"scale={video_width}:{video_height}:force_original_aspect_ratio=decrease,pad={video_width}:{video_height}:(ow-iw)/2:(oh-ih)/2",
                                "-r", "24",
                                slate_video_path
                            ]
                            
                            if self.verbose:
                                print(f"INFO: Creating slate video with FFmpeg: {' '.join(ffmpeg_slate_cmd)}")
                                
                            try:
                                subprocess.run(ffmpeg_slate_cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                                
                                if os.path.exists(slate_video_path) and os.path.getsize(slate_video_path) > 0:
                                    # Save the final animated video first
                                    animated_video_path = os.path.join(temp_dir, "animated_part.mp4")
                                    
                                    if self.verbose:
                                        print(f"INFO: Writing animated video portion to temporary file: {animated_video_path}")
                                    
                                    # Write the animated portion with reduced quality settings to save memory
                                    final_animated_video_obj.write_videofile(
                                        animated_video_path,
                                        codec="libx264",
                                        audio_codec="aac",
                                        fps=24,
                                        bitrate="5000k",
                                        preset="ultrafast",  # Use ultrafast for temp file
                                        threads=2,
                                        ffmpeg_params=["-pix_fmt", "yuv420p"],
                                        logger=None,
                                        verbose=False
                                    )
                                    
                                    # Clear any resources no longer needed
                                    if final_animated_video_obj and hasattr(final_animated_video_obj, 'close'):
                                        final_animated_video_obj.close()
                                        final_animated_video_obj = None
                                    
                                    # Use FFmpeg to concatenate the slate and the animated video
                                    # Create a concat file
                                    concat_file_path = os.path.join(temp_dir, "concat.txt")
                                    with open(concat_file_path, "w") as f:
                                        f.write(f"file '{os.path.abspath(slate_video_path)}'\n")
                                        f.write(f"file '{os.path.abspath(animated_video_path)}'\n")
                                    
                                    if output_path is None:
                                        output_path = f"chibi_clip_with_music_{int(time.time())}.mp4"
                                    
                                    ffmpeg_concat_cmd = [
                                        "ffmpeg", "-y",
                                        "-f", "concat",
                                        "-safe", "0",
                                        "-i", concat_file_path,
                                        "-c", "copy",  # Just copy, don't re-encode
                                        output_path
                                    ]
                                    
                                    if self.verbose:
                                        print(f"INFO: Concatenating videos with FFmpeg: {' '.join(ffmpeg_concat_cmd)}")
                                        
                                    subprocess.run(ffmpeg_concat_cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                                    
                                    if os.path.exists(output_path) and os.path.getsize(output_path) > 0:
                                        if self.verbose:
                                            print(f"✅ Final video with birthday card slate saved to {output_path}")
                                        return output_path
                                    else:
                                        if self.verbose:
                                            print("WARNING: Failed to create concatenated video. Falling back to animated part only.")
                                        # Copy the animated part as the result
                                        shutil.copy(animated_video_path, output_path)
                                        return output_path
                                else:
                                    if self.verbose:
                                        print("WARNING: Failed to create slate video. Proceeding with animated video only.")
                            except subprocess.CalledProcessError as ffmpeg_e:
                                if self.verbose:
                                    print(f"WARNING: FFmpeg command failed: {ffmpeg_e}")
                                    print("Proceeding with the animated portion only.")
                            except Exception as e:
                                if self.verbose:
                                    print(f"WARNING: Error during slate video creation: {e}")
                                    print("Proceeding with the animated portion only.")
                            
                    except Exception as slate_e:
                        if self.verbose:
                            print(f"ERROR: Error creating birthday card slate: {slate_e}. Proceeding without it.")
                            import traceback
                            traceback.print_exc()
                # --- BIRTHDAY CARD SLATE LOGIC END ---
                
                # If we reach here, it means we're using the original final_animated_video_obj
                # (Either because there's no birthday message or the slate creation failed)
                if output_path is None:
                    base_filename = "chibi_clip_with_music"
                    output_path = f"{base_filename}_{int(time.time())}.mp4"
                
                if self.verbose:
                    print(f"⑨ Writing final video to {output_path}")
                
                # Even more memory optimization: Use ultrafast preset and lower bitrate
                final_video_to_write.write_videofile(
                    output_path, 
                    codec="libx264", 
                    audio_codec="aac", 
                    fps=24,
                    bitrate="4000k",  # Further reduced bitrate
                    preset="ultrafast",  # Use ultrafast (lowest memory usage)
                    threads=2,
                    ffmpeg_params=["-pix_fmt", "yuv420p"],
                    logger=None,
                    verbose=False
                )
            
            except MemoryError as mem_e:
                # Handle extreme memory pressure with ffmpeg direct manipulation if possible
                if self.verbose:
                    print(f"Critical memory error during video processing: {mem_e}")
                    print("Attempting emergency fallback to pure FFmpeg for basic concatenation...")
                
                # Here we would implement a very low-level FFmpeg-only approach
                # But for now, we'll just propagate the error
                raise
            
            except Exception as e:
                if self.verbose:
                    print(f"Error loading VideoFileClip: {e}")
                raise RuntimeError(f"Error processing video file: {e}") from e
        except Exception as e:
            error_message = f"Error adding music to video: {e}"
            if self.verbose:
                print(error_message)
                import traceback
                traceback.print_exc() # Print full traceback for debugging
            raise RuntimeError(error_message) from e
        finally:
            if self.verbose: print("⑩ Cleaning up resources in finally block...")
            # Safely close each resource in a try/except block to avoid errors
            try:
                if video_clip_obj and hasattr(video_clip_obj, 'close'): 
                    video_clip_obj.close()
                    if self.verbose: print("   Closed video_clip_obj")
            except Exception as e:
                if self.verbose: print(f"   Warning: Error closing video_clip_obj: {e}")
                
            try:
                if audio_obj and hasattr(audio_obj, 'close'): 
                    audio_obj.close()
                    if self.verbose: print("   Closed audio_obj")
            except Exception as e:
                if self.verbose: print(f"   Warning: Error closing audio_obj: {e}")
                
            try:
                if final_animated_video_obj and hasattr(final_animated_video_obj, 'close'): 
                    final_animated_video_obj.close()
                    if self.verbose: print("   Closed final_animated_video_obj")
            except Exception as e:
                if self.verbose: print(f"   Warning: Error closing final_animated_video_obj: {e}")
                
            try:
                # Ensure final_video_to_write is closed if it's a different object (i.e., if slate was added)
                if final_video_to_write and final_video_to_write is not final_animated_video_obj and hasattr(final_video_to_write, 'close'): 
                    final_video_to_write.close()
                    if self.verbose: print("   Closed final_video_to_write")
            except Exception as e:
                if self.verbose: print(f"   Warning: Error closing final_video_to_write: {e}")
                
            try:
                if card_slate and hasattr(card_slate, 'close'): 
                    card_slate.close()
                    if self.verbose: print("   Closed card_slate")
            except Exception as e:
                if self.verbose: print(f"   Warning: Error closing card_slate: {e}")
                
            try:
                if backdrop_clip and hasattr(backdrop_clip, 'close'): 
                    backdrop_clip.close()
                    if self.verbose: print("   Closed backdrop_clip")
            except Exception as e:
                if self.verbose: print(f"   Warning: Error closing backdrop_clip: {e}")
                
            try:
                if txt_clip and hasattr(txt_clip, 'close'): 
                    txt_clip.close()
                    if self.verbose: print("   Closed txt_clip")
            except Exception as e:
                if self.verbose: print(f"   Warning: Error closing txt_clip: {e}")
            
            # Clean up temp directory if it exists
            try:
                if 'temp_dir' in locals() and os.path.exists(temp_dir):
                    import shutil
                    shutil.rmtree(temp_dir, ignore_errors=True)
                    if self.verbose: print(f"   Removed temp directory: {temp_dir}")
            except Exception as e:
                if self.verbose: print(f"   Warning: Error removing temp directory: {e}")

    # Step 7: High-level orchestrator (Updated to handle local file URLs)
    def process_clip(self, photo_path: str, action: str = "running", ratio: str = "9:16", duration: int = 5, audio_path: str = None, extended_duration: int = 45, use_local_storage=False, birthday_message=None):
        if self.verbose:
            print(f"▶ Generating clip (source: {photo_path}, action: {action}, ratio: {ratio}, duration: {duration}s)…")
            if birthday_message:
                print(f"  With birthday message: {birthday_message}")

        # For birthday-dance action, force local storage and use birthday song
        if action == "birthday-dance":
            use_local_storage = True
            # Set default audio path to birthday_song.mp3 if not specified
            if audio_path is None:
                # Look for birthday_song.mp3 in the project root
                project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
                default_audio_path = os.path.join(project_root, "birthday_song.mp3")
                if os.path.exists(default_audio_path):
                    audio_path = default_audio_path
                    if self.verbose:
                        print(f"Birthday theme selected: Using default birthday song: {audio_path}")
                else:
                    if self.verbose:
                        print("Birthday song not found at expected location. Will generate video without audio.")

        try:
            # ===== ENHANCED INITIAL VALIDATION BLOCK for photo_path =====
            if self.verbose:
                print(f"ChibiClip: Initial validation for photo_path: {photo_path}")
            if not os.path.exists(photo_path):
                raise FileNotFoundError(f"ChibiClip: Input photo file does not exist at path: {photo_path}")
            if os.path.getsize(photo_path) == 0:
                raise ValueError(f"ChibiClip: Input photo file is empty: {photo_path}")

            # Fail fast if the file looks like text (XML, HTML, JSON)
            try:
                with open(photo_path, "rb") as f_text_check:
                    head = f_text_check.read(64)
                    # Strip leading whitespace (like UTF-8 BOM, etc.) before checking
                    stripped_head = head.lstrip()
                    if stripped_head.startswith((b"<", b"{")): # Common starts for XML/HTML and JSON
                        # More specific check for <?xml
                        if stripped_head.startswith(b"<?xml"):
                             error_detail = "looks like an XML document (e.g., S3 error page)"
                        elif stripped_head.startswith(b"<html") or stripped_head.startswith(b"<!DOCTYPE"):
                             error_detail = "looks like an HTML document"
                        elif stripped_head.startswith(b"{"):
                             error_detail = "looks like a JSON response"
                        else:
                             error_detail = "starts with '<' or '{', indicating a text-based file"
                        
                        raise ValueError(
                            f"ChibiClip: Input file {photo_path} is not a binary image; it {error_detail}. "
                            f"Header (first ~64 bytes): {head.hex()}..."
                        )
            except ValueError: # Re-raise if it's our specific error
                raise
            except Exception as e_text_check: # Catch other read errors
                if self.verbose:
                    print(f"ChibiClip: Could not perform initial text check on {photo_path}: {e_text_check}")


            # Log first 16 bytes for header sniffing
            file_header_bytes_hex = "unknown (read error)"
            try:
                with open(photo_path, "rb") as f_check_header:
                    file_header_bytes_hex = f_check_header.read(16).hex() # Read first 16 bytes
                if self.verbose:
                    print(f"ChibiClip: First 16 header bytes of {photo_path}: {file_header_bytes_hex}")
            except Exception as e_read_header:
                if self.verbose:
                    print(f"ChibiClip: Could not read header bytes from {photo_path}: {e_read_header}")
            
            # HEIC/HEIF check (common problematic format)
            # Magic bytes for HEIC/HEIF variants (ftypheic, ftypheix, ftyphevc, ftyphevx)
            # b'\x00\x00\x00\xNNftypheic' or similar
            if file_header_bytes_hex.startswith("000000") and "6674797068656963" in file_header_bytes_hex: # ftypheic
                 if self.verbose:
                    print(f"ChibiClip: Detected HEIC/HEIF variant based on header: {file_header_bytes_hex}. Attempting conversion to PNG.")
                 try:
                    photo_path = self._to_png(photo_path) # Convert and update photo_path
                    if self.verbose:
                        print(f"ChibiClip: Successfully converted HEIC to PNG: {photo_path}")
                    # Re-check header after conversion
                    with open(photo_path, "rb") as f_check_header_after_conv:
                        file_header_bytes_hex = f_check_header_after_conv.read(16).hex()
                    if self.verbose:
                        print(f"ChibiClip: First 16 header bytes of new PNG {photo_path}: {file_header_bytes_hex}")
                 except RuntimeError as e_heic_conv:
                    raise ValueError(f"ChibiClip: HEIC/HEIF file detected but conversion to PNG failed: {e_heic_conv}")

            # Use imghdr for a quick check
            image_type_imghdr = imghdr.what(photo_path)
            if self.verbose:
                print(f"ChibiClip: imghdr.what('{photo_path}') detected type: {image_type_imghdr}")

            if image_type_imghdr is None:
                if self.verbose:
                    print(f"ChibiClip: imghdr could not identify image type for {photo_path}. This might be an unsupported format (e.g., WebP before Pillow 10, AVIF) or not an image. Attempting conversion to PNG as a fallback.")
                try:
                    photo_path = self._to_png(photo_path) # Convert and update photo_path
                    image_type_imghdr = imghdr.what(photo_path) # Re-check
                    if self.verbose:
                        print(f"ChibiClip: Post-conversion, imghdr detected: {image_type_imghdr} for {photo_path}")
                    if image_type_imghdr is None:
                         raise ValueError(f"ChibiClip: File {photo_path} is not a recognized image even after attempting PNG conversion. Header: {file_header_bytes_hex}.")
                except RuntimeError as e_conv_fallback:
                    raise ValueError(f"ChibiClip: Fallback conversion to PNG failed for {photo_path}: {e_conv_fallback}. Original header: {file_header_bytes_hex}.")

            # Further validation using python-magic and 'file' command if available (existing logic)
            file_type_confirmed_by_tool = False
            detected_mime_type = f"image/{image_type_imghdr}" if image_type_imghdr else "unknown"

            if MAGIC_AVAILABLE:
                try:
                    mime_detector = magic.Magic(mime=True)
                    detected_mime_type = mime_detector.from_file(photo_path)
                    if self.verbose:
                        print(f"ChibiClip: python-magic detected MIME type: {detected_mime_type} for {photo_path}")
                    if detected_mime_type.startswith("image/"):
                        file_type_confirmed_by_tool = True
                except Exception as e_magic:
                    if self.verbose:
                        print(f"ChibiClip: python-magic check failed for {photo_path}: {e_magic}")
            
            if not file_type_confirmed_by_tool and SUBPROCESS_AVAILABLE:
                try:
                    subprocess.run(['which', 'file'], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=5)
                    result = subprocess.run(['file', '--mime-type', '-b', photo_path], capture_output=True, text=True, check=True, timeout=5)
                    detected_mime_type_file_cmd = result.stdout.strip()
                    if self.verbose:
                        print(f"ChibiClip: 'file' command detected MIME type: {detected_mime_type_file_cmd} for {photo_path}")
                    if detected_mime_type_file_cmd.startswith("image/"):
                        file_type_confirmed_by_tool = True
                        if detected_mime_type == "unknown":
                             detected_mime_type = detected_mime_type_file_cmd
                    elif self.verbose:
                        result_full = subprocess.run(['file', photo_path], capture_output=True, text=True, timeout=5)
                        print(f"ChibiClip: 'file' command full output: {result_full.stdout.strip()} for {photo_path}")
                except (subprocess.SubprocessError, FileNotFoundError, subprocess.TimeoutExpired) as e_file_cmd:
                    if self.verbose:
                        print(f"ChibiClip: 'file' command check failed for {photo_path}: {e_file_cmd}")
            
            pil_can_open = False
            pil_format_guess = "unknown"
            if not file_type_confirmed_by_tool:
                try:
                    with Image.open(photo_path) as img_pil_check:
                        pil_format_guess = img_pil_check.format
                        if self.verbose:
                            print(f"ChibiClip: PIL initial check successful for {photo_path}: format={pil_format_guess}")
                        if pil_format_guess: 
                            file_type_confirmed_by_tool = True 
                            if detected_mime_type == "unknown":
                                detected_mime_type = f"image/{pil_format_guess.lower()}"
                        pil_can_open = True
                except Exception as e_pil_check:
                     if self.verbose:
                        print(f"ChibiClip: PIL initial check failed for {photo_path}: {e_pil_check}")
            
            if not file_type_confirmed_by_tool:
                error_msg = (
                    f"ChibiClip: Initial validation failed: Cannot confirm '{photo_path}' is a valid image file. "
                    f"imghdr type: {image_type_imghdr}. Detected MIME (by other tools): {detected_mime_type}. "
                    f"PIL could open: {pil_can_open} (format guess: {pil_format_guess}). "
                    f"First 16 Bytes Hex: {file_header_bytes_hex}." # Updated to use the 16-byte hex
                )
                if self.verbose: print(error_msg)
                raise ValueError(error_msg)
            
            if self.verbose:
                print(f"ChibiClip: Initial validation passed for {photo_path}. Confirmed image type (imghdr: {image_type_imghdr}). Best guess MIME: {detected_mime_type}")
            # ===== END OF ENHANCED INITIAL VALIDATION BLOCK =====

            from io import BytesIO # Ensure BytesIO is imported for this scope
            
            prompt = self.generate_ai_prompt(action)
            
            if self.verbose:
                print(f"ChibiClip: Reading photo from validated path: {photo_path}")
            
            try: # This is the block that previously started around line 1170
                with open(photo_path, "rb") as f:
                    file_data = f.read()
                    
                if not file_data: 
                    raise ValueError(f"ChibiClip: No data read from file {photo_path} despite earlier size check.")
                
                image_content = BytesIO(file_data)
                
                # Verify the image file format - with enhanced error handling (existing complex block)
                try:
                    # Verify BytesIO has data
                    if image_content.getbuffer().nbytes == 0:
                        raise ValueError("ChibiClip: BytesIO object (from validated file) contains no data")
                    
                    image_content.seek(0)
                    
                    try:
                        # Verify it's a valid image stream using Pillow, but don't let Image.open close image_content
                        img_verify_pil_obj = None # Use a distinct variable name
                        try:
                            img_verify_pil_obj = Image.open(image_content) 
                            img_format = img_verify_pil_obj.format
                            img_mode = img_verify_pil_obj.mode
                            img_size = img_verify_pil_obj.size
                            if self.verbose:
                                print(f"ChibiClip: Successfully loaded image into BytesIO: format={img_format}, mode={img_mode}, size={img_size}")
                        finally:
                            # Close only the PIL Image object, not the underlying BytesIO stream
                            if img_verify_pil_obj:
                                img_verify_pil_obj.close()

                        # IMPORTANT: Reset the BytesIO stream to the beginning
                        image_content.seek(0)
                    except Exception as pil_error:
                        if self.verbose:
                            print(f"ChibiClip: PIL Error opening BytesIO from validated file: {pil_error}")
                            print(f"ChibiClip: Attempting to save and reload the image file directly (again, from validated photo_path)...")
                        
                        temp_image_path = os.path.join(self.output_dir, f"debug_image_validated_{uuid.uuid4().hex}.png")
                        try:
                            if not os.path.exists(self.output_dir):
                                os.makedirs(self.output_dir, exist_ok=True)
                            # Re-read from the validated photo_path to ensure fresh data for this debug save
                            with open(photo_path, "rb") as f_orig_for_debug:
                                original_data_for_debug = f_orig_for_debug.read()

                            if self.verbose:
                                print(f"ChibiClip: Writing {len(original_data_for_debug)} bytes from {photo_path} to debug file {temp_image_path}")
                            with open(temp_image_path, "wb") as tmp_file:
                                tmp_file.write(original_data_for_debug)
                            
                            if not os.path.exists(temp_image_path) or os.path.getsize(temp_image_path) == 0:
                                raise IOError(f"ChibiClip: Failed to create or wrote empty debug file: {temp_image_path}")
                            
                            if self.verbose:
                                print(f"ChibiClip: Wrote {os.path.getsize(temp_image_path)} bytes to {temp_image_path}")
                            
                            try:
                                img = Image.open(temp_image_path)
                                if self.verbose:
                                    print(f"ChibiClip: Successfully loaded debug image from temp file: format={img.format}, mode={img.mode}, size={img.size}")
                                # photo_path = temp_image_path # Decide if we want to proceed with this path
                                img.close()
                                # If successful, image_content might need to be recreated from this temp_image_path if it's to be used
                                # For now, let's assume if this works, the original file was the issue.
                                # Recreate image_content from the successfully opened temp_image_path
                                with open(temp_image_path, "rb") as f_temp_debug:
                                    image_content = BytesIO(f_temp_debug.read())
                                image_content.seek(0) # Reset for further processing
                                if self.verbose: print(f"ChibiClip: Recreated BytesIO from {temp_image_path} and called seek(0).")

                            except Exception as img_load_error:
                                if self.verbose:
                                    print(f"ChibiClip: Failed to open saved debug image {temp_image_path}: {img_load_error}")
                                # Try direct PIL conversion as a deeper fallback
                                try:
                                    if self.verbose: print("ChibiClip: Attempting direct PIL conversion on original validated photo_path")
                                    with open(photo_path, "rb") as f_orig_convert:
                                        original_data_convert = f_orig_convert.read()
                                    
                                    from io import BytesIO # Ensure again for this specific scope if needed
                                    input_buffer_convert = BytesIO(original_data_convert)
                                    
                                    from PIL import ImageFile # For LOAD_TRUNCATED_IMAGES
                                    ImageFile.LOAD_TRUNCATED_IMAGES = True
                                    
                                    direct_img_convert = Image.open(input_buffer_convert)
                                    if direct_img_convert.mode != "RGBA": # Prefer RGBA for consistency
                                        direct_img_convert = direct_img_convert.convert("RGBA")
                                    
                                    converted_png_path = os.path.join(self.output_dir, f"converted_final_{uuid.uuid4().hex}.png")
                                    direct_img_convert.save(converted_png_path, "PNG")
                                    direct_img_convert.close()
                                    
                                    if self.verbose: print(f"ChibiClip: Successfully converted original to PNG: {converted_png_path}")
                                    
                                    with open(converted_png_path, "rb") as f_converted:
                                        image_content = BytesIO(f_converted.read())
                                    image_content.seek(0)
                                    if self.verbose: print(f"ChibiClip: Recreated BytesIO from converted PNG {converted_png_path} and called seek(0).")
                                    # photo_path = converted_png_path # Update photo_path if we use this
                                except Exception as pil_convert_error_deep:
                                    if self.verbose: print(f"ChibiClip: Direct PIL conversion also failed: {pil_convert_error_deep}")
                                    raise ValueError(f"ChibiClip: Could not convert image from {photo_path} to a usable format after multiple attempts: {pil_error}") from pil_convert_error_deep
                        except Exception as file_error_debug_save:
                            if self.verbose: print(f"ChibiClip: Error saving debug image file: {file_error_debug_save}")
                            raise ValueError(f"ChibiClip: Could not save debug image for {photo_path}: {pil_error}") from file_error_debug_save
                    
                    image_content.seek(0) # Ensure pointer is at the start for _preprocess_image_for_openai
                    if self.verbose: print(f"ChibiClip: Called seek(0) on image_content before passing to OpenAI preprocessing.")
                except Exception as img_error_main_processing: # Catch errors from the main PIL processing block
                    if self.verbose:
                        print(f"ChibiClip: Critical image verification/processing error for {photo_path}: {img_error_main_processing}")
                    # The initial validation block should have caught most structural file issues.
                    # If we are here, it might be a more subtle PIL issue or an issue with the complex fallback logic itself.
                    raise ValueError(f"ChibiClip: Could not process image content from {photo_path}: {img_error_main_processing}")

            except Exception as e_read_validated_file: # Catch errors from reading the file or creating BytesIO
                if self.verbose:
                    print(f"ChibiClip: Error in reading validated image file {photo_path} or creating BytesIO: {e_read_validated_file}")
                    import traceback
                    traceback.print_exc()
                raise ValueError(f"ChibiClip: Error reading validated image file {photo_path}: {e_read_validated_file}")
            
            image_size = IMAGE_SIZE_MAP.get(ratio, "1024x1024") # Ensure this is after image_content is defined
            if self.verbose:
                print(f"ChibiClip: Using image size {image_size} for ratio {ratio}")

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
            
            task_id = self.generate_runway_video(img_url, action, ratio, duration)
            task_result = self.wait_for_runway_video(task_id)
            
            # Extract the video URL from the task_result correctly
            if "output" not in task_result or not task_result["output"]:
                raise RuntimeError(f"No output found in Runway task result: {task_result}")
            
            video_url = task_result["output"][0]
            
            # For birthday-dance or when audio_path is provided, add music to the video
            local_video_path = None
            if action == "birthday-dance" or (audio_path and os.path.exists(audio_path)):
                if self.verbose:
                    if action == "birthday-dance":
                        print(f"Adding birthday music from {audio_path} to video")
                    else:
                        print(f"Adding music from {audio_path} to video")
                
                # For birthday theme, use the Output directory with a descriptive name
                if action == "birthday-dance":
                    timestamp = int(time.time())
                    output_filename = f"birthday_dog_video_{timestamp}.mp4"
                    output_path = os.path.join(self.output_dir, output_filename)
                else:
                    output_path = None  # Default naming will be used
                
                # Add music and loop the video to the extended duration (default 45 seconds)
                local_video_path = self.add_music_to_video(
                    video_url, 
                    audio_path, 
                    output_path=output_path, 
                    total_duration=extended_duration,
                    birthday_message=birthday_message
                )
            else:
                # For non-birthday themes without audio, download and save the video locally 
                # if using local storage
                if use_local_storage:
                    try:
                        # Create a filename and path for the video
                        timestamp = int(time.time())
                        output_filename = f"dog_video_{timestamp}.mp4"
                        local_video_path = os.path.join(self.output_dir, output_filename)
                        
                        if self.verbose:
                            print(f"Downloading original video to: {local_video_path}")
                        
                        # Download the video
                        urllib.request.urlretrieve(video_url, local_video_path)
                        
                        if self.verbose:
                            print(f"Video saved locally to: {local_video_path}")
                    except Exception as e:
                        if self.verbose:
                            print(f"Warning: Failed to download video locally: {e}")
            
            result = {"image_url": img_url, "video_url": video_url}
            if local_image_path:
                result["local_image_path"] = local_image_path
            if local_video_path:
                result["local_video_path"] = local_video_path
                if action == "birthday-dance" or audio_path:
                    result["extended_duration"] = extended_duration
            
            if self.verbose:
                print(f"✅ Clip processing complete. Image: {img_url}, Video: {video_url}")
                if local_image_path:
                    print(f"Local image saved to: {local_image_path}")
                if local_video_path:
                    if action == "birthday-dance" or audio_path:
                        print(f"Extended video with music ({extended_duration}s) saved to: {local_video_path}")
                    else:
                        print(f"Video saved to: {local_video_path}")
            
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
                    help="Action the dog should perform in the animation. Note: 'birthday-dance' option automatically uses local storage and adds birthday music.")
    ap.add_argument("--ratio", default="9:16", choices=["9:16", "16:9", "1:1"],
                    help="Aspect ratio for the output video.")
    ap.add_argument("--duration", default=5, type=int, choices=[5, 10],
                    help="Duration of the video in seconds (5 or 10).")
    ap.add_argument("--audio", help="Path to an audio file to add to the video. Not needed for birthday-dance as it uses the default birthday song.")
    ap.add_argument("--extended-duration", type=int, default=45,
                    help="Total duration in seconds for the extended video with music (default: 45)")
    ap.add_argument("--verbose", action="store_true", help="Enable verbose logging.")
    ap.add_argument("--use-local-storage", action="store_true",
                    help="Save images locally instead of uploading to ImgBB. Auto-enabled for birthday-dance.")
    ap.add_argument("--output-dir", help="Directory to save locally stored images and videos")
    args = ap.parse_args()

    # Print a special message for birthday theme
    if args.action == "birthday-dance":
        print("🎂 Birthday theme selected! 🎂")
        print("- Will create a dancing dog with a party hat")
        print("- Will automatically use local storage")
        print("- Will add birthday music and loop to 45 seconds")
        print("- Output will be saved to the Output directory\n")

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
            if args.action == "birthday-dance" or args.audio:
                print(f"Extended video with music ({res.get('extended_duration', 45)}s) saved to: {res['local_video_path']}")
            else:
                print(f"Video saved to: {res['local_video_path']}")

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