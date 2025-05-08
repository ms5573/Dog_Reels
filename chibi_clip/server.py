from flask import Flask, request, jsonify, abort
import os
import uuid
import tempfile # For secure temporary file creation
from werkzeug.utils import secure_filename # For secure filenames

# Assuming chibi_clip.py is in the same directory or package
try:
    from .chibi_clip import ChibiClipGenerator
except ImportError:
    # Fallback for running server.py directly for testing, assuming chibi_clip.py is in PYTHONPATH
    from chibi_clip import ChibiClipGenerator

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

if not all([OPENAI_KEY, IMGBB_KEY, RUNWAY_KEY]):
    print("CRITICAL: One or more API keys are missing in the environment. The /generate endpoint will fail.")
    # You might choose to exit here or let it fail at runtime if keys are truly not found.

# Initialize ChibiClipGenerator, verbose=False for server typically
# Allow verbose to be controlled by an environment variable for the server too
SERVER_VERBOSE = os.getenv('CHIBICLIP_SERVER_VERBOSE', 'false').lower() == 'true'
gen = ChibiClipGenerator(
    openai_api_key=OPENAI_KEY,
    imgbb_api_key=IMGBB_KEY,
    runway_api_key=RUNWAY_KEY,
    verbose=SERVER_VERBOSE, 
)

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'} # Add more if needed

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route("/generate", methods=["POST"])
def generate_route(): # Renamed from generate to avoid conflict with module
    if not all([OPENAI_KEY, IMGBB_KEY, RUNWAY_KEY]):
        return jsonify({"error": "Server is not configured with necessary API keys."}), 500

    if 'photo' not in request.files:
        return jsonify({"error": "No photo file part in the request"}), 400
    
    file = request.files["photo"]
    if file.filename == '' :
        return jsonify({"error": "No selected file"}), 400

    if not file or not allowed_file(file.filename):
        return jsonify({"error": "Invalid file type. Allowed: png, jpg, jpeg, gif"}), 400

    action = request.form.get("action", "running")
    ratio = request.form.get("ratio", "9:16")
    try:
        duration = int(request.form.get("duration", 5))
    except ValueError:
        return jsonify({"error": "Duration must be an integer"}), 400
    
    # Securely save the uploaded file to a temporary path
    # Using tempfile module for better security and automatic cleanup
    filename = secure_filename(file.filename) # Sanitize filename
    # Create a temporary directory that will be cleaned up
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = os.path.join(tmp_dir, filename)
        file.save(tmp_path)
        if SERVER_VERBOSE:
            print(f"Temporary file saved to: {tmp_path}")

        try:
            # Process the request
            app.logger.info(f"Processing request: action={action}, ratio={ratio}, duration={duration}, temp_file={tmp_path}")
            
            result = gen.process_clip(
                photo_path=tmp_path, 
                action=action, 
                ratio=ratio, 
                duration=duration
            )
            app.logger.info(f"Processing successful: {result}")
            
            return jsonify(result), 200
        except FileNotFoundError:
            app.logger.error(f"File not found during processing: {tmp_path}")
            return jsonify({"error": "File disappeared during processing. Please try again."}), 500
        except (ValueError, RuntimeError, TimeoutError) as e:
            app.logger.error(f"Error during clip generation: {e}")
            return jsonify({"error": str(e)}), 500
        except Exception as e:
            app.logger.error(f"Unexpected server error: {e}", exc_info=True)
            return jsonify({"error": "An unexpected server error occurred."}), 500

if __name__ == '__main__':
    # Make sure FLASK_ENV=development for debugger and reloader
    # Host 0.0.0.0 to make it accessible on the network
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=True) 