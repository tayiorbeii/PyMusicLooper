"""Common media utility functions."""

import os
import shutil
from typing import Optional, List, Tuple
import subprocess
import json

def ensure_directory(path: str) -> str:
    """Ensure a directory exists, creating it if necessary.
    
    Args:
        path: Directory path to ensure exists
        
    Returns:
        The absolute path to the directory
    """
    os.makedirs(path, exist_ok=True)
    return os.path.abspath(path)

def clean_filename(filename: str) -> str:
    """Clean a filename to be filesystem safe.
    
    Args:
        filename: Original filename
        
    Returns:
        Cleaned filename
    """
    # Replace problematic characters
    unsafe_chars = ['/', '\\', ':', '*', '?', '"', '<', '>', '|']
    for char in unsafe_chars:
        filename = filename.replace(char, '_')
    return filename

def get_media_info(filepath: str) -> dict:
    """Get information about a media file using ffprobe.
    
    Args:
        filepath: Path to the media file
        
    Returns:
        Dictionary containing media information
    """
    cmd = [
        'ffprobe',
        '-v', 'quiet',
        '-print_format', 'json',
        '-show_format',
        '-show_streams',
        filepath
    ]
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        return json.loads(result.stdout)
    except subprocess.CalledProcessError as e:
        raise Exception(f"Failed to get media info: {e.stderr}")

def get_duration(filepath: str) -> float:
    """Get the duration of a media file in seconds.
    
    Args:
        filepath: Path to the media file
        
    Returns:
        Duration in seconds
    """
    info = get_media_info(filepath)
    return float(info['format']['duration'])

def organize_media(
    source_dir: str,
    target_dir: str,
    extensions: List[str],
    create_subdirs: bool = True
) -> List[str]:
    """Organize media files by moving them to appropriate directories.
    
    Args:
        source_dir: Source directory containing media files
        target_dir: Target directory to organize files into
        extensions: List of file extensions to process (e.g., ['.mp3', '.mp4'])
        create_subdirs: Whether to create subdirectories by extension
        
    Returns:
        List of paths to organized files
    """
    organized_files = []
    ensure_directory(target_dir)
    
    for root, _, files in os.walk(source_dir):
        for file in files:
            ext = os.path.splitext(file)[1].lower()
            if ext in extensions:
                source_path = os.path.join(root, file)
                
                if create_subdirs:
                    # Remove the dot from extension
                    subdir = ext[1:].upper()
                    target_subdir = ensure_directory(os.path.join(target_dir, subdir))
                    target_path = os.path.join(target_subdir, file)
                else:
                    target_path = os.path.join(target_dir, file)
                
                # Handle duplicates by adding a number
                base, ext = os.path.splitext(target_path)
                counter = 1
                while os.path.exists(target_path):
                    target_path = f"{base}_{counter}{ext}"
                    counter += 1
                
                shutil.move(source_path, target_path)
                organized_files.append(target_path)
    
    return organized_files

def extract_audio(
    video_path: str,
    output_path: Optional[str] = None,
    format: str = 'mp3',
    quality: str = '0'
) -> str:
    """Extract audio from a video file.
    
    Args:
        video_path: Path to the video file
        output_path: Optional path for the output audio file
        format: Output audio format (default: 'mp3')
        quality: Audio quality (0 is best, default: '0')
        
    Returns:
        Path to the extracted audio file
    """
    if output_path is None:
        base, _ = os.path.splitext(video_path)
        output_path = f"{base}.{format}"
    
    cmd = [
        'ffmpeg',
        '-i', video_path,
        '-vn',  # No video
        '-acodec', format,
        '-q:a', quality,
        output_path
    ]
    
    try:
        subprocess.run(cmd, capture_output=True, check=True)
        return output_path
    except subprocess.CalledProcessError as e:
        raise Exception(f"Failed to extract audio: {e.stderr}")

def create_thumbnail(
    video_path: str,
    output_path: Optional[str] = None,
    time: float = 0,
    size: Tuple[int, int] = (1280, 720)
) -> str:
    """Create a thumbnail from a video file.
    
    Args:
        video_path: Path to the video file
        output_path: Optional path for the output thumbnail
        time: Time in seconds to take thumbnail from (default: 0)
        size: Tuple of (width, height) for thumbnail (default: 1280x720)
        
    Returns:
        Path to the created thumbnail
    """
    if output_path is None:
        base, _ = os.path.splitext(video_path)
        output_path = f"{base}_thumb.jpg"
    
    cmd = [
        'ffmpeg',
        '-ss', str(time),
        '-i', video_path,
        '-vframes', '1',
        '-s', f"{size[0]}x{size[1]}",
        '-f', 'image2',
        output_path
    ]
    
    try:
        subprocess.run(cmd, capture_output=True, check=True)
        return output_path
    except subprocess.CalledProcessError as e:
        raise Exception(f"Failed to create thumbnail: {e.stderr}") 