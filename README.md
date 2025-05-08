# Chibi-Clip MVP

Turns a dog photo into a Reels-ready MP4 video using AI.

## Setup

1.  Install dependencies:
    ```bash
    pip install requests python-dotenv flask
    ```

2.  Create a `.env` file in the project root and add your API keys:
    ```env
    OPENAI_API_KEY="your_openai_api_key_here"
    IMGBB_API_KEY="your_imgbb_api_key_here"
    RUNWAY_API_KEY="your_runway_api_key_here"
    ```

## Usage

### CLI

Generate a clip with default settings (running action, 9:16 ratio, 5 seconds):
```bash
python -m chibi_clip.chibi_clip sample.jpg
```

Specify custom options:
```bash
python -m chibi_clip.chibi_clip sample.jpg --action jumping --ratio 16:9 --duration 10 --verbose
```

### Server (Optional)

Run the Flask server:
```bash
python -m chibi_clip.server
```

Then, send a POST request to `/generate`:
```bash
curl -X POST -F "photo=@/path/to/your/sample.jpg" -F "action=jumping" -F "ratio=16:9" -F "duration=10" http://127.0.0.1:5000/generate
```

The response will contain the image and video URLs. 