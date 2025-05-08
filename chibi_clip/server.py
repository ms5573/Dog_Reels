from flask import Flask, request, jsonify, abort, send_from_directory
import os
import uuid
import tempfile # For secure temporary file creation
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

    action = request.form.get("action", "running")
    ratio = request.form.get("ratio", "9:16")
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
    
    # Handle audio parameter
    use_default_audio = request.form.get("use_default_audio", "false").lower() == "true"
    audio_path = None
    
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
    
    # If default audio is requested, use birthday_song.mp3
    if use_default_audio:
        # Path to the default birthday_song.mp3 in project root
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        audio_path = os.path.join(project_root, "birthday_song.mp3")
        if not os.path.exists(audio_path):
            return jsonify({"error": "Default audio file not found on server"}), 500
    
    # Securely save the uploaded file to a temporary path
    # Using tempfile module for better security and automatic cleanup
    filename = secure_filename(file.filename) # Sanitize filename
    # Create a temporary directory that will be cleaned up
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = os.path.join(tmp_dir, filename)
        file.save(tmp_path)
        
        # If a custom audio file was uploaded, save it temporarily
        if custom_audio and custom_audio.filename != '':
            audio_filename = secure_filename(custom_audio.filename)
            audio_path = os.path.join(tmp_dir, audio_filename)
            custom_audio.save(audio_path)
        
        if SERVER_VERBOSE:
            print(f"Temporary file saved to: {tmp_path}")
            if audio_path:
                print(f"Audio file path: {audio_path}")
            print(f"Using local storage: {use_local_storage}")

        try:
            # Process the request
            app.logger.info(f"Processing request: action={action}, ratio={ratio}, duration={duration}, extended_duration={extended_duration}, temp_file={tmp_path}, audio_path={audio_path}, use_local_storage={use_local_storage}")
            
            result = gen.process_clip(
                photo_path=tmp_path, 
                action=action, 
                ratio=ratio, 
                duration=duration,
                audio_path=audio_path,
                extended_duration=extended_duration,
                use_local_storage=use_local_storage
            )
            app.logger.info(f"Processing successful: {result}")
            
            # If using local storage, modify the URL to use our server endpoint
            if "local_image_path" in result and result.get("image_url", "").startswith("file://"):
                # Extract filename from the path
                filename = os.path.basename(result["local_image_path"])
                # Replace file:// URL with our server endpoint
                server_url = request.url_root.rstrip('/') + f"/images/{filename}"
                result["image_url"] = server_url
                
                app.logger.info(f"Replaced local file URL with server URL: {server_url}")
            
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
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5001)), debug=True) 