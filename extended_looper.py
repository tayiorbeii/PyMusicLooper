#!/usr/bin/env python3
"""
Extended Looper Script for PyMusicLooper

This script creates extended versions of songs by finding all good non-overlapping 
loop points and repeating them sequentially throughout the song.
"""

import argparse
import os
import sys
from typing import List

# Add the project directory to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from pydub import AudioSegment
except ImportError:
    print("Error: pydub is required. Install with: pip install pydub")
    sys.exit(1)

from pymusiclooper.core.core import MusicLooper

def format_timestamp(seconds: float) -> str:
    """Convert seconds to MM:SS format.
    
    Args:
        seconds: Time in seconds
        
    Returns:
        Formatted timestamp as MM:SS string
    """
    minutes = int(seconds // 60)
    seconds = int(seconds % 60)
    return f"{minutes}:{seconds:02d}"

def crossfade_segments(segment1: AudioSegment, segment2: AudioSegment, fade_duration: float) -> AudioSegment:
    """Crossfade two audio segments together.
    
    Args:
        segment1: First audio segment
        segment2: Second audio segment  
        fade_duration: Duration of crossfade in seconds
        
    Returns:
        Combined audio segment with crossfade applied
    """
    if fade_duration <= 0:
        return segment1 + segment2
    
    fade_ms = int(fade_duration * 1000)
    
    # Ensure fade duration doesn't exceed segment lengths
    fade_ms = min(fade_ms, len(segment1), len(segment2))
    
    if fade_ms <= 0:
        return segment1 + segment2
    
    # Apply fade out to end of first segment
    segment1_faded = segment1.fade_out(fade_ms)
    
    # Apply fade in to beginning of second segment
    segment2_faded = segment2.fade_in(fade_ms)
    
    # Combine: take all of segment1 except the fade portion, 
    # then overlay the fade portions, then add the rest of segment2
    if len(segment1) > fade_ms and len(segment2) > fade_ms:
        # Extract fade portions
        segment1_fade_portion = segment1[-fade_ms:].fade_out(fade_ms)
        segment2_fade_portion = segment2[:fade_ms].fade_in(fade_ms)
        
        # Overlay the fade portions
        overlayed_fade = segment1_fade_portion.overlay(segment2_fade_portion)
        
        # Combine everything
        result = segment1[:-fade_ms] + overlayed_fade + segment2[fade_ms:]
        return result
    else:
        # For very short segments, just use simple concatenation with fades
        return segment1_faded + segment2_faded

def select_non_overlapping_loops(loop_pairs: List) -> List:
    """Select the best non-overlapping loop points from all discovered loops.
    
    Args:
        loop_pairs: List of LoopPair objects from MusicLooper
        
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
                          num_repeats: int = 3, min_gap: float = 5.0, fade_duration: float = 0.1,
                          min_confidence: float = 0.9):
    """Create an extended version of a song by finding all good loop points that don't overlap
    and repeating them sequentially throughout the song.
    
    Args:
        filepath: Path to the audio file
        min_length: Minimum length of loops in seconds
        max_length: Maximum length of loops in seconds  
        num_repeats: Number of times to repeat each loop section (default 3)
        min_gap: Minimum gap between loops in seconds to avoid overlaps
        fade_duration: Duration of crossfade between segments in seconds (default 0.1)
        min_confidence: Minimum confidence level for loops (0.0-1.0, default 0.9)
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
    
    # Filter loops by minimum confidence level
    filtered_loops = [loop for loop in all_loop_pairs if loop.score >= min_confidence]
    
    if not filtered_loops:
        print(f"No loops found with confidence >= {min_confidence:.1%}!")
        return
    
    print(f"Filtered to {len(filtered_loops)} loops with confidence >= {min_confidence:.1%}")
    
    # Select non-overlapping loops
    selected_loops = select_non_overlapping_loops(filtered_loops)
    
    if not selected_loops:
        print("No non-overlapping loops found!")
        return
    
    print(f"Selected {len(selected_loops)} non-overlapping loops")
    
    # Load the audio file
    audio = AudioSegment.from_file(filepath)
    
    # Create the extended version
    extended = AudioSegment.empty()
    last_end_samples = 0
    
    print(f"Creating extended version with {fade_duration:.3f}s crossfade and {min_confidence:.1%} min confidence...")
    
    for i, loop_pair in enumerate(selected_loops):
        # Convert samples to milliseconds for pydub
        loop_start_ms = int(loop_pair.loop_start * 1000 / looper.mlaudio.rate)
        loop_end_ms = int(loop_pair.loop_end * 1000 / looper.mlaudio.rate)
        last_end_ms = int(last_end_samples * 1000 / looper.mlaudio.rate)
        
        # Add section before the loop if there is one
        if loop_start_ms > last_end_ms:
            bridge_section = audio[last_end_ms:loop_start_ms]
            
            if len(extended) > 0:
                # Use crossfade to connect bridge section to existing audio
                extended = crossfade_segments(extended, bridge_section, fade_duration)
            else:
                # First segment, no crossfade needed
                extended = bridge_section
            
            print(f"  Added bridge section: {last_end_ms/1000:.1f}s - {loop_start_ms/1000:.1f}s")
        
        # Add the loop section repeated num_repeats times
        loop_section = audio[loop_start_ms:loop_end_ms]
        loop_duration = (loop_end_ms - loop_start_ms) / 1000
        
        print(f"  Loop {i+1}: {loop_start_ms/1000:.1f}s - {loop_end_ms/1000:.1f}s "
              f"({loop_duration:.1f}s) x{num_repeats} repeats, score: {loop_pair.score:.2%}")
        
        # Create the repeated loop section
        repeated_loop = loop_section * num_repeats
        
        # Add with crossfade
        if len(extended) > 0:
            extended = crossfade_segments(extended, repeated_loop, fade_duration)
        else:
            extended = repeated_loop
        
        last_end_samples = loop_pair.loop_end
    
    # Add any remaining audio after the last loop
    last_end_ms = int(last_end_samples * 1000 / looper.mlaudio.rate)
    if last_end_ms < len(audio):
        remaining_section = audio[last_end_ms:]
        
        if len(extended) > 0:
            # Use crossfade to connect final section to existing audio
            extended = crossfade_segments(extended, remaining_section, fade_duration)
        else:
            extended = remaining_section
        
        print(f"  Added final section: {last_end_ms/1000:.1f}s - {len(audio)/1000:.1f}s")
    
    # Create output directory and export
    output_dir = os.path.join(os.path.dirname(filepath), 'output')
    os.makedirs(output_dir, exist_ok=True)
    
    filename = os.path.splitext(os.path.basename(filepath))[0]
    output_path = os.path.join(output_dir, f"{filename}_extended.mp3")
    
    print(f"Exporting extended version...")
    extended.export(output_path, format="mp3", bitrate="320k")
    
    original_duration = len(audio) / 1000
    extended_duration = len(extended) / 1000
    extension_ratio = extended_duration / original_duration
    
    print(f"Original duration: {original_duration:.1f}s")
    print(f"Extended duration: {extended_duration:.1f}s")
    print(f"Extension ratio: {extension_ratio:.1f}x")
    print(f"Created extended version at: {output_path}")
    
    # Create comprehensive loop report
    report_path = os.path.join(output_dir, f"{filename}_loop_report.txt")
    with open(report_path, 'w') as f:
        f.write("=" * 80 + "\n")
        f.write(f"EXTENDED LOOP REPORT - {filename}\n")
        f.write("=" * 80 + "\n\n")
        
        f.write("SUMMARY:\n")
        f.write("-" * 40 + "\n")
        f.write(f"Original file: {os.path.basename(filepath)}\n")
        f.write(f"Original duration: {format_timestamp(original_duration)}\n")
        f.write(f"Extended duration: {format_timestamp(extended_duration)}\n")
        f.write(f"Extension ratio: {extension_ratio:.1f}x\n")
        f.write(f"Total loops found: {len(all_loop_pairs)}\n")
        f.write(f"Loops with confidence >= {min_confidence:.1%}: {len(filtered_loops)}\n")
        f.write(f"Non-overlapping loops selected: {len(selected_loops)}\n")
        f.write(f"Repeats per loop: {num_repeats}\n")
        f.write(f"Crossfade duration: {fade_duration:.3f}s\n\n")
        
        f.write("LOOP DETAILS:\n")
        f.write("-" * 40 + "\n")
        
        extended_time = 0.0
        last_end_samples = 0
        
        for i, loop_pair in enumerate(selected_loops):
            loop_start_sec = loop_pair.loop_start / looper.mlaudio.rate
            loop_end_sec = loop_pair.loop_end / looper.mlaudio.rate
            loop_duration = loop_end_sec - loop_start_sec
            last_end_sec = last_end_samples / looper.mlaudio.rate
            
            # Add time for bridge section before this loop
            if loop_start_sec > last_end_sec:
                bridge_duration = loop_start_sec - last_end_sec
                extended_time += bridge_duration
                f.write(f"Bridge section: {format_timestamp(extended_time - bridge_duration)} - {format_timestamp(extended_time)} ({format_timestamp(bridge_duration)})\n")
            
            # The loop starts at extended_time in the extended version
            extended_loop_start = extended_time
            
            # Add the loop duration * num_repeats
            extended_time += loop_duration * num_repeats
            
            f.write(f"Loop {i+1}:\n")
            f.write(f"  Original position: {format_timestamp(loop_start_sec)} - {format_timestamp(loop_end_sec)}\n")
            f.write(f"  Extended position: {format_timestamp(extended_loop_start)} - {format_timestamp(extended_time)}\n")
            f.write(f"  Duration: {format_timestamp(loop_duration)}\n")
            f.write(f"  Repeats: {num_repeats}x\n")
            f.write(f"  Total extended time: {format_timestamp(loop_duration * num_repeats)}\n")
            f.write(f"  Quality score: {loop_pair.score:.2%}\n")
            f.write(f"  Note distance: {loop_pair.note_distance:.3f}\n")
            f.write(f"  Loudness difference: {loop_pair.loudness_difference:.3f}\n\n")
            
            last_end_samples = loop_pair.loop_end
        
        # Add final section info if it exists
        final_start_sec = last_end_samples / looper.mlaudio.rate
        if final_start_sec < original_duration:
            final_duration = original_duration - final_start_sec
            extended_time += final_duration
            f.write(f"Final section: {format_timestamp(extended_time - final_duration)} - {format_timestamp(extended_time)} ({format_timestamp(final_duration)})\n\n")
        
        f.write("NAVIGATION GUIDE:\n")
        f.write("-" * 40 + "\n")
        f.write("Use these timestamps to navigate the extended version:\n\n")
        
        extended_time = 0.0
        last_end_samples = 0
        
        for i, loop_pair in enumerate(selected_loops):
            loop_start_sec = loop_pair.loop_start / looper.mlaudio.rate
            loop_end_sec = loop_pair.loop_end / looper.mlaudio.rate
            loop_duration = loop_end_sec - loop_start_sec
            last_end_sec = last_end_samples / looper.mlaudio.rate
            
            # Add time for bridge section before this loop
            if loop_start_sec > last_end_sec:
                bridge_duration = loop_start_sec - last_end_sec
                extended_time += bridge_duration
            
            # The loop starts at extended_time in the extended version
            extended_loop_start = extended_time
            extended_time += loop_duration * num_repeats
            
            f.write(f"Loop {i+1}: {format_timestamp(extended_loop_start)} - {format_timestamp(extended_time)} ")
            f.write(f"({format_timestamp(loop_duration)} × {num_repeats})\n")
            
            last_end_samples = loop_pair.loop_end
        
        f.write(f"\nTotal extended duration: {format_timestamp(extended_time)}\n")
        
    print(f"Created loop report at: {report_path}")

def process_multiple_files(filepaths, min_length=10.0, max_length=60.0, num_repeats=3, min_gap=5.0, fade_duration=0.1, min_confidence=0.9):
    """Process multiple audio files for extended loop creation.
    
    Args:
        filepaths: List of paths to audio files
        min_length: Minimum length of loops in seconds
        max_length: Maximum length of loops in seconds
        num_repeats: Number of times to repeat each loop section
        min_gap: Minimum gap between loops in seconds
        fade_duration: Duration of crossfade between segments in seconds
        min_confidence: Minimum confidence level for loops (0.0-1.0)
    """
    total_files = len(filepaths)
    successful_files = 0
    failed_files = []
    
    print(f"Processing {total_files} files...")
    print("=" * 60)
    
    for i, filepath in enumerate(filepaths, 1):
        print(f"\n[{i}/{total_files}] Processing: {os.path.basename(filepath)}")
        print("-" * 50)
        
        try:
            # Check if file exists
            if not os.path.exists(filepath):
                print(f"ERROR: File not found: {filepath}")
                failed_files.append((filepath, "File not found"))
                continue
            
            # Check if file is a supported audio format
            supported_extensions = {'.mp3', '.wav', '.flac', '.m4a', '.aac', '.ogg', '.wma'}
            file_ext = os.path.splitext(filepath)[1].lower()
            if file_ext not in supported_extensions:
                print(f"WARNING: Unsupported file format: {file_ext}")
                print(f"Supported formats: {', '.join(supported_extensions)}")
                failed_files.append((filepath, f"Unsupported format: {file_ext}"))
                continue
            
            # Process the file
            create_extended_version(
                filepath=filepath,
                min_length=min_length,
                max_length=max_length,
                num_repeats=num_repeats,
                min_gap=min_gap,
                fade_duration=fade_duration,
                min_confidence=min_confidence
            )
            successful_files += 1
            print(f"✓ Successfully processed: {os.path.basename(filepath)}")
            
        except Exception as e:
            print(f"ERROR processing {os.path.basename(filepath)}: {str(e)}")
            failed_files.append((filepath, str(e)))
    
    # Summary
    print("\n" + "=" * 60)
    print("BATCH PROCESSING SUMMARY")
    print("=" * 60)
    print(f"Total files: {total_files}")
    print(f"Successful: {successful_files}")
    print(f"Failed: {len(failed_files)}")
    
    if failed_files:
        print("\nFailed files:")
        for filepath, error in failed_files:
            print(f"  - {os.path.basename(filepath)}: {error}")
    
    print(f"\nProcessing complete! {successful_files}/{total_files} files processed successfully.")

def main():
    parser = argparse.ArgumentParser(
        description='Create extended versions of songs by finding all good non-overlapping loop points and repeating them sequentially.'
    )
    parser.add_argument('filepaths', nargs='+', type=str, help='Paths to audio files (supports multiple files)')
    parser.add_argument('--min-length', type=float, default=10.0, 
                       help='Minimum length of loops in seconds (default: 10.0)')
    parser.add_argument('--max-length', type=float, default=60.0, 
                       help='Maximum length of loops in seconds (default: 60.0)')
    parser.add_argument('--num-repeats', type=int, default=3, 
                       help='Number of times to repeat each loop section (default: 3)')
    parser.add_argument('--min-gap', type=float, default=5.0, 
                       help='Minimum gap between loops in seconds (default: 5.0)')
    parser.add_argument('--fade-duration', type=float, default=0.1, 
                       help='Duration of crossfade between segments in seconds (default: 0.1)')
    parser.add_argument('--min-confidence', type=float, default=0.9, 
                       help='Minimum confidence level for loops (0.0-1.0, default: 0.9)')

    args = parser.parse_args()

    if len(args.filepaths) == 1:
        # Single file processing
        create_extended_version(
            filepath=args.filepaths[0],
            min_length=args.min_length,
            max_length=args.max_length,
            num_repeats=args.num_repeats,
            min_gap=args.min_gap,
            fade_duration=args.fade_duration,
            min_confidence=args.min_confidence
        )
    else:
        # Multiple file processing
        process_multiple_files(
            filepaths=args.filepaths,
            min_length=args.min_length,
            max_length=args.max_length,
            num_repeats=args.num_repeats,
            min_gap=args.min_gap,
            fade_duration=args.fade_duration,
            min_confidence=args.min_confidence
        )

if __name__ == "__main__":
    main()