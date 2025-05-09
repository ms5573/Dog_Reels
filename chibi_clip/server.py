from flask import Flask, request, jsonify, abort, send_from_directory, render_template
import os
import uuid
import tempfile # For secure temporary file creation
from werkzeug.utils import secure_filename # For secure filenames

# Note: This server has been modified to support distributed deployment with Render.com
# It uploads files to S3 and passes S3 URLs between web and worker services.

# Import Celery tasks
try:
    from .tasks import process_clip as process_clip_task
except ImportError:
    from tasks import process_clip as process_clip_task

# Import S3 storage
try:
    from .storage import S3Storage
except ImportError:
    try:
        from storage import S3Storage
    except ImportError:
        print("Warning: S3Storage not available. S3 functionality will be disabled.")
        S3Storage = None

# Assuming chibi_clip.py is in the same directory or package
try:
    # Try relative import first (when imported as a package)
    from .chibi_clip import ChibiClipGenerator
    print("Imported ChibiClipGenerator using relative import")
except (ImportError, ModuleNotFoundError) as e:
    print(f"Relative import failed: {e}")
    try:
        # Try direct import (when run as a script)
        from chibi_clip import ChibiClipGenerator
        print("Imported ChibiClipGenerator using direct import")
    except (ImportError, ModuleNotFoundError) as e:
        print(f"Direct import failed: {e}")
        try:
            # Last resort - try importing directly from the file
            print("Trying absolute import from file...")
            import sys
            sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            from chibi_clip.chibi_clip import ChibiClipGenerator
            print("Imported ChibiClipGenerator using absolute import")
        except Exception as e:
            print(f"Could not import ChibiClipGenerator: {e}")
            print("Please make sure moviepy is installed correctly:")
            print("  pip install moviepy")
            print("Current Python paths:")
            for p in sys.path:
                print(f"  {p}")
            raise

app = Flask(__name__)

# Load .env variables for the server context as well
try:
    from dotenv import load_dotenv
    # Load .env from the parent directory of chibi_clip, which is the project root
    project_root = os.path.dirname(os.path.abspath(__file__))
    dotenv_path = os.path.join(project_root, '../.env') # Adjust if server.py is moved deeper
    
    # More robust .env loading: check project root first, then current dir
    if os.path.exists(os.path.join(os.getcwd(), '.env')):
        load_dotenv(os.path.join(os.getcwd(), '.env'), override=True)
        print("Loaded .env from current working directory for server.")
    elif os.path.exists(dotenv_path):
        load_dotenv(dotenv_path, override=True)
        print(f"Loaded .env from {dotenv_path} for server.")
    else:
        # Fallback to load_dotenv searching if no specific path found
        if load_dotenv(override=True):
            print("Loaded .env from standard search path for server.")
        else:
            print("Server: No .env file found. Relying on environment variables.")
except ImportError:
    print("Server: python-dotenv not installed. Skipping .env file loading. Ensure API keys are set.")

# Initialize the generator
# It's better to initialize this once, but ensure keys are present.
# Verbose set to False for server to keep logs cleaner, can be configured.
OPENAI_KEY = os.getenv("OPENAI_API_KEY")
IMGBB_KEY = os.getenv("IMGBB_API_KEY")
RUNWAY_KEY = os.getenv("RUNWAY_API_KEY")

# Set up output directory for local storage
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUTPUT_DIR = os.path.join(project_root, "Output")
os.makedirs(OUTPUT_DIR, exist_ok=True)
print(f"Output directory for local storage: {OUTPUT_DIR}")

if not all([OPENAI_KEY, RUNWAY_KEY]):
    print("CRITICAL: OpenAI and/or Runway API keys are missing in the environment. The /generate endpoint will fail.")
    # You might choose to exit here or let it fail at runtime if keys are truly not found.

if not IMGBB_KEY:
    print("Warning: ImgBB API key is missing. Will use local storage as fallback.")

# Initialize ChibiClipGenerator, verbose=False for server typically
# Allow verbose to be controlled by an environment variable for the server too
SERVER_VERBOSE = os.getenv('CHIBICLIP_SERVER_VERBOSE', 'true').lower() == 'true'
gen = ChibiClipGenerator(
    openai_api_key=OPENAI_KEY,
    imgbb_api_key=IMGBB_KEY,
    runway_api_key=RUNWAY_KEY,
    verbose=SERVER_VERBOSE,
    output_dir=OUTPUT_DIR 
)

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'} # Add more if needed

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# Route to serve locally stored images
@app.route('/images/<filename>')
def serve_image(filename):
    return send_from_directory(OUTPUT_DIR, filename)

@app.route('/')
def index():
    return render_template('index.html')

# Determine if we should use S3 storage
use_s3 = os.getenv('USE_S3_STORAGE', 'false').lower() == 'true'

# Initialize S3 storage if enabled
s3_storage = None
if use_s3 and S3Storage:
    try:
        s3_storage = S3Storage()
        print("S3 storage initialized successfully")
    except Exception as e:
        print(f"Error initializing S3 storage: {e}")
        use_s3 = False
else:
    print("S3 storage is disabled")

@app.route("/generate", methods=["POST"])
def generate_route(): # Renamed from generate to avoid conflict with module
    if not all([OPENAI_KEY, RUNWAY_KEY]):
        return jsonify({"error": "Server is not configured with necessary API keys."}), 500

    if 'imageFile' not in request.files and 'photo' not in request.files:
        return jsonify({"error": "No photo file part in the request"}), 400
    
    # Support both 'imageFile' (for new frontend) and 'photo' (for legacy)
    file = request.files.get("imageFile") or request.files.get("photo")
    if file.filename == '' :
        return jsonify({"error": "No selected file"}), 400

    if not file or not allowed_file(file.filename):
        return jsonify({"error": "Invalid file type. Allowed: png, jpg, jpeg, gif"}), 400

    action = request.form.get("action", "birthday-dance")
    ratio = request.form.get("ratio", "9:16")
    birthday_message = request.form.get("birthdayMessage", None) # Get the birthday message
    try:
        duration = int(request.form.get("duration", 5))
    except ValueError:
        return jsonify({"error": "Duration must be an integer"}), 400
    
    # Get extended duration parameter
    try:
        extended_duration = int(request.form.get("extended_duration", 45))
    except ValueError:
        return jsonify({"error": "Extended duration must be an integer"}), 400
    
    # New parameter to use local storage instead of ImgBB
    use_local_storage = request.form.get("use_local_storage", "false").lower() == "true"
    
    # Handle birthday theme automation
    # If action is birthday-dance, force local storage and use default birthday song
    if action == "birthday-dance":
        use_local_storage = True
        app.logger.info("Birthday theme selected - will use local storage and birthday song")
    
    # Handle audio parameter
    use_default_audio = request.form.get("use_default_audio", "false").lower() == "true"
    audio_path = None
    
    # For birthday theme or when default audio is requested, use birthday_song.mp3
    if action == "birthday-dance" or use_default_audio:
        # Path to the default birthday_song.mp3 in project root
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        audio_path = os.path.join(project_root, "birthday_song.mp3")
        if not os.path.exists(audio_path):
            return jsonify({"error": "Default audio file not found on server"}), 500
    
    # Check if audio file was uploaded
    custom_audio = None
    if 'audio' in request.files:
        custom_audio = request.files['audio']
        if custom_audio.filename != '':
            # Process the uploaded audio file
            if custom_audio.filename.lower().endswith(('.mp3', '.wav', '.ogg')):
                # We'll handle saving this audio file later
                pass
            else:
                return jsonify({"error": "Invalid audio file type. Allowed: mp3, wav, ogg"}), 400
    
    # Create a unique job ID
    job_id = str(uuid.uuid4())
    
    # Create temporary directory for processing files
    temp_dir = os.path.join(OUTPUT_DIR, f"temp_{job_id}")
    os.makedirs(temp_dir, exist_ok=True)
    
    # Securely save the uploaded file to the temp directory
    filename = secure_filename(file.filename) # Sanitize filename
    file_ext = os.path.splitext(filename)[1]
    saved_filename = f"{job_id}{file_ext}"
    saved_path = os.path.join(temp_dir, saved_filename)
    file.save(saved_path)
    
    # Save audio file if provided
    saved_audio_path = None
    if custom_audio and custom_audio.filename != '':
        audio_filename = secure_filename(custom_audio.filename)
        audio_ext = os.path.splitext(audio_filename)[1]
        saved_audio_filename = f"{job_id}_audio{audio_ext}"
        saved_audio_path = os.path.join(temp_dir, saved_audio_filename)
        custom_audio.save(saved_audio_path)
        audio_path = saved_audio_path
    
    # If S3 storage is enabled, upload the input files
    s3_photo_url = None
    s3_audio_url = None
    
    if use_s3 and s3_storage:
        try:
            # Upload the input photo to S3
            s3_photo_url, s3_photo_key = s3_storage.upload_file(
                saved_path, 
                key_prefix="inputs"
            )
            
            app.logger.info(f"Uploaded input photo to S3: {s3_photo_url}")
            
            # Upload the audio file if available
            if saved_audio_path:
                s3_audio_url, s3_audio_key = s3_storage.upload_file(
                    saved_audio_path, 
                    key_prefix="inputs"
                )
                app.logger.info(f"Uploaded input audio to S3: {s3_audio_url}")
            elif audio_path:  # If using default birthday song
                # We need to upload the default audio file to S3 as well
                s3_audio_url, s3_audio_key = s3_storage.upload_file(
                    audio_path,
                    key_prefix="inputs"
                )
                app.logger.info(f"Uploaded default audio to S3: {s3_audio_url}")
        except Exception as e:
            app.logger.error(f"Error uploading to S3: {e}")
            return jsonify({"error": f"S3 upload failed: {str(e)}"}), 500
    else:
        app.logger.error("S3 storage is required for distributed processing")
        return jsonify({"error": "S3 storage must be enabled for this application"}), 500
        
    if SERVER_VERBOSE:
        print(f"File saved to: {saved_path}")
        print(f"S3 photo URL: {s3_photo_url}")
        if audio_path:
            print(f"Audio file path: {audio_path}")
            if s3_audio_url:
                print(f"S3 audio URL: {s3_audio_url}")
        print(f"Using local storage: {use_local_storage}")
        print(f"Using S3 storage: {use_s3}")
        if action == "birthday-dance":
            print("Birthday theme selected - will use local storage and add birthday music")

    try:
        # Process the request asynchronously with Celery
        app.logger.info(f"Starting async task: action={action}, ratio={ratio}, duration={duration}, extended_duration={extended_duration}")
        
        # Add detailed logging
        print(f"DEBUG: Task parameters - photo_url={s3_photo_url}, audio_url={s3_audio_url}")
        print(f"DEBUG: About to submit task to Celery with Redis URL: {os.environ.get('REDIS_URL')}")
        
        # Launch the task
        task = process_clip_task.delay(
            photo_url=s3_photo_url,  # Pass S3 URL instead of local path
            audio_url=s3_audio_url,  # Pass S3 URL instead of local path
            action=action, 
            ratio=ratio, 
            duration=duration,
            extended_duration=extended_duration,
            use_local_storage=use_local_storage,
            birthday_message=birthday_message
        )
        
        # Log task ID
        print(f"DEBUG: Task submitted successfully with ID: {task.id}")
        app.logger.info(f"Task submitted with ID: {task.id}")
        
        # Return the task ID so the client can poll for results
        return jsonify({
            "status": "processing",
            "job_id": job_id,
            "task_id": task.id,
            "message": "Your video is being processed. Check status at /status/{task_id}"
        }), 202
        
    except Exception as e:
        app.logger.error(f"Error initiating job: {e}", exc_info=True)
        return jsonify({"error": "An unexpected server error occurred."}), 500

# Add a route to check the status of a task
@app.route("/status/<task_id>", methods=["GET"])
def check_status(task_id):
    """Check the status of a processing task."""
    try:
        task = process_clip_task.AsyncResult(task_id)
        
        if task.state == 'PENDING':
            response = {
                'status': 'pending',
                'message': 'Task is waiting to be processed'
            }
        elif task.state == 'FAILURE':
            response = {
                'status': 'failed',
                'message': str(task.info)
            }
        elif task.state == 'SUCCESS':
            response = {
                'status': 'completed',
                'result': task.result
            }
            
            # Add server URLs for local files
            if "local_image_path" in task.result and task.result.get("image_url", "").startswith("file://"):
                # Extract filename from the path
                filename = os.path.basename(task.result["local_image_path"])
                # Replace file:// URL with our server endpoint
                server_url = request.url_root.rstrip('/') + f"/images/{filename}"
                response['result']["image_url"] = server_url
            
            # Add local video endpoint if available
            if "local_video_path" in task.result:
                filename = os.path.basename(task.result["local_video_path"])
                # Only replace if it starts with file:// (unlikely but possible)
                if task.result.get("video_url", "").startswith("file://"):
                    server_url = request.url_root.rstrip('/') + f"/videos/{filename}"
                    response['result']["video_url"] = server_url
                # Add a local video URL
                server_url = request.url_root.rstrip('/') + f"/videos/{filename}"
                response['result']["local_video_url"] = server_url
        else:
            response = {
                'status': 'processing',
                'message': 'Task is being processed'
            }
        return jsonify(response)
    except Exception as e:
        app.logger.error(f"Error checking task status: {e}", exc_info=True)
        return jsonify({"error": "An error occurred checking task status"}), 500

# Route to serve locally stored videos
@app.route('/videos/<filename>')
def serve_video(filename):
    return send_from_directory(OUTPUT_DIR, filename)

# Add health check endpoint
@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint for monitoring and container orchestration."""
    return jsonify({
        "status": "healthy",
        "service": "dog-reels",
        "version": "1.0.0"
    }), 200

if __name__ == '__main__':
    # Make sure FLASK_ENV=development for debugger and reloader
    # Host 0.0.0.0 to make it accessible on the network
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5001)), debug=True) 