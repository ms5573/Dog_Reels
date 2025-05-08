# Chibi-Clip MVP

Turns a dog photo into a Reels-ready MP4 video using AI.

## Setup

1.  Install dependencies:
    ```bash
    pip install requests python-dotenv flask moviepy
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

Add music to the animation:
```bash
python -m chibi_clip.chibi_clip sample.jpg --action birthday-dance --audio path/to/music.mp3 --verbose
```

Create an extended 45-second video by looping the clip (with continuous music):
```bash
python -m chibi_clip.chibi_clip sample.jpg --action birthday-dance --audio path/to/music.mp3 --extended-duration 45 --verbose
```

### Special Actions

- `running`: Dog running in place
- `tail-wagging`: Dog wagging its tail
- `jumping`: Dog jumping in place
- `birthday-dance`: Dog wearing a party hat dancing with confetti (great with music!)

### Server (Optional)

Run the Flask server:
```bash
python -m chibi_clip.server
```

Then, send a POST request to `/generate`:
```bash
curl -X POST -F "photo=@/path/to/your/sample.jpg" -F "action=jumping" -F "ratio=16:9" -F "duration=10" http://127.0.0.1:5000/generate
```

To add music, you can either:
1. Upload a custom audio file:
```bash
curl -X POST -F "photo=@/path/to/your/sample.jpg" -F "audio=@/path/to/your/music.mp3" http://127.0.0.1:5000/generate
```

2. Use the default birthday song (must exist in server root):
```bash
curl -X POST -F "photo=@/path/to/your/sample.jpg" -F "use_default_audio=true" -F "action=birthday-dance" http://127.0.0.1:5000/generate
```

3. Create an extended video by looping the clip with continuous music:
```bash
curl -X POST -F "photo=@/path/to/your/sample.jpg" -F "use_default_audio=true" -F "action=birthday-dance" -F "extended_duration=60" http://127.0.0.1:5000/generate
```

The response will contain the image and video URLs, and if audio was added, a path to the local video file with audio.

### Testing

Run the test script to generate a clip with the birthday song:
```bash
python test_audio.py
```

This will create a 45-second video by looping a 5-second clip with continuous background music. 