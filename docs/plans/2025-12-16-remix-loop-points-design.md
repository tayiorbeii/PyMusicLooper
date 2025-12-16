# Remix Loop Points Design

## Overview

Enhance the Infinite Jukebox remix functionality to detect, verify, and export seamless loop points within generated remixes. This allows remixes to contain multiple internal loop points that can be used for perfect looping playback.

## Problem

Currently, `InfiniteJukebox.generate_remix()` creates extended versions by jumping between similar sections, but:

- Loop points aren't explicitly marked or exported
- No verification that planned jumps actually sound seamless in the final audio
- No way to preview transitions before committing
- No standardized metadata format for loop points

## Solution

A three-phase system: **Generation → Verification → Export** with optional interactive curation.

### Phase 1: Generation with Transition Tracking

`generate_remix()` and `generate_composition()` track every section boundary as a potential loop point:

```python
@dataclass
class RemixTransition:
    """Represents a potential loop point in a remix."""
    timestamp_samples: int          # Position in final remix
    timestamp_seconds: float        # Human-readable position
    source_section_id: int          # Which section we're jumping from
    target_section_id: int          # Which section we're jumping to
    planned_similarity: float       # Original connection score
    verified_similarity: float      # Measured similarity in final audio
    transition_type: str            # "jump", "continuation", "restart"
    manually_approved: bool         # User-curated flag
```

**Modified return signature:**

```python
def generate_remix(...) -> Tuple[List[SectionNode], List[RemixTransition]]:
    # Returns both the section list AND transition metadata
```

### Phase 2: Verification

After building the remix audio, analyze each transition to confirm it actually loops smoothly:

```python
def verify_transitions(
    self,
    mlaudio: MLAudio,
    remix_audio: np.ndarray,
    transitions: List[RemixTransition],
    verification_window: float = 2.0  # seconds to analyze around transition
) -> List[RemixTransition]:
    """
    Verify that planned transitions actually sound seamless in final audio.

    For each transition:
    1. Extract audio window around the splice point
    2. Calculate actual similarity using existing analysis algorithms
    3. Update verified_similarity field

    Returns updated transitions list.
    """
```

**Why verify?**

- Crossfading can change perceived similarity
- Audio processing artifacts at splice points
- Edge effects from section boundaries
- Catches degraded quality from cumulative processing

### Phase 3: Export & Interactive Curation

**Option A: Automatic Export** (default)

```python
def export_loop_points_json(
    self,
    transitions: List[RemixTransition],
    output_path: str,
    min_similarity: float = 0.85,
    detailed: bool = False,
    manually_approved_only: bool = False
) -> None:
```

**Option B: Interactive Browser** (`--interactive` flag)

```python
def interactive_loop_browser(
    self,
    mlaudio: MLAudio,
    remix_audio: np.ndarray,
    transitions: List[RemixTransition],
    preview_duration: float = 4.0  # 2s before, 2s after transition
) -> List[RemixTransition]:
    """
    TUI for previewing and curating loop points.

    Features:
    - Arrow keys to navigate transitions
    - Space: play preview (before → crossfade → after)
    - L: loop current transition continuously
    - M: mark/unmark for export
    - A: accept all above threshold
    - Q: quit and export marked loops

    Returns list of approved transitions.
    """
```

**TUI Layout:**

```
╔══════════════════════════════════════════════════════════╗
║ Remix Loop Point Explorer                    [12/47]    ║
╠══════════════════════════════════════════════════════════╣
║ Position: 01:23.45                                       ║
║ Quality: ✓ Excellent (0.92 verified / 0.89 planned)     ║
║ Jump: Section 8 → Section 3                             ║
║ Type: jump (chorus → verse)                             ║
╠══════════════════════════════════════════════════════════╣
║ [Space] Play  [L] Loop  [M] Mark  [A] Accept All  [Q] Quit
╚══════════════════════════════════════════════════════════╝
```

**Quality indicators:**

- ✓ Excellent: verified_similarity >= 0.85
- ~ Medium: 0.70 <= verified_similarity < 0.85
- ✗ Failed: verified_similarity < 0.70

## JSON Export Formats

### Minimal (default)

```json
{
  "remix_file": "song_remix.mp3",
  "duration_seconds": 245.3,
  "loop_points": [
    { "timestamp": 12.45, "quality": 0.92 },
    { "timestamp": 45.67, "quality": 0.88 },
    { "timestamp": 123.45, "quality": 0.91 }
  ]
}
```

### Detailed (`--detailed-metadata`)

```json
{
  "remix_file": "song_remix.mp3",
  "duration_seconds": 245.3,
  "generation_params": {
    "similarity_threshold": 0.7,
    "min_loop_quality": 0.85,
    "jump_probability": 0.3,
    "min_section_duration": 2.0,
    "max_section_duration": 8.0,
    "seed": 42
  },
  "loop_points": [
    {
      "timestamp_seconds": 12.45,
      "timestamp_samples": 551250,
      "planned_similarity": 0.89,
      "verified_similarity": 0.92,
      "source_section": 8,
      "target_section": 3,
      "transition_type": "jump",
      "manually_approved": false
    },
    {
      "timestamp_seconds": 45.67,
      "timestamp_samples": 2023575,
      "planned_similarity": 0.87,
      "verified_similarity": 0.88,
      "source_section": 3,
      "target_section": 12,
      "transition_type": "jump",
      "manually_approved": true
    }
  ]
}
```

## CLI Design

### New Command: `pymusiclooper remix`

```bash
# Basic usage
pymusiclooper remix song.mp3 --target-length 5m

# Full control
pymusiclooper remix song.mp3 \
  --target-length 5m30s \
  --min-section-duration 2s \
  --max-section-duration 8s \
  --similarity-threshold 0.7 \
  --jump-probability 0.3 \
  --min-loop-quality 0.85 \
  --output remix.mp3

# Interactive curation
pymusiclooper remix song.mp3 \
  --target-length 5m \
  --interactive

# Detailed metadata
pymusiclooper remix song.mp3 \
  --target-length 5m \
  --detailed-metadata \
  --min-loop-quality 0.9
```

### Time Format Parsing

Support flexible human-readable time formats:

- `5m30s` → 330 seconds
- `2:30` → 150 seconds (colon notation)
- `150s` → 150 seconds (explicit seconds)
- `2.5m` → 150 seconds (decimal minutes)
- `300` → 300 seconds (raw number fallback)

```python
def parse_time_duration(time_str: str) -> float:
    """
    Parse flexible time formats to seconds.

    Supports:
    - 5m30s (minutes + seconds)
    - 2:30 (MM:SS colon notation)
    - 150s (seconds with unit)
    - 2.5m (decimal minutes)
    - 300 (raw seconds)

    Returns:
        Duration in seconds

    Raises:
        ValueError: If format is invalid
    """
```

### Help Text

```
pymusiclooper remix --help

Create a remixed version with seamless loop points.

The remix algorithm finds similar sections in your song and jumps between them
to create new arrangements. Loop points mark each transition where the audio
seamlessly loops back.

Options:
  --target-length TEXT          Target length of remix [required]
                                Formats: 5m30s, 2:30, 150s, 2.5m, 300

  --min-section-duration TEXT   Minimum section size (default: 2s)
  --max-section-duration TEXT   Maximum section size (default: 8s)

  --similarity-threshold FLOAT  Min similarity for section jumps
                                Range: 0.0-1.0 (default: 0.7)
                                Lower = more diverse, Higher = safer jumps

  --jump-probability FLOAT      How often to jump vs continue sequentially
                                Range: 0.0-1.0 (default: 0.3)
                                Higher = more chaotic remixes

  --min-loop-quality FLOAT      Min similarity to mark as loop point
                                Range: 0.0-1.0 (default: 0.85)
                                Only transitions above this are exported

  --interactive                 Preview and curate loop points interactively
                                Launch TUI to listen and approve transitions

  --detailed-metadata           Export detailed loop point metadata
                                Include section IDs, scores, and generation params

  --seed INTEGER                Random seed for reproducible remixes

  --output PATH                 Output file path
                                (default: {input}_remix.mp3)

  --help                        Show this message and exit.

Examples:
  # Create 5-minute remix
  pymusiclooper remix song.mp3 --target-length 5m

  # High-quality loops only, with interactive preview
  pymusiclooper remix song.mp3 --target-length 3m --min-loop-quality 0.9 --interactive

  # Chaotic remix with frequent jumps
  pymusiclooper remix song.mp3 --target-length 10m --jump-probability 0.7
```

## File Outputs

Running `pymusiclooper remix song.mp3 --target-length 5m` produces:

- `song_remix.mp3` - The remixed audio file
- `song_remix_loops.json` - Loop point metadata

With `--detailed-metadata`:

- `song_remix_loops_detailed.json` - Extended metadata

## Implementation Details

### Modified Methods

**`InfiniteJukebox.generate_remix()`**

- Add `track_transitions: bool = True` parameter
- Track cumulative sample position as sections are added
- Record `RemixTransition` at each section boundary
- Return `(sections, transitions)` tuple instead of just sections

**`InfiniteJukebox.generate_composition()`**

- Same modifications as `generate_remix()`
- Track transitions between macro sections

**`InfiniteJukebox.export_remix_audio()`**

- Add `return_audio: bool = False` parameter
- Optionally return the built audio array for verification
- Keep existing file writing behavior

### New Methods

**`InfiniteJukebox.verify_transitions()`**

```python
def verify_transitions(
    self,
    mlaudio: MLAudio,
    remix_audio: np.ndarray,
    transitions: List[RemixTransition],
    verification_window: float = 2.0
) -> List[RemixTransition]:
```

**`InfiniteJukebox.export_loop_points_json()`**

```python
def export_loop_points_json(
    self,
    transitions: List[RemixTransition],
    output_path: str,
    min_similarity: float = 0.85,
    detailed: bool = False,
    manually_approved_only: bool = False
) -> None:
```

**`InfiniteJukebox.interactive_loop_browser()`**

```python
def interactive_loop_browser(
    self,
    mlaudio: MLAudio,
    remix_audio: np.ndarray,
    transitions: List[RemixTransition],
    preview_duration: float = 4.0
) -> List[RemixTransition]:
```

### New Utilities

**`pymusiclooper.utils.time_parser.py`**

```python
def parse_time_duration(time_str: str) -> float:
    """Parse flexible time formats to seconds."""

def format_time_duration(seconds: float) -> str:
    """Format seconds to human-readable string (MM:SS)."""
```

**`pymusiclooper.utils.loop_browser.py`**

```python
class LoopBrowserTUI:
    """Interactive TUI for previewing and curating loop points."""

    def __init__(self, mlaudio, remix_audio, transitions, preview_duration):
        pass

    def run(self) -> List[RemixTransition]:
        """Run the interactive browser, return approved transitions."""
        pass
```

## Dependencies

### New Dependencies

- `curses` - Built-in on Unix/macOS, `windows-curses` package on Windows
- `sounddevice` - Already an indirect dependency via librosa

### Optional Dependencies

- `windows-curses` - Only needed on Windows for TUI support

## Migration Path

### Backward Compatibility

Existing code continues to work:

```python
# Old API still works
sections = jukebox.generate_remix(mlaudio, target_duration=300)
jukebox.export_remix_audio(mlaudio, sections, "output.mp3")
```

New API is opt-in:

```python
# New API with transition tracking
sections, transitions = jukebox.generate_remix(
    mlaudio,
    target_duration=300,
    track_transitions=True
)

# Build and verify
jukebox.export_remix_audio(mlaudio, sections, "output.mp3", return_audio=True)
remix_audio = jukebox.last_exported_audio  # cached

verified_transitions = jukebox.verify_transitions(
    mlaudio,
    remix_audio,
    transitions
)

# Export metadata
jukebox.export_loop_points_json(
    verified_transitions,
    "output_loops.json",
    min_similarity=0.85
)
```

### CLI Integration

Add new subcommand without breaking existing commands:

- `pymusiclooper` - Existing loop finder (unchanged)
- `pymusiclooper extend` - Existing extender (unchanged)
- `pymusiclooper remix` - **NEW** - Remix with loop points

## Success Criteria

### Must Have

- ✓ Track transitions during remix generation
- ✓ Verify transitions in final audio
- ✓ Export minimal JSON format
- ✓ CLI command with time parsing
- ✓ Configurable quality threshold

### Should Have

- ✓ Detailed JSON export option
- ✓ Interactive TUI browser
- ✓ Preview playback in TUI
- ✓ Manual approval workflow

### Nice to Have

- Import loop points JSON and re-export audio with just those sections
- Export to other formats (CUE sheet, Audacity labels)
- Visualize waveform around transitions in TUI
- Auto-tag MP3 files with loop point metadata

## Open Questions

1. **Verification algorithm** - Reuse `_calculate_subseq_beat_similarity()` or need something different for post-processed audio?
   - **Answer**: Start with existing algorithm, can refine if needed

2. **Crossfade handling** - Should verification analyze pre-fade or post-fade audio?
   - **Answer**: Post-fade (measure what the listener actually hears)

3. **Windows support** - Worth bundling `windows-curses` or make it optional?
   - **Answer**: Make interactive mode gracefully degrade on Windows without curses

4. **Loop point density** - Should we filter out transitions that are too close together?
   - **Answer**: Yes, add `min_gap_between_loops` parameter (default: 5 seconds)

## Future Enhancements

- **Beatmatching** - Tempo-align sections for even smoother transitions
- **Key detection** - Prefer jumps that stay in the same key
- **Energy matching** - Analyze energy levels to avoid jarring volume changes
- **Smart section labeling** - Detect verse/chorus/bridge patterns automatically
- **Loop point visualization** - Generate waveform image with loop points marked
- **Export to DJ software** - Generate cue points for Rekordbox, Serato, etc.
