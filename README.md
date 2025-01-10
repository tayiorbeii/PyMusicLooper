# PyMusicLooper Video Generator

This project combines PyMusicLooper with video generation capabilities to create looping music videos. It consists of several scripts that work together to:
1. Download YouTube videos and extract their audio
2. Find the best loop points in the audio
3. Generate glitch art visuals
4. Combine the looped audio with the visuals into a final video

## Prerequisites

- Python 3.8 or higher
- ffmpeg
- sox
- yt-dlp
- Required Python packages (install via pip):
  - pymusiclooper
  - moviepy
  - pillow
  - numpy
  - matplotlib
  - randimage
  - glitch_this
  - imageio

## Usage

### 1. Prepare YouTube URLs

Create a JSON file (e.g., `videos.json`) containing an array of YouTube URLs you want to process:

```json
[
    "https://www.youtube.com/watch?v=example1",
    "https://www.youtube.com/watch?v=example2"
]
```

### 2. Download and Process Audio

Use `youtube-loop-digger.py` to download videos and find loop points:

```bash
python youtube-loop-digger.py videos.json MIN_LENGTH MAX_LENGTH NUM_LOOPS [--target_dir TARGET_DIR]
```

Parameters:
- `MIN_LENGTH`: Minimum length of loops in seconds
- `MAX_LENGTH`: Maximum length of loops in seconds
- `NUM_LOOPS`: Number of loops to extract per video
- `--target_dir`: Optional output directory (default: current directory)

This will:
1. Download each video's audio as MP3
2. Create a directory for each video
3. Find the best loop points
4. Export the looped audio files

### 3. Generate Glitch Art

Run `glitcher.py` to generate random glitch art GIFs:

```bash
python glitcher.py
```

This will:
1. Generate random images
2. Apply glitch effects
3. Save the results as GIFs in the `glitch-gifs` directory

### 4. Create Final Video

Use `makemovie.py` to combine the glitch art with the looped audio:

```bash
python makemovie.py
```

Edit the script to set your input/output paths:
- `input_video`: Path to the generated glitch GIF
- `input_audio`: Path to the looped audio file
- `output_file`: Where to save the final MP4

The script will:
1. Convert the GIF to MP4
2. Loop the video to match audio duration
3. Combine video and audio
4. Export the final video

## Directory Structure

```
.
├── videos.json              # YouTube URLs
├── youtube-loop-digger.py  # Download and process audio
├── glitcher.py            # Generate glitch art
├── makemovie.py          # Create final videos
├── glitch-gifs/          # Generated glitch art
└── output/               # Downloaded and processed audio
    └── [Video Title]/    # One directory per video
        ├── audio.mp3     # Original audio
        └── loop_*.mp3    # Extracted loops
```

## Notes

- The glitch art generator creates random visuals each time it runs
- You can adjust glitch parameters in `glitcher.py`
- Video resolution is set to 1920x1080 by default
- The final video will loop the glitch art to match the audio duration
