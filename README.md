# PyMusicLooper

A comprehensive tool for creating seamless music loops with video generation capabilities.

## Features

- Find optimal loop points in audio files
- Generate glitch art and visual effects
- Create music videos with synchronized audio loops
- Download and process YouTube videos
- Export loops in various formats

## Project Structure

```
pymusiclooper/           # Main package
├── core/               # Core audio analysis
│   ├── core.py         # Main MusicLooper class
│   ├── analysis.py     # Loop detection algorithms
│   ├── audio.py        # Audio processing utilities
│   └── looper.py       # Legacy looper functionality
├── video/              # Video processing
│   ├── youtube-loop-digger.py  # YouTube processing
│   ├── makemovie.py           # Video creation
│   └── process.py             # Video processing utilities
├── effects/            # Visual effects
│   ├── glitcher.py     # Glitch art generation
│   └── center-image-blur-bg.py # Image processing
├── downloader/         # Media downloading
│   └── youtube.py      # YouTube download utilities
├── utils/              # Shared utilities
│   ├── handler.py      # CLI handling
│   ├── playback.py     # Audio playback
│   ├── media.py        # Media utilities
│   ├── extended_looper.py # Extended looper script
│   └── randomize_finished_videos.py # Video organization
└── config/            # Configuration files
    ├── videos.json    # YouTube video URLs
    ├── groove.json    # Groove music configs
    ├── jazz.json      # Jazz music configs
    └── cosmic.json    # Cosmic music configs

extended_looper.py      # Standalone extended looper script

- [Python (64-bit)](https://www.python.org/downloads/) >=3.10
- [ffmpeg](https://ffmpeg.org/download.html): required for loading audio from youtube (or any stream supported by [yt-dlp](https://github.com/yt-dlp/yt-dlp)) and adds support for loading additional audio formats and codecs such as M4A/AAC, Apple Lossless (ALAC), WMA, ATRAC (.at9), etc. A full list can be found at [ffmpeg's documentation](https://www.ffmpeg.org/general.html#Audio-Codecs). If the aforementioned features are not required, can be skipped.

output/               # Generated content
├── LooperOutput/     # Generated loops
├── glitch-gifs/      # Generated glitch art
├── finished/         # Final videos
└── downloads/        # Downloaded content
```

Additionally, to use the `play` command on Linux systems, you may need to
install the PortAudio library. On Ubuntu, run `sudo apt install libportaudio2`.

## Installation

### Option 1: Installing using uv [Recommended]

This method of installation is strongly recommended, as it isolates PyMusicLooper's dependencies from the rest of your environment,
and as a result, avoids dependency conflicts and breakage due to other packages.

Required tool: [`uv`](https://github.com/astral-sh/uv).

Note: python is not required, as `uv` automatically installs this package's required python version automatically if not present.

```sh
# Normal install
# (follows the official releases on https://pypi.org/project/pymusiclooper/)
uv tool install pymusiclooper

# Alternative install
# (follows the git repository; equivalent to a nightly release channel)
uv tool install git+https://github.com/arkrow/PyMusicLooper.git

# Updating to new releases in either case can be done simply using:
uv tool upgrade pymusiclooper
```

Installation note: you may need to specify a Python version if the latest Python release is not supported and fails to install, e.g.

```sh
uv tool install pymusiclooper --python "3.12"
```

### Option 2: Installing using pipx

Like `uv`, isolates PyMusicLooper's dependencies from the rest of your environment,
and as a result, avoids dependency conflicts and breakage due to other packages.
However, unlike `uv`, requires python to already be installed along with `pipx`.

Required python packages: [`pipx`](https://pypa.github.io/pipx/) (can be installed using `pip install pipx` ).

```sh
# Normal install
# (follows the official releases on https://pypi.org/project/pymusiclooper/)
pipx install pymusiclooper

# Alternative install
# (follows the git repository; equivalent to a nightly release channel)
pipx install git+https://github.com/arkrow/PyMusicLooper.git

# Updating to new releases in either case can be done simply using:
pipx upgrade pymusiclooper
```

### Option 3: Installing using pip

Traditional package installation method.

*Note: fragile compared to an installation using `uv` or `pipx`. PyMusicLooper may suddenly stop working if its dependencies were overwritten by another package (e.g. [issue #12](https://github.com/arkrow/PyMusicLooper/issues/12)).*

```sh
pip install pymusiclooper
```

## Available Commands

PyMusicLooper provides a command-line interface for easy use:

```bash
# Basic loop finding and export
pymusiclooper /path/to/audio.mp3 --output-dir ./output

# Interactive mode to choose from discovered loops
PML_INTERACTIVE_MODE=1 pymusiclooper /path/to/audio.mp3

# Batch process multiple files
pymusiclooper /path/to/audio/folder --batch --recursive --output-dir ./output

# Export with custom loop duration constraints
pymusiclooper /path/to/audio.mp3 --min-loop-duration 20 --max-loop-duration 120

# Export extended version with multiple loop repetitions
pymusiclooper /path/to/audio.mp3 --extended-length 300 --fade-length 5

# Export loop points to text file
pymusiclooper /path/to/audio.mp3 --to-txt --output-dir ./output

# Split audio into intro/loop/outro sections
pymusiclooper /path/to/audio.mp3 --split-audio --output-dir ./output

# Export with custom tags
pymusiclooper /path/to/audio.mp3 --tag-names "LOOP_START,LOOP_END"
```

### Python API Usage

#### Basic Loop Finding
```python
from pymusiclooper.core.core import MusicLooper

# Create a MusicLooper instance
looper = MusicLooper("path/to/audio.mp3")

# Find loop points with various options
loops = looper.find_loop_pairs(
    min_loop_duration=30,      # Minimum loop duration in seconds
    max_loop_duration=120,     # Maximum loop duration in seconds
    num_loops=5,               # Number of diverse loops to find
    disable_pruning=False      # Enable/disable loop pruning
)

# Export the first loop
looper.export(
    loop_start=loops[0].loop_start,
    loop_end=loops[0].loop_end,
    output_dir="./output",
    format="WAV"
)

# Export extended version with loop repetitions
looper.extend(
    loop_start=loops[0].loop_start,
    loop_end=loops[0].loop_end,
    extended_length=300,       # Target length in seconds
    fade_length=5.0,           # Fade duration in seconds
    output_dir="./output"
)
```

#### Advanced Loop Analysis
```python
from pymusiclooper.utils.handler import LoopHandler

# Create handler with advanced options
handler = LoopHandler(
    path="path/to/audio.mp3",
    min_duration_multiplier=0.35,
    min_loop_duration=15,
    max_loop_duration=180,
    brute_force=True,          # Enable brute force search
    disable_pruning=True       # Disable loop pruning
)

# Get all discovered loops
all_loops = handler.get_all_loop_pairs()

# Interactive loop selection
if handler.interactive_mode:
    selected_index = handler.interactive_handler()
    chosen_loop = all_loops[selected_index]
```

#### Creating Music Videos
```python
from pymusiclooper.effects.glitcher import create_glitch_animation
from pymusiclooper.video.makemovie import adjust_gif_length, export_video

# Create a glitch art animation
gif_path = create_glitch_animation(num_frames=20)

# Combine with audio
video, audio = adjust_gif_length(gif_path, "path/to/loop.mp3")
export_video(video, audio, "output.mp4")
```

#### YouTube Processing
```python
from pymusiclooper.downloader.youtube import download_video

# Download and extract audio from YouTube
audio_path = download_video("https://youtube.com/watch?v=...")
```

#### Batch Processing
```python
from pymusiclooper.utils.handler import BatchHandler

# Process multiple files
batch_handler = BatchHandler(
    path="/path/to/audio/folder",
    min_duration_multiplier=0.35,
    output_dir="./output",
    recursive=True,           # Process subdirectories
    flatten=False,            # Maintain directory structure
    split_audio=True,         # Split into intro/loop/outro
    to_txt=True,              # Export loop points to text
    extended_length=240       # Create extended versions
)

batch_handler.run()
```

Available at [CHANGELOG.md](CHANGELOG.md)

## Star History

[![Star History Chart](https://api.star-history.com/svg?repos=arkrow/PyMusicLooper&type=Date)](https://www.star-history.com/#arkrow/PyMusicLooper&Date)
