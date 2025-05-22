from flask import Flask, request, jsonify, abort, send_from_directory, render_template
import os
import uuid
import tempfile # For secure temporary file creation
import time
import json
import redis
from werkzeug.utils import secure_filename # For secure filenames
import cloudinary
import cloudinary.uploader

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

# Import Celery tasks (for reference, but we'll process in web dyno)
try:
    from .tasks import generate_birthday_card
    print("Imported Celery tasks using relative import")
except (ImportError, ModuleNotFoundError):
    try:
        from chibi_clip.tasks import generate_birthday_card
        print("Imported Celery tasks using direct import")
    except Exception as e:
        print(f"Could not import Celery tasks: {e}")
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
APP_ROOT = os.getcwd()
print(f"App root directory: {APP_ROOT}")
OUTPUT_DIR = os.path.join(APP_ROOT, "Output")
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

# Initialize Redis client
REDIS_URL = os.getenv('REDIS_URL')
redis_client = None
if REDIS_URL:
    try:
        # Set SSL verification to false for self-signed certificates
        connection_pool = redis.ConnectionPool.from_url(
            REDIS_URL,
            ssl_cert_reqs=None  # Disable certificate verification
        )
        redis_client = redis.Redis(connection_pool=connection_pool)
        # Test connection
        redis_client.ping()
        print(f"Connected to Redis at {REDIS_URL}")
    except Exception as e:
        print(f"Failed to connect to Redis: {e}")
        # Fall back to a non-SSL connection if SSL fails
        try:
            if 'CERTIFICATE_VERIFY_FAILED' in str(e):
                print("Trying alternative connection method for Redis...")
                # Import necessary SSL settings
                import ssl
                ssl_context = ssl.create_default_context()
                ssl_context.check_hostname = False
                ssl_context.verify_mode = ssl.CERT_NONE
                
                connection_pool = redis.ConnectionPool.from_url(
                    REDIS_URL,
                    ssl=True,
                    ssl_context=ssl_context
                )
                redis_client = redis.Redis(connection_pool=connection_pool)
                redis_client.ping()
                print("Connected to Redis using custom SSL context")
        except Exception as backup_error:
            print(f"All Redis connection attempts failed: {backup_error}")
            redis_client = None
else:
    print("REDIS_URL not found. Worker tasks will not be processed correctly.")

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'} # Add more if needed

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# Create a directory for task storage
TASKS_DIR = os.path.join(OUTPUT_DIR, "tasks")
os.makedirs(TASKS_DIR, exist_ok=True)
print(f"Task directory for status files: {TASKS_DIR}")

# Dictionary to store task data in memory while processing
tasks = {}

# Helper function to ensure Cloudinary is configured
def ensure_cloudinary_configured():
    if hasattr(ensure_cloudinary_configured, 'configured') and ensure_cloudinary_configured.configured:
        # app.logger.info("Cloudinary already confirmed as configured.")
        return True

    app.logger.info("Attempting EXPLICIT Cloudinary configuration with individual environment variables.")
    
    cloud_name = os.getenv('CLOUDINARY_CLOUD_NAME')
    api_key = os.getenv('CLOUDINARY_API_KEY')
    api_secret = os.getenv('CLOUDINARY_API_SECRET')

    # Log presence and basic details (avoid logging the secret itself)
    app.logger.info(f"CLOUDINARY_CLOUD_NAME found: {'Yes' if cloud_name else 'No'}")
    app.logger.info(f"CLOUDINARY_API_KEY found: {'Yes' if api_key else 'No'}")
    app.logger.info(f"CLOUDINARY_API_SECRET found: {'Yes' if api_secret else 'No'} (Length: {len(api_secret) if api_secret else 0})")

    if cloud_name and api_key and api_secret:
        try:
            cloudinary.config(
                cloud_name=cloud_name,
                api_key=api_key,
                api_secret=api_secret,
                secure=True
            )
            current_config = cloudinary.config()
            if current_config.cloud_name == cloud_name:
                app.logger.info(f"Cloudinary configured successfully using EXPLICIT variables. Cloud name: {current_config.cloud_name}")
                ensure_cloudinary_configured.configured = True
                return True
            else:
                app.logger.error("Cloudinary config() called with explicit variables, but verification of cloud_name failed. SDK might not have applied them.")
                ensure_cloudinary_configured.configured = False
                return False
        except Exception as e:
            app.logger.error(f"Error during EXPLICIT cloudinary.config() with individual variables: {e}")
            ensure_cloudinary_configured.configured = False
            return False
    else:
        app.logger.error("CRITICAL: Not all individual Cloudinary credentials (NAME, KEY, SECRET) were found. Cannot configure Cloudinary explicitly.")
        ensure_cloudinary_configured.configured = False
        return False
ensure_cloudinary_configured.configured = False # Initialize static variable

# Helper function to save task status
def save_task_status(task_id, status, stage="Queued", result_url=None, error=None):
    task_file = os.path.join(TASKS_DIR, f"{task_id}.json")
    data = {
        "id": task_id,
        "status": status,
        "stage": stage,
        "created": time.time(),
        "updated": time.time()
    }
    if result_url:
        data["result_url"] = result_url
    if error:
        data["error"] = error
    
    # Store in memory
    tasks[task_id] = data
    
    # Also write to file
    try:
        with open(task_file, "w") as f:
            json.dump(data, f)
    except Exception as e:
        app.logger.error(f"Error saving task status to file: {e}")
    
    return data

# Function to add a task to Redis queue for processing by worker
def add_task_to_queue(task_id, photo_url, birthday_message=None):
    if not redis_client:
        app.logger.error("Redis client not initialized. Cannot add task to queue.")
        save_task_status(task_id, "FAILED", "Redis not available", error="Redis connection not available")
        return False
    
    try:
        app.logger.info(f"Adding task {task_id} to Redis queue")
        
        # Update task status
        save_task_status(task_id, "QUEUED", "Added to processing queue")
        
        # Create task data for worker
        task_data = {
            "task_id": task_id,
            "photo_url": photo_url,  # Now using a URL instead of local path
            "product_title": "Dog Birthday Card",
            "product_description": birthday_message or "Happy Birthday!",
            "created_at": time.strftime("%Y-%m-%d %H:%M:%S")
        }
        
        # Add to queue
        queue_name = 'dog_video_tasks'
        redis_client.rpush(queue_name, json.dumps(task_data))
        
        app.logger.info(f"Task {task_id} successfully added to Redis queue '{queue_name}'")
        return True
        
    except Exception as e:
        app.logger.error(f"Error adding task to Redis queue: {e}", exc_info=True)
        save_task_status(task_id, "FAILED", "Queue error", error=str(e))
        return False

# Route to serve locally stored images
@app.route('/images/<filename>')
def serve_image(filename):
    return send_from_directory(OUTPUT_DIR, filename)

@app.route('/')
def index():
    return render_template('index.html')

@app.route("/generate", methods=["POST"])
def generate_route(): # Renamed from generate to avoid conflict with module
    if not all([OPENAI_KEY, RUNWAY_KEY]):
        return jsonify({"error": "Server is not configured with necessary API keys."}), 500

    if 'photo' not in request.files:
        return jsonify({"error": "No photo file part in the request"}), 400
    
    file = request.files["photo"]
    if file.filename == '' :
        return jsonify({"error": "No selected file"}), 400

    if not file or not allowed_file(file.filename):
        return jsonify({"error": "Invalid file type. Allowed: png, jpg, jpeg, gif"}), 400

    # Generate a task ID
    task_id = str(uuid.uuid4())
    
    # Get parameters
    action = request.form.get("action", "birthday-dance")
    birthday_message = request.form.get("birthdayMessage", None)
    
    # Handle birthday theme automation
    if action == "birthday-dance":
        app.logger.info("Birthday theme selected - will use local storage and birthday song")
    
    permanent_path = None # Define to ensure it's available in finally block
    try:
        # Create initial task status
        save_task_status(task_id, "PENDING", "Processing queued")
        
        # Securely save the uploaded file to a temporary path for Cloudinary upload
        filename = secure_filename(file.filename)
        base, ext = os.path.splitext(filename)
        
        with tempfile.NamedTemporaryFile(delete=False, prefix=f"{base}_{task_id}_", suffix=ext) as tmp_file:
            file.save(tmp_file.name)
            permanent_path = tmp_file.name # Use this temp path for upload
            app.logger.info(f"Saved uploaded file to temporary path for Cloudinary: {permanent_path}")

        # Attempt to configure Cloudinary before uploading
        if not ensure_cloudinary_configured():
            app.logger.error("Cloudinary is not configured. Cannot upload image.")
            # Save status reflecting this
            save_task_status(task_id, "FAILED", "Configuration error", 
                            error="Cloud storage service is not configured on the server.")
            return jsonify({
                "error": "Image storage service not configured",
                "message": "Our image processing service is currently experiencing configuration issues. Please try again later."
            }), 503
        
        # Upload to Cloudinary
        cloudinary_url = None
        try:
            app.logger.info(f"Attempting to upload {permanent_path} to Cloudinary.")
            upload_result = cloudinary.uploader.upload(
                permanent_path,
                public_id=f"dog_cards/{task_id}", # Using task_id ensures a unique public_id
                overwrite=True,
                resource_type="image" # Explicitly set resource type
            )
            cloudinary_url = upload_result.get('secure_url')
            
            if not cloudinary_url:
                app.logger.error("Cloudinary upload succeeded but no secure_url was returned.")
                raise Exception("Cloudinary upload failed: No secure_url returned.")
                
            app.logger.info(f"Uploaded image to Cloudinary: {cloudinary_url}")
                
        except Exception as cloud_error:
            app.logger.error(f"Cloudinary upload failed: {cloud_error}", exc_info=True)
            # Save error in task status
            save_task_status(task_id, "FAILED", "Cloudinary upload error", 
                            error=f"Cloud storage upload failed: {str(cloud_error)}")
            return jsonify({
                "error": "Failed to upload image to cloud storage",
                "message": "Our image processing service is experiencing issues. Please try again later."
            }), 500 # 500 for server-side cloud storage issue
        
        # Check if Redis is available first
        if not redis_client:
            app.logger.error("Redis client is not available. Cannot add task to queue.")
            save_task_status(task_id, "FAILED", "Redis connection error", 
                            error="Could not connect to the task processing system. Please try again later.")
            return jsonify({
                "error": "Task processing system unavailable",
                "message": "Our video generation service is currently experiencing issues. Please try again later.",
                "code": "REDIS_UNAVAILABLE"
            }), 503
            
        # Add task to Redis queue with Cloudinary URL
        try:
            redis_client.ping() # Test Redis connection
            success = add_task_to_queue(task_id, cloudinary_url, birthday_message)
            
            if not success:
                # add_task_to_queue already saves FAILED status, so just return
                return jsonify({
                    "error": "Failed to queue task for processing", 
                    "message": "Your request could not be added to the processing queue. Please try again."
                }), 500
            
            # Return task ID for status polling
            return jsonify({
                "task_id": task_id,
                "status": "QUEUED",
                "message": "Your request has been queued for processing. Please check status endpoint."
            })
        except redis.exceptions.ConnectionError as e:
            app.logger.error(f"Redis connection error when queueing task: {e}")
            save_task_status(task_id, "FAILED", "Redis connection failed", error=str(e))
            return jsonify({
                "error": "Connection to processing service failed",
                "message": "We encountered an issue connecting to our video processing service. Please try again later."
            }), 503
        except redis.exceptions.RedisError as e: # Catch other Redis errors
            app.logger.error(f"Redis error when queueing task: {e}")
            save_task_status(task_id, "FAILED", "Redis operation failed", error=str(e))
            return jsonify({
                "error": "Processing service error",
                "message": "An error occurred in our video processing service. Please try again later."
            }), 500
        
    except Exception as e:
        app.logger.error(f"Error in /generate endpoint: {e}", exc_info=True)
        # Ensure a task status is saved if an ID was generated
        if 'task_id' in locals() and task_id:
             save_task_status(task_id, "FAILED", "Unhandled server error", error=str(e))
        return jsonify({
            "error": str(e), # It's often better to return a generic error to the client
            "details": "An unexpected error occurred while processing your request. Please try again later."
        }), 500
    finally:
        # Clean up the temporary file from local storage after Cloudinary upload attempt
        if permanent_path and os.path.exists(permanent_path):
            try:
                os.remove(permanent_path)
                app.logger.info(f"Cleaned up temporary file: {permanent_path}")
            except Exception as e_clean:
                app.logger.error(f"Error cleaning up temp file {permanent_path}: {e_clean}")

# Route to check task status
@app.route('/task/<task_id>', methods=['GET'])
def get_task_status(task_id):
    # First check in-memory storage
    if task_id in tasks:
        status_data = tasks[task_id]
        
        # If status is still QUEUED or PROCESSING, check Redis for results
        if status_data.get('status') in ['QUEUED', 'PROCESSING', 'PENDING'] and redis_client:
            try:
                # Check for results in the results queue
                result_queue = 'dog_video_results'
                queue_length = redis_client.llen(result_queue)
                
                if queue_length:
                    for i in range(queue_length):
                        result_json = redis_client.lindex(result_queue, i)
                        if result_json:
                            result = json.loads(result_json)
                            if result.get('task_id') == task_id:
                                # Found our task result
                                if result.get('status') == 'completed' and result.get('cloudinary_video_url'):
                                    # Update the status file
                                    status_data['status'] = 'SUCCESS'
                                    status_data['stage'] = 'Video processing complete'
                                    status_data['result_url'] = result.get('cloudinary_video_url')
                                    status_data['updated'] = time.time()
                                    
                                    # Save the updated status
                                    tasks[task_id] = status_data
                                    task_file = os.path.join(TASKS_DIR, f"{task_id}.json")
                                    with open(task_file, "w") as f:
                                        json.dump(status_data, f)
                                    
                                    # Remove this result from the queue
                                    redis_client.lrem(result_queue, 1, result_json)
                                    app.logger.info(f"Updated task {task_id} with completed result from Redis")
                                    
                                elif result.get('status') == 'error':
                                    # Update with error
                                    status_data['status'] = 'FAILED'
                                    status_data['stage'] = 'Processing failed'
                                    status_data['error'] = result.get('error', 'Unknown error')
                                    status_data['updated'] = time.time()
                                    
                                    # Save the updated status
                                    tasks[task_id] = status_data
                                    task_file = os.path.join(TASKS_DIR, f"{task_id}.json")
                                    with open(task_file, "w") as f:
                                        json.dump(status_data, f)
                                    
                                    # Remove this result from the queue
                                    redis_client.lrem(result_queue, 1, result_json)
                                    app.logger.info(f"Updated task {task_id} with error result from Redis")
                                
                                break
            except Exception as e:
                app.logger.error(f"Error checking Redis for task results: {e}")
        
        return jsonify(status_data), 200
    
    # Otherwise check file storage
    task_file = os.path.join(TASKS_DIR, f"{task_id}.json")
    
    if not os.path.exists(task_file):
        return jsonify({"error": "Task not found"}), 404
    
    try:
        with open(task_file, "r") as f:
            task_data = json.load(f)
        
        # Store in memory for future lookups
        tasks[task_id] = task_data
        
        # If status is still QUEUED or PROCESSING, check Redis for results
        if task_data.get('status') in ['QUEUED', 'PROCESSING', 'PENDING'] and redis_client:
            try:
                # Check for results in the results queue
                result_queue = 'dog_video_results'
                queue_length = redis_client.llen(result_queue)
                
                if queue_length:
                    for i in range(queue_length):
                        result_json = redis_client.lindex(result_queue, i)
                        if result_json:
                            result = json.loads(result_json)
                            if result.get('task_id') == task_id:
                                # Found our task result
                                if result.get('status') == 'completed' and result.get('cloudinary_video_url'):
                                    # Update the status file
                                    task_data['status'] = 'SUCCESS'
                                    task_data['stage'] = 'Video processing complete'
                                    task_data['result_url'] = result.get('cloudinary_video_url')
                                    task_data['updated'] = time.time()
                                    
                                    # Save the updated status
                                    tasks[task_id] = task_data
                                    with open(task_file, "w") as f:
                                        json.dump(task_data, f)
                                    
                                    # Remove this result from the queue
                                    redis_client.lrem(result_queue, 1, result_json)
                                    app.logger.info(f"Updated task {task_id} with completed result from Redis")
                                    
                                elif result.get('status') == 'error':
                                    # Update with error
                                    task_data['status'] = 'FAILED'
                                    task_data['stage'] = 'Processing failed'
                                    task_data['error'] = result.get('error', 'Unknown error')
                                    task_data['updated'] = time.time()
                                    
                                    # Save the updated status
                                    tasks[task_id] = task_data
                                    with open(task_file, "w") as f:
                                        json.dump(task_data, f)
                                    
                                    # Remove this result from the queue
                                    redis_client.lrem(result_queue, 1, result_json)
                                    app.logger.info(f"Updated task {task_id} with error result from Redis")
                                
                                break
            except Exception as e:
                app.logger.error(f"Error checking Redis for task results: {e}")
        
        return jsonify(task_data), 200
    except Exception as e:
        app.logger.error(f"Error retrieving task status: {e}")
        return jsonify({"error": "Failed to retrieve task status"}), 500

# Route to serve locally stored videos
@app.route('/videos/<filename>')
def serve_video(filename):
    response = send_from_directory(OUTPUT_DIR, filename)
    
    # Set content disposition header for download when requested
    if request.args.get('download'):
        response.headers['Content-Disposition'] = f'attachment; filename="{filename}"'
    else:
        # Default to inline to display in browser
        response.headers['Content-Disposition'] = f'inline; filename="{filename}"'
        
    return response

if __name__ == '__main__':
    # Make sure FLASK_ENV=development for debugger and reloader
    # Host 0.0.0.0 to make it accessible on the network
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5001)), debug=True) 