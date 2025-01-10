import argparse
import subprocess
import os
import json
from typing import Optional, List
from pymusiclooper.core import MusicLooper
from pymusiclooper.analysis import LoopPair

def get_json_filename(filepath: str) -> str:
    """Get the JSON filename for storing loops"""
    base = os.path.splitext(filepath)[0]
    return f"{base}_loops.json"

def save_loops_to_json(filepath: str, loop_pairs: List[LoopPair]):
    """Save all detected loops to a JSON file"""
    loops_data = []
    for pair in loop_pairs:
        loops_data.append({
            "loop_start": pair.loop_start,
            "loop_end": pair.loop_end,
            "note_distance": pair.note_distance,
            "loudness_difference": pair.loudness_difference,
            "score": pair.score
        })
    
    json_file = get_json_filename(filepath)
    with open(json_file, 'w') as f:
        json.dump(loops_data, f, indent=2)
    print(f"Saved {len(loops_data)} loops to {json_file}")

def load_loops_from_json(filepath: str) -> Optional[List[LoopPair]]:
    """Load loops from JSON if available"""
    json_file = get_json_filename(filepath)
    if not os.path.exists(json_file):
        return None
        
    with open(json_file) as f:
        loops_data = json.load(f)
        
    loop_pairs = []
    for data in loops_data:
        pair = LoopPair(
            _loop_start_frame_idx=0,  # These will be recalculated if needed
            _loop_end_frame_idx=0,
            note_distance=float(data["note_distance"]),
            loudness_difference=float(data["loudness_difference"]),
            score=float(data["score"])
        )
        pair.loop_start = float(data["loop_start"])
        pair.loop_end = float(data["loop_end"])
        loop_pairs.append(pair)
        
    print(f"Loaded {len(loop_pairs)} loops from {json_file}")
    return loop_pairs

def export_best_loops(filepath: str, min_length: float, max_length: float, num_loops: int, target_dir: Optional[str] = None):
    # Create a MusicLooper instance
    looper = MusicLooper(filepath)

    # Find all loop pairs with pruning disabled to get all possible loops
    loop_pairs = looper.find_loop_pairs(
        min_loop_duration=min_length, 
        max_loop_duration=max_length,
        disable_pruning=True  # Get all possible loops
    )
    
    # Save all detected loops to JSON
    save_loops_to_json(filepath, loop_pairs)

    # Sort all loops by score and get the top num_loops
    loop_pairs = sorted(loop_pairs, key=lambda lp: lp.score, reverse=True)[:num_loops]
    print(f"Selected {len(loop_pairs)} best scoring loops")

    # Check if target_dir is a valid directory
    if target_dir and not os.path.isdir(target_dir):
        print(f"Error: {target_dir} is not a valid directory.")
        return

    # Export each loop to a file
    for i, loop_pair in enumerate(loop_pairs):
        print(f"Exporting loop pair {i}: {loop_pair}")
        try:
            filename = os.path.splitext(os.path.basename(filepath))[0] + '_' + str(i) + '.mp3'
            output_dir = os.path.join(target_dir if target_dir else os.path.dirname(filepath), 'output')
            os.makedirs(output_dir, exist_ok=True)
            
            # Create a new MusicLooper instance for exporting
            looper = MusicLooper(filepath)
            looper.export(loop_start=loop_pair.loop_start, loop_end=loop_pair.loop_end, filename=filename, output_dir=output_dir)
        
            # Run the sox command
            output_filename = filename.replace('.mp3', '-looped.mp3')
            sox_command = ['sox', os.path.join(output_dir, filename + "-loop.wav"), os.path.join(output_dir, output_filename), 'repeat', '10']
            try:
                subprocess.run(sox_command, check=True)
            except subprocess.CalledProcessError as e:
                print(f"Error running sox command for loop pair {i}: {e}")
        except Exception as e:
            print(f"Error exporting loop pair {i}: {e}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Export best loops from an audio file.')
    parser.add_argument('filepath', type=str, help='Path to the audio file.')
    parser.add_argument('min_length', type=float, help='Minimum length of loops.')
    parser.add_argument('max_length', type=float, help='Maximum length of loops.')
    parser.add_argument('num_loops', type=int, help='Number of loops to export.')
    parser.add_argument('--target_dir', type=str, default=None, help='Directory to export the loops to.')

    args = parser.parse_args()

    export_best_loops(args.filepath, args.min_length, args.max_length, args.num_loops, args.target_dir)