import argparse
import subprocess
import os
import json
from typing import Optional
from pymusiclooper.core.core import MusicLooper

def export_best_loops(filepath: str, min_length: float, max_length: float, num_loops: int, target_dir: Optional[str] = None):
    # Create a MusicLooper instance
    looper = MusicLooper(filepath)

    try:
        # Find all loop pairs
        loop_pairs = looper.find_loop_pairs(min_loop_duration=min_length, max_loop_duration=max_length)[:num_loops]
    except Exception as e:
        print(f"Error finding loop pairs: {e}")
        return


    # Sort the loop pairs by their duration and get the top 'num_loops' loops
    # loop_pairs = sorted(loop_pairs, key=lambda lp: lp.loop_end - lp.loop_start, reverse=True)[:num_loops]
    

    # Check if target_dir is a valid directory
    if target_dir and not os.path.isdir(target_dir):
        print(f"Error: {target_dir} is not a valid directory.")
        return

    # Export each loop to a file
    for i, loop_pair in enumerate(loop_pairs):
        print(f"Exporting loop pair {i}: {loop_pair}")  # Check if this line is being executed
        try:
            # Update the filename to be the original input file from the filepath + the i
            filename = os.path.splitext(os.path.basename(filepath))[0] + '_' + str(i)
            looper.export(loop_start=loop_pair.loop_start, loop_end=loop_pair.loop_end, filename=filename, output_dir=target_dir)
        
            # Run the sox command
            output_filename = os.path.join(target_dir, filename + '-looped')
            sox_command = ['sox', os.path.join(target_dir, filename + "-loop.wav"), output_filename + ".mp3", 'repeat', '10']
            try:
                subprocess.run(sox_command, check=True)
            except subprocess.CalledProcessError as e:
                print(f"Error running sox command for loop pair {i}: {e}")
        except Exception as e:
            print(f"Error exporting loop pair {i}: {e}")

def download_and_process_videos(video_urls: list[str], min_length: float, max_length: float, num_loops: int, target_dir: Optional[str] = None):
    for url in video_urls:
        # get actual video title
        yt_dlp_command = ['yt-dlp', '--skip-download', '--get-title', '-o', '%(title)s.%(ext)s', '-k', url]
        try:
            video_title = subprocess.run(yt_dlp_command, check=True, capture_output=True)
            
        except subprocess.CalledProcessError as e:
            print(f"Error getting video title for video {url}: {e}")
            continue

        # replace any non-filesystem characters with underscores
        video_title = video_title.stdout.decode('utf-8').strip().replace('/', '_').replace('\\', '_').replace(':', '_').replace('*', '_').replace('?', '_').replace('"', '_').replace('<', '_').replace('>', '_').replace('|', '_')

        # Create a directory for the video
        video_dir = os.path.join(target_dir, video_title)
        os.makedirs(video_dir, exist_ok=True)

        # Run the yt-dlp command to download the audio
        output_filename = os.path.join(video_dir, video_title)

        yt_dlp_command = ['yt-dlp', '--extract-audio', '--audio-format', 'mp3', '--audio-quality', '0', '-k', '--restrict-filenames', '-o', output_filename, url]

        try:
            subprocess.run(yt_dlp_command, check=True)
        except subprocess.CalledProcessError as e:
            print(f"Error downloading video {url}: {e}")
            continue

        # Get the name of the downloaded file
        downloaded_file = output_filename + '.mp3'
        

        # Call the export_best_loops function for the downloaded file
        export_best_loops(downloaded_file, min_length, max_length, num_loops, video_dir)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Export best loops from an audio file.')
    parser.add_argument('json_file', type=str, help='Path to the .json file containing YouTube URLs.')
    parser.add_argument('min_length', type=float, help='Minimum length of loops.')
    parser.add_argument('max_length', type=float, help='Maximum length of loops.')
    parser.add_argument('num_loops', type=int, help='Number of loops to export.')
    parser.add_argument('--target_dir', type=str, default=None, help='Directory to export the loops to.')

    args = parser.parse_args()

    # Load the YouTube URLs from the .json file
    with open(args.json_file, 'r') as f:
        video_urls = json.load(f)

    download_and_process_videos(video_urls, args.min_length, args.max_length, args.num_loops, args.target_dir)
