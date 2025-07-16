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

assets/                # Static assets
├── img/              # Image assets
└── media/            # Media files

output/               # Generated content
├── LooperOutput/     # Generated loops
├── glitch-gifs/      # Generated glitch art
├── finished/         # Final videos
└── downloads/        # Downloaded content
```

## Installation

### From PyPI
```bash
pip install pymusiclooper
```

### From Source
```bash
git clone https://github.com/arkrow/PyMusicLooper.git
cd PyMusicLooper
pip install -e .
```

### Development Installation
```bash
git clone https://github.com/arkrow/PyMusicLooper.git
cd PyMusicLooper
poetry install
```

## Usage

### CLI Usage

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

## Configuration

PyMusicLooper supports various configuration options through environment variables:

- `PML_INTERACTIVE_MODE`: Enable interactive mode for loop selection
- `PML_DISPLAY_SAMPLES`: Display loop points in samples instead of time format

### Configuration Files

The project includes predefined configuration files in `pymusiclooper/config/`:
- `videos.json`: YouTube video URLs for processing
- `groove.json`, `groove2.json`: Groove music configurations
- `jazz.json`: Jazz music configurations  
- `cosmic.json`: Cosmic music configurations
- `polygon.json`: Polygon music configurations

## CLI Options

Common command-line options:
- `--output-dir`: Specify output directory
- `--batch`: Process multiple files in a directory
- `--recursive`: Process subdirectories recursively
- `--min-loop-duration`: Minimum loop duration (seconds)
- `--max-loop-duration`: Maximum loop duration (seconds)
- `--extended-length`: Create extended version with target length
- `--fade-length`: Fade duration for extended versions
- `--split-audio`: Split into intro/loop/outro sections
- `--to-txt`: Export loop points to text file
- `--to-stdout`: Print loop points to stdout
- `--tag-names`: Export custom tags to audio file
- `--brute-force`: Enable brute force loop search
- `--disable-pruning`: Disable loop pruning algorithm
- `--format`: Output audio format (WAV, MP3, etc.)

## Requirements

- Python 3.8+
- ffmpeg
- sox  
- yt-dlp

## Dependencies

See pyproject.toml for the complete list of Python dependencies.

## Examples

### Extended Looper Script
The repository includes an `extended_looper.py` script that creates very long versions of songs by finding all good non-overlapping loop points and repeating them sequentially throughout the song.

#### How it works:
1. Finds all potential loop points in the song
2. Filters loops by minimum confidence level (default 90%)
3. Selects the best non-overlapping loops (no temporal overlap)
4. Plays the original song until the first loop point
5. Repeats the first loop section N times (default 3) with crossfade transitions
6. Continues with original audio until the next loop point
7. Repeats the process for all selected loops
8. Adds any remaining audio after the last loop with smooth crossfades

#### CLI Usage:
```bash
# Basic usage - finds non-overlapping loops and repeats them 3 times each
python extended_looper.py path/to/song.mp3

# Custom parameters
python extended_looper.py path/to/song.mp3 \
    --min-length 15 \           # Minimum loop duration in seconds
    --max-length 45 \           # Maximum loop duration in seconds  
    --num-repeats 4 \           # Times to repeat each loop section
    --fade-duration 0.05 \      # Crossfade duration between segments (seconds)
    --min-confidence 0.8        # Minimum confidence level for loops (0.0-1.0)

# Process multiple files
python extended_looper.py song1.mp3 song2.mp3 song3.mp3

# High-quality loops only with short crossfades
python extended_looper.py path/to/song.mp3 \
    --min-confidence 0.95 \     # Very high confidence threshold
    --fade-duration 0.02        # Very short crossfade

# Find multiple short loops instead of few long ones
python extended_looper.py path/to/song.mp3 \
    --min-length 3 \            # Allow 3-second loops
    --max-length 15 \           # Maximum 15-second loops
    --min-confidence 0.7        # Slightly lower confidence for more options
```

#### Python API Usage:
```python
from extended_looper import create_extended_version

# Create an extended version with non-overlapping sequential loops
create_extended_version(
    filepath="path/to/song.mp3",
    min_length=10.0,           # Minimum loop duration
    max_length=60.0,           # Maximum loop duration 
    num_repeats=3,             # Times to repeat each loop section
    min_gap=5.0,               # Minimum gap between loops (seconds)
    fade_duration=0.1,         # Crossfade duration between segments (seconds)
    min_confidence=0.9         # Minimum confidence level for loops (0.0-1.0)
)
```

#### Extended Looper Options:
- `--min-length`: Minimum loop duration in seconds (default: 10.0)
- `--max-length`: Maximum loop duration in seconds (default: 60.0)
- `--num-repeats`: Number of times to repeat each loop section (default: 3)
- `--min-gap`: Minimum gap between loops in seconds (default: 5.0)
- `--fade-duration`: Crossfade duration between segments in seconds (default: 0.1)
- `--min-confidence`: Minimum confidence level for loops 0.0-1.0 (default: 0.9)

#### Output:
The script provides detailed progress information including:
- Number of potential loop points found
- Number of loops filtered by confidence threshold
- Number of non-overlapping loops selected
- Details for each loop (position with MM:SS timestamps, duration, score)
- Crossfade duration applied
- Original vs extended duration and extension ratio
- Output file location in `output/` directory

#### Generated Files:
- `{filename}_extended.mp3`: The extended audio file with repeated loops
- `{filename}_loop_report.txt`: Detailed report with human-readable timestamps (MM:SS format)
  - Summary statistics
  - Loop details with original and extended positions
  - Navigation guide for the extended version

### Output Structure
PyMusicLooper creates organized output directories:
- `output/LooperOutput/`: Basic loop exports
- `output/glitch-gifs/`: Generated glitch art animations
- `output/finished/`: Final processed videos
- `output/downloads/`: Downloaded YouTube content

## License

MIT License
