"""YouTube video downloading utilities."""

import os
from typing import Optional
import subprocess

def download_video(url: str, output_dir: Optional[str] = None) -> str:
    """Download a video from YouTube and extract its audio.
    
    Args:
        url: YouTube URL to download
        output_dir: Optional directory to save the file in
        
    Returns:
        Path to the downloaded audio file
    """
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)
        output_template = os.path.join(output_dir, '%(title)s.%(ext)s')
    else:
        output_template = '%(title)s.%(ext)s'
    
    # Download audio only
    command = [
        'yt-dlp',
        '-x',  # Extract audio
        '--audio-format', 'mp3',  # Convert to MP3
        '--audio-quality', '0',  # Best quality
        '-o', output_template,
        url
    ]
    
    try:
        result = subprocess.run(command, capture_output=True, text=True, check=True)
        
        # Parse output to get the filename
        for line in result.stdout.split('\n'):
            if '[ExtractAudio] Destination:' in line:
                return line.split(': ')[1].strip()
                
        # If we can't find the exact file, look for any MP3 in the directory
        if output_dir:
            files = os.listdir(output_dir)
            mp3_files = [f for f in files if f.endswith('.mp3')]
            if mp3_files:
                return os.path.join(output_dir, mp3_files[0])
                
        raise Exception("Could not find downloaded file")
        
    except subprocess.CalledProcessError as e:
        raise Exception(f"Failed to download video: {e.stderr}")
