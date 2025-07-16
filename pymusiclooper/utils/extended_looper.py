import argparse
import os
import sys
from typing import List

# Add the project directory to the Python path
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

try:
    from pydub import AudioSegment
except ImportError:
    print("Error: pydub is required. Install with: pip install pydub")
    sys.exit(1)

from pymusiclooper.core.core import MusicLooper

def select_non_overlapping_loops(loop_pairs: List, sample_rate: int) -> List:
    """Select the best non-overlapping loop points from all discovered loops.
    
    Args:
        loop_pairs: List of LoopPair objects from MusicLooper
        sample_rate: Audio sample rate for time calculations
        
    Returns:
        List of non-overlapping loop pairs sorted by start position
    """
    if not loop_pairs:
        return []
    
    # Sort by score (best first)
    sorted_pairs = sorted(loop_pairs, key=lambda x: x.score, reverse=True)
    
    selected_loops = []
    
    for candidate in sorted_pairs:
        # Check if this candidate overlaps with any already selected loop
        overlaps = False
        for selected in selected_loops:
            # Check for overlap: candidate starts before selected ends AND candidate ends after selected starts
            if (candidate.loop_start < selected.loop_end and 
                candidate.loop_end > selected.loop_start):
                overlaps = True
                break
        
        if not overlaps:
            selected_loops.append(candidate)
    
    # Sort selected loops by start position for sequential processing
    selected_loops.sort(key=lambda x: x.loop_start)
    
    return selected_loops

def create_extended_version(filepath: str, min_length: float = 10.0, max_length: float = 60.0, 
                          num_repeats: int = 3, min_gap: float = 5.0):
    """Create an extended version of a song by finding all good loop points that don't overlap
    and repeating them sequentially throughout the song.
    
    Args:
        filepath: Path to the audio file
        min_length: Minimum length of loops in seconds
        max_length: Maximum length of loops in seconds  
        num_repeats: Number of times to repeat each loop section (default 3)
        min_gap: Minimum gap between loops in seconds to avoid overlaps
    """
    print(f"Processing: {filepath}")
    
    # Create a MusicLooper instance
    looper = MusicLooper(filepath)
    
    print("Finding all possible loop points...")
    
    # Find all possible loop pairs without pruning to get maximum coverage
    all_loop_pairs = looper.find_loop_pairs(
        min_loop_duration=min_length,
        max_loop_duration=max_length,
        disable_pruning=True,  # Get all possible loops
        brute_force=False      # Keep reasonable performance
    )
    
    if not all_loop_pairs:
        print("No suitable loop points found!")
        return
    
    print(f"Found {len(all_loop_pairs)} potential loop points")
    
    # Select non-overlapping loops
    selected_loops = select_non_overlapping_loops(all_loop_pairs, looper.mlaudio.rate)
    
    if not selected_loops:
        print("No non-overlapping loops found!")
        return
    
    print(f"Selected {len(selected_loops)} non-overlapping loops")
    
    # Load the audio file
    audio = AudioSegment.from_file(filepath)
    
    # Create the extended version
    extended = AudioSegment.empty()
    last_end_samples = 0
    
    print("Creating extended version...")
    
    for i, loop_pair in enumerate(selected_loops):
        # Convert samples to milliseconds for pydub
        loop_start_ms = int(loop_pair.loop_start * 1000 / looper.mlaudio.rate)
        loop_end_ms = int(loop_pair.loop_end * 1000 / looper.mlaudio.rate)
        last_end_ms = int(last_end_samples * 1000 / looper.mlaudio.rate)
        
        # Add section before the loop if there is one
        if loop_start_ms > last_end_ms:
            bridge_section = audio[last_end_ms:loop_start_ms]
            extended += bridge_section
            print(f"  Added bridge section: {last_end_ms/1000:.1f}s - {loop_start_ms/1000:.1f}s")
        
        # Add the loop section repeated num_repeats times
        loop_section = audio[loop_start_ms:loop_end_ms]
        loop_duration = (loop_end_ms - loop_start_ms) / 1000
        
        print(f"  Loop {i+1}: {loop_start_ms/1000:.1f}s - {loop_end_ms/1000:.1f}s "
              f"({loop_duration:.1f}s) x{num_repeats} repeats, score: {loop_pair.score:.2%}")
        
        # Add original loop once, then repeat it (num_repeats - 1) more times
        extended += loop_section * num_repeats
        
        last_end_samples = loop_pair.loop_end
    
    # Add any remaining audio after the last loop
    last_end_ms = int(last_end_samples * 1000 / looper.mlaudio.rate)
    if last_end_ms < len(audio):
        remaining_section = audio[last_end_ms:]
        extended += remaining_section
        print(f"  Added final section: {last_end_ms/1000:.1f}s - {len(audio)/1000:.1f}s")
    
    # Create output directory and export
    output_dir = os.path.join(os.path.dirname(filepath), 'output')
    os.makedirs(output_dir, exist_ok=True)
    
    filename = os.path.splitext(os.path.basename(filepath))[0]
    output_path = os.path.join(output_dir, f"{filename}_extended.mp3")
    
    print(f"Exporting extended version...")
    extended.export(output_path, format="mp3")
    
    original_duration = len(audio) / 1000
    extended_duration = len(extended) / 1000
    extension_ratio = extended_duration / original_duration
    
    print(f"Original duration: {original_duration:.1f}s")
    print(f"Extended duration: {extended_duration:.1f}s")
    print(f"Extension ratio: {extension_ratio:.1f}x")
    print(f"Created extended version at: {output_path}")

def main():
    parser = argparse.ArgumentParser(
        description='Create an extended version of a song by finding all good non-overlapping loop points and repeating them sequentially.'
    )
    parser.add_argument('filepath', type=str, help='Path to the audio file')
    parser.add_argument('--min-length', type=float, default=10.0, 
                       help='Minimum length of loops in seconds (default: 10.0)')
    parser.add_argument('--max-length', type=float, default=60.0, 
                       help='Maximum length of loops in seconds (default: 60.0)')
    parser.add_argument('--num-repeats', type=int, default=3, 
                       help='Number of times to repeat each loop section (default: 3)')
    parser.add_argument('--min-gap', type=float, default=5.0, 
                       help='Minimum gap between loops in seconds (default: 5.0)')

    args = parser.parse_args()

    create_extended_version(
        filepath=args.filepath,
        min_length=args.min_length,
        max_length=args.max_length,
        num_repeats=args.num_repeats,
        min_gap=args.min_gap
    )

if __name__ == "__main__":
    main()