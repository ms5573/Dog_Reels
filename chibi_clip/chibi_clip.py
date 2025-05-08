import os
import requests
import json
import time
import base64
from io import BytesIO
# argparse and random will be imported in their respective scopes

# Step 6: Runway helpers (constants)
RATIO_MAP = {
    "9:16": "720:1280",
    "16:9": "1280:720",
    "1:1":  "960:960"  # fallback square
}
DUR_ALLOWED = (5, 10)

class ChibiClipGenerator:
    # Step 2: Rename & slim the class constructor
    def __init__(self, openai_api_key, imgbb_api_key, runway_api_key, *, verbose=True):
        self.verbose = verbose
        self.openai_api_key = openai_api_key
        self.imgbb_api_key  = imgbb_api_key
        self.runway_api_key = runway_api_key

        missing = [k for k,v in {"OpenAI":openai_api_key,
                                 "ImgBB":imgbb_api_key,
                                 "Runway":runway_api_key}.items() if not v]
        if missing:
            raise ValueError(f"Missing API key(s): {', '.join(missing)}")
        if self.verbose:
            print("ChibiClipGenerator initialized.")

    # Step 3: Prompt generator
    def generate_ai_prompt(self, action="running"):
        base = ("Charming vector illustration of a chibi‑style dog with flat pastel colors, "
                "bold black outlines, subtle cel‑shading and soft shadows, centered on a clean "
                "light‑beige background with a faint oval ground shadow, minimalistic and playful.")
        prompt = f"{base} The dog is {action} in place."
        if self.verbose:
            print(f"Generated AI prompt for OpenAI: '{prompt}'")
        return prompt

    # Step 4: OpenAI image-editing wrapper (unchanged from your original script)
    def edit_image_with_openai(self, image_content: BytesIO, prompt: str) -> str:
        if self.verbose:
            print(f"Editing image with OpenAI using prompt: \"{prompt}\"")
        headers = {
            "Authorization": f"Bearer {self.openai_api_key}"
        }
        image_bytes = image_content.getvalue()
        files = {
            'image': ('image.png', image_bytes, 'image/png'),
            'prompt': (None, prompt),
            'model': (None, 'gpt-image-1') # Using the model from the original script
        }

        try:
            response = requests.post("https://api.openai.com/v1/images/edits", headers=headers, files=files, timeout=60)
            response.raise_for_status()
            b64_json = response.json()["data"][0]["b64_json"]
            if self.verbose:
                print("Image successfully edited with OpenAI.")
            return b64_json
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
            raise RuntimeError(error_message) from e

    # Step 5: ImgBB upload (unchanged from your original script)
    def upload_to_imgbb(self, image_base64: str) -> str:
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
            raise RuntimeError(error_message) from e

    # Step 6a: Runway Kick-off call
    def generate_runway_video(self, img_url: str, action: str, ratio: str, duration: int) -> str:
        if ratio not in RATIO_MAP:
            raise ValueError(f"Invalid ratio '{ratio}'. Must be one of {list(RATIO_MAP.keys())}")
        if duration not in DUR_ALLOWED:
            raise ValueError(f"Invalid duration {duration}. Must be one of {DUR_ALLOWED}")

        if self.verbose:
            print(f"Starting Runway video generation for image: {img_url} (action: {action}, ratio: {ratio}, duration: {duration}s)")

        headers = {
            "Authorization": f"Bearer {self.runway_api_key}",
            "X-Runway-Version": "2024-11-06", # As specified
            "Content-Type": "application/json",
        }
        payload = {
            "promptImage": img_url,
            "model":       "gen4_turbo", # As specified
            "promptText": (f"Seamless looped 2D animation of a chibi‑style puppy {action} in place — "
                           "flat pastel colours, bold black outlines, smooth limb and ear motion, "
                           "subtle cel‑shading, clean light‑beige background, no cuts."),
            "duration":    duration,
            "ratio":       RATIO_MAP[ratio],
        }
        if self.verbose:
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

    # Step 7: High-level orchestrator (Simplified: no watermark, no local out_path)
    def process_clip(self, photo_path: str, action: str = "running", ratio: str = "9:16", duration: int = 5):
        if self.verbose:
            print(f"▶ Generating clip (source: {photo_path}, action: {action}, ratio: {ratio}, duration: {duration}s)…")

        try:
            prompt = self.generate_ai_prompt(action)
            
            if self.verbose:
                print(f"Reading photo from: {photo_path}")
            with open(photo_path, "rb") as f:
                image_content = BytesIO(f.read())

            edited_b64 = self.edit_image_with_openai(image_content, prompt)
            img_url    = self.upload_to_imgbb(edited_b64)
            task_id    = self.generate_runway_video(img_url, action, ratio, duration)
            task_result = self.wait_for_runway_video(task_id)
            
            # Extract the video URL from the task_result correctly
            # Based on original working code, it's task_result["output"][0]
            if "output" not in task_result or not task_result["output"]:
                raise RuntimeError(f"No output found in Runway task result: {task_result}")
            
            video_url = task_result["output"][0]
            
            if self.verbose:
                print(f"✅ Clip processing complete. Image: {img_url}, Video: {video_url}")
            
            return {"image_url": img_url, "video_url": video_url}

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

# Step 9: CLI entry point (Simplified: no --watermark, no --out)
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
    ap.add_argument("--action", default="running", choices=["running", "tail-wagging", "jumping"], 
                    help="Action the dog should perform in the animation.")
    ap.add_argument("--ratio", default="9:16", choices=["9:16", "16:9", "1:1"],
                    help="Aspect ratio for the output video.")
    ap.add_argument("--duration", default=5, type=int, choices=[5, 10],
                    help="Duration of the video in seconds (5 or 10).")
    ap.add_argument("--verbose", action="store_true", help="Enable verbose logging.")
    args = ap.parse_args()

    try:
        gen = ChibiClipGenerator(
            openai_api_key=os.getenv("OPENAI_API_KEY"),
            imgbb_api_key=os.getenv("IMGBB_API_KEY"),
            runway_api_key=os.getenv("RUNWAY_API_KEY"),
            verbose=args.verbose 
        )
        
        res = gen.process_clip(
            photo_path=args.photo, 
            action=args.action, 
            ratio=args.ratio, 
            duration=args.duration
        )
        
        print("\n✨ Clip Generation Result ✨") 
        print(json.dumps(res, indent=2, ensure_ascii=False))

        if res.get("video_url"):
             print(f"\nVideo is available at: {res['video_url']}")
        if res.get("image_url"):
            print(f"Edited image is available at: {res['image_url']}")

    except ValueError as e: 
        print(f"Error: {e}")
        if "Missing API key(s)" in str(e):
            print("Please ensure OPENAI_API_KEY, IMGBB_API_KEY, and RUNWAY_API_KEY are set in your .env file or environment.")
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