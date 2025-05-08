# Output Directory

This directory is used to store locally generated image and video files from the Chibi-Clip generator.

## Contents

This directory may contain:

1. `.png` files - Generated dog illustrations processed by OpenAI
2. `.mp4` files - Generated animated videos from Runway ML (possibly with added music)

## Usage

Files in this directory are automatically created when:

1. The `--use-local-storage` flag is used with the CLI
2. The `use_local_storage=true` parameter is passed to the server API
3. The ImgBB service is unavailable and local storage is used as a fallback

## How Local Storage Works with External APIs

When using local storage, the images need to be accessible to Runway ML for video generation. Chibi-Clip uses a reliable approach to make this work:

### Primary Method: ImgBB Upload

If ImgBB is available and an API key is provided:
1. Images are stored locally for archiving and reference
2. For Runway ML video generation, the images are temporarily uploaded to ImgBB
3. The ImgBB HTTPS URL is then provided to Runway ML

### Fallback Method: Data URI Embedding

If ImgBB is unavailable or no API key is provided:
1. The local image is read and encoded as base64
2. A data URI is created (e.g., `data:image/png;base64,iVBORw0KGgoAAAANSUhEUg...`)
3. This data URI is sent directly to Runway ML, with the image data embedded in the request

The data URI approach is 100% reliable as it doesn't depend on any external services or networking configuration, though it does increase the size of API requests.

## File Naming

- Images: UUID-based filenames with `.png` extension (e.g., `0de897ca5850.png`)
- Videos: UUID-based or timestamp-based filenames with `.mp4` extension

## Accessing Files

When using the server, these files can be accessed via the `/images/<filename>` endpoint.

When using the CLI, the paths to these files will be included in the output JSON result.

## Maintenance

This directory may grow large over time if many images and videos are generated. Consider cleaning it periodically to free up disk space. 