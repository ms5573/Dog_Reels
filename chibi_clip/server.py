from flask import Flask, request, jsonify, abort, send_from_directory, render_template
import os
import uuid
import tempfile # For secure temporary file creation
import time
import json
from werkzeug.utils import secure_filename # For secure filenames

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

# Import Celery tasks
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

# Create a directory for task storage
TASKS_DIR = os.path.join(OUTPUT_DIR, "tasks")
os.makedirs(TASKS_DIR, exist_ok=True)

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
    
    with open(task_file, "w") as f:
        json.dump(data, f)
    
    return data

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
    
    # Securely save the uploaded file to a permanent path
    filename = secure_filename(file.filename)
    base, ext = os.path.splitext(filename)
    permanent_filename = f"{base}_{task_id}{ext}"
    permanent_path = os.path.join(OUTPUT_DIR, permanent_filename)
    
    try:
        file.save(permanent_path)
        app.logger.info(f"Saved uploaded file to: {permanent_path}")
        
        # Create initial task status
        save_task_status(task_id, "PENDING", "Processing upload")
        
        # Submit the task to Celery
        generate_birthday_card.delay(permanent_path, birthday_message)
        
        # Return task ID for status polling
        return jsonify({
            "task_id": task_id,
            "status": "PENDING",
            "message": "Your request is being processed",
            "status_url": f"/task/{task_id}"
        }), 202
        
    except Exception as e:
        app.logger.error(f"Error during request processing: {e}", exc_info=True)
        return jsonify({"error": f"Failed to process your request: {str(e)}"}), 500

# Route to check task status
@app.route('/task/<task_id>', methods=['GET'])
def get_task_status(task_id):
    task_file = os.path.join(TASKS_DIR, f"{task_id}.json")
    
    if not os.path.exists(task_file):
        return jsonify({"error": "Task not found"}), 404
    
    try:
        with open(task_file, "r") as f:
            task_data = json.load(f)
        
        return jsonify(task_data), 200
    except Exception as e:
        app.logger.error(f"Error retrieving task status: {e}")
        return jsonify({"error": "Failed to retrieve task status"}), 500

# Route to serve locally stored videos
@app.route('/videos/<filename>')
def serve_video(filename):
    return send_from_directory(OUTPUT_DIR, filename)

if __name__ == '__main__':
    # Make sure FLASK_ENV=development for debugger and reloader
    # Host 0.0.0.0 to make it accessible on the network
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5001)), debug=True) 