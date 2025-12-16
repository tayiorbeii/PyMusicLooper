import functools
import logging
import os
import tempfile
import warnings

import rich_click as click
from rich.logging import RichHandler
from rich.progress import Progress, SpinnerColumn, TimeElapsedColumn
from rich.traceback import install as rich_traceback_handler
from rich_click.patch import patch as rich_click_patch
from yt_dlp.utils import YoutubeDLError

rich_click_patch()
from click_option_group import RequiredMutuallyExclusiveOptionGroup, optgroup
from click_params import URL as UrlParamType

from pymusiclooper import __version__
from pymusiclooper.cli_config import CliConfig
from pymusiclooper.console import _COMMAND_GROUPS, _OPTION_GROUPS, rich_console
from pymusiclooper.core import MusicLooper
from pymusiclooper.exceptions import AudioLoadError, LoopNotFoundError
from pymusiclooper.handler import BatchHandler, LoopExportHandler, LoopHandler
from pymusiclooper.utils import download_audio, get_outputdir, mk_outputdir

# CLI --help styling
click.rich_click.OPTION_GROUPS = _OPTION_GROUPS
click.rich_click.COMMAND_GROUPS = _COMMAND_GROUPS
click.rich_click.USE_RICH_MARKUP = True
# End CLI styling


@click.group("pymusiclooper", epilog="Full documentation and examples can be found at https://github.com/arkrow/PyMusicLooper")
@click.option("--debug", "-d", is_flag=True, default=False, help="Enables debugging mode.")
@click.option("--verbose", "-v", is_flag=True, default=False, help="Enables verbose logging output.")
@click.option("--interactive", "-i", is_flag=True, default=False, help="Enables interactive mode to manually preview/choose the desired loop point.")
@click.option("--samples", "-s", is_flag=True, default=False, help="Display all the loop points shown in interactive mode in sample points instead of the default mm:ss.sss format.")
@click.version_option(__version__, prog_name="pymusiclooper", message="%(prog)s %(version)s")
@click.pass_context
def cli_main(ctx, debug, verbose, interactive, samples):
    """A program for repeating music seamlessly and endlessly, by automatically finding the best loop points."""
    # Create config object and store in Click context
    config = CliConfig(
        debug=debug,
        verbose=verbose,
        interactive_mode=interactive,
        display_samples=samples,
    )
    ctx.obj = config

    if debug:
        warnings.simplefilter("default")
        rich_traceback_handler(console=rich_console, suppress=[click])
    else:
        warnings.filterwarnings("ignore")

    if verbose:
        logging.basicConfig(format="%(message)s", level=logging.INFO, handlers=[RichHandler(level=logging.INFO, console=rich_console, rich_tracebacks=True, show_path=debug, show_time=False, tracebacks_suppress=[click])])
    else:
        logging.basicConfig(format="%(message)s", level=logging.ERROR, handlers=[RichHandler(level=logging.ERROR, console=rich_console, show_time=False, show_path=False)])


def common_path_options(f):
    @optgroup.group("audio path", cls=RequiredMutuallyExclusiveOptionGroup, help="the path to the audio track(s) to load")
    @optgroup.option("--path", type=click.Path(exists=True), default=None, help=r"Path to the audio file(s). [dim cyan]\[mutually exclusive with --url][/] [dim red]\[at least one required][/]")
    @optgroup.option("--url",type=UrlParamType, default=None, help=r"Link to the youtube video (or any stream supported by yt-dlp) to extract audio from and use. [dim cyan]\[mutually exclusive with --path][/] [dim red]\[at least one required][/]")

    @functools.wraps(f)
    def wrapper_common_options(*args, **kwargs):
        return f(*args, **kwargs)

    return wrapper_common_options


def common_loop_options(f):
    @click.option('--min-duration-multiplier', type=click.FloatRange(min=0.0, max=1.0, min_open=True, max_open=True), default=0.35, show_default=True, help="The minimum loop duration as a multiplier of the audio track's total duration.")
    @click.option('--min-loop-duration', type=click.FloatRange(min=0, min_open=True), default=None, help='The minimum loop duration in seconds. [dim](overrides --min-duration-multiplier if set)[/]')
    @click.option('--max-loop-duration', type=click.FloatRange(min=0, min_open=True), default=None, help='The maximum loop duration in seconds.')
    @click.option('--approx-loop-position', type=click.FloatRange(min=0), nargs=2, default=None, help='The approximate desired loop start and loop end in seconds. [dim]([cyan]+/-2[/] second search window for each point)[/]')
    @click.option("--brute-force", is_flag=True, default=False, help=r"Check the entire audio track instead of just the detected beats. [dim yellow](Warning: may take several minutes to complete.)[/]")
    @click.option("--disable-pruning", is_flag=True, default=False, help="Disables filtering of the detected loop points from the initial pass.")

    @functools.wraps(f)
    def wrapper_common_options(*args, **kwargs):
        return f(*args, **kwargs)

    return wrapper_common_options


def common_export_options(f):
    @click.option('--output-dir', '-o', type=click.Path(exists=False, writable=True, file_okay=False), help="The output directory to use for the exported files.")
    @click.option("--recursive", "-r", is_flag=True, default=False, help="Process directories recursively.")
    @click.option("--flatten", "-f", is_flag=True, default=False, help="Flatten the output directory structure instead of preserving it when using the --recursive flag. [dim yellow](Note: files with identical filenames are silently overwritten.)[/]")
    @functools.wraps(f)
    def wrapper_common_options(*args, **kwargs):
        return f(*args, **kwargs)

    return wrapper_common_options


@cli_main.command()
@common_path_options
@common_loop_options
@click.pass_obj
def play(config, **kwargs):
    """Play an audio file on repeat from the terminal with the best discovered loop points, or a chosen point if interactive mode is active."""
    try:
        if kwargs.get("url", None) is not None:
            kwargs["path"] = download_audio(kwargs["url"], tempfile.gettempdir(), verbose=config.verbose)

        with Progress(
            SpinnerColumn(),
            *Progress.get_default_columns(),
            TimeElapsedColumn(),
            console=rich_console,
            transient=True
        ) as progress:
            progress.add_task("Processing", total=None)
            handler = LoopHandler(config=config, **kwargs)

        chosen_loop_pair = handler.choose_loop_pair(interactive_mode=config.interactive_mode)

        start_time = handler.format_time(chosen_loop_pair.loop_start, in_samples=config.display_samples)
        end_time = handler.format_time(chosen_loop_pair.loop_end, in_samples=config.display_samples)

        rich_console.print(
            "\nPlaying with looping active from [green]{}[/] back to [green]{}[/]; similarity: {:.2%}".format(
                end_time,
                start_time,
                chosen_loop_pair.score,
            )
        )
        rich_console.print("(Press [red]Ctrl+C[/] to stop looping.)")

        handler.play_looping(chosen_loop_pair.loop_start, chosen_loop_pair.loop_end)

    except YoutubeDLError:
        # Already logged from youtube.py
        pass
    except (AudioLoadError, LoopNotFoundError, Exception) as e:
        print_exception(e, config.debug)


@cli_main.command()
@click.option('--path', type=click.Path(exists=True), required=True, help='Path to the audio file.')
@click.option("--tag-names", type=str, required=False, nargs=2, help="Name of the loop metadata tags to read from, e.g. --tag-names LOOP_START LOOP_END  (note: values must be integers and in sample units). Default: auto-detected.")
@click.option("--tag-offset/--no-tag-offset", is_flag=True, default=None, help="Always parse second loop metadata tag as a relative length / or as an absolute length. Default: auto-detected based on tag name.")
@click.pass_obj
def play_tagged(config, path, tag_names, tag_offset):
    """Skips loop analysis and reads the loop points directly from the tags present in the file."""
    try:
        if tag_names is None:
            tag_names = [None, None]

        looper = MusicLooper(path)
        loop_start, loop_end = looper.read_tags(tag_names[0], tag_names[1], tag_offset)

        start_time = (
            loop_start
            if config.display_samples
            else looper.samples_to_ftime(loop_start)
        )
        end_time = (
            loop_end
            if config.display_samples
            else looper.samples_to_ftime(loop_end)
        )

        rich_console.print(f"\nPlaying with looping active from [green]{end_time}[/] back to [green]{start_time}[/]")
        rich_console.print("(Press [red]Ctrl+C[/] to stop looping.)")

        looper.play_looping(loop_start, loop_end)

    except Exception as e:
        print_exception(e, config.debug)


@cli_main.command()
@common_path_options
@common_loop_options
@common_export_options
@click.option('--format', type=click.Choice(("WAV", "FLAC", "OGG", "MP3"), case_sensitive=False), default="WAV", show_default=True, help="Audio format to use for the exported split audio files.")
@click.pass_obj
def split_audio(config, **kwargs):
    """Split the input audio into intro, loop and outro sections."""
    kwargs["split_audio"] = True
    run_handler(config, **kwargs)

@cli_main.command()
@common_path_options
@common_loop_options
@common_export_options
@click.option('--format', type=click.Choice(("WAV", "FLAC", "OGG", "MP3"), case_sensitive=False), default="MP3", show_default=True, help="Audio format to use for the output audio file.")
@click.option('--extended-length', type=float, required=True, help="Desired length of the extended looped track in seconds. [Must be longer than the audio's original length.]")
@click.option('--fade-length', type=float, default=5, show_default=True, help="Desired length of the loop fade out in seconds.")
@click.option('--disable-fade-out', is_flag=True, default=False, help="Extend the track with all its sections (intro/loop/outro) without fading out. --extended-length will be treated as an 'at least' constraint.")
@click.pass_obj
def extend(config, **kwargs):
    """Create an extended version of the input audio by looping it to a specific length."""
    run_handler(config, **kwargs)


@cli_main.command()
@common_path_options
@common_loop_options
@common_export_options
@click.option("--export-to", type=click.Choice(("STDOUT", "TXT"), case_sensitive=False), default="STDOUT", show_default=True, help="STDOUT: print the loop points of a track in samples to the terminal; TXT: export the loop points of a track in samples and append to a loop.txt file.")
@click.option("--fmt", type=click.Choice(("SAMPLES", "SECONDS", "TIME"), case_sensitive=False), default="SAMPLES", show_default=True, help="Export loop points formatted as samples (default), seconds, or time (mm:ss.sss).")
@click.option("--alt-export-top", type=int, default=0, help="Alternative export format of the top N loop points instead of the best detected/chosen point. --alt-export-top -1 to export all points.")
@click.pass_obj
def export_points(config, **kwargs):
    """Export the best discovered or chosen loop points to a text file or to the terminal."""
    kwargs["to_stdout"] = kwargs["export_to"].upper() == "STDOUT"
    kwargs["to_txt"] = kwargs["export_to"].upper() == "TXT"
    kwargs.pop("export_to", "")

    run_handler(config, **kwargs)


@cli_main.command()
@common_path_options
@common_loop_options
@common_export_options
@click.option('--tag-names', type=str, required=True, nargs=2, help='Name of the loop metadata tags to use, e.g. --tag-names LOOP_START LOOP_END')
@click.option("--tag-offset/--no-tag-offset", is_flag=True, default=None, help="Always export second loop metadata tag as a relative length / or as an absolute length. Default: auto-detected based on tag name.")
@click.pass_obj
def tag(config, **kwargs):
    """Adds metadata tags of loop points to a copy of the input audio file(s)."""
    run_handler(config, **kwargs)


@cli_main.command()
@common_path_options
@common_export_options
@click.option('--target-duration', type=float, required=True, help='Target duration of the remixed song in seconds.')
@click.option('--format', type=click.Choice(("WAV", "FLAC", "OGG", "MP3"), case_sensitive=False), default="MP3", show_default=True, help="Audio format to use for the remixed audio file.")
@click.option('--similarity-threshold', type=click.FloatRange(0.0, 1.0), default=0.7, show_default=True, help='Minimum similarity score for sections to be considered similar (0.0-1.0).')
@click.option('--jump-probability', type=click.FloatRange(0.0, 1.0), default=0.3, show_default=True, help='Probability of jumping to a similar section vs. continuing sequentially (0.0-1.0).')
@click.option('--max-connections', type=int, default=10, show_default=True, help='Maximum number of connections per section.')
@click.option('--min-section-duration', type=float, default=2.0, show_default=True, help='Minimum duration of each section in seconds.')
@click.option('--max-section-duration', type=float, default=8.0, show_default=True, help='Maximum duration of each section in seconds.')
@click.option('--prefer-similar', is_flag=True, default=True, help='Prefer jumping to more similar sections when making connections.')
@click.option('--seed', type=int, default=None, help='Random seed for reproducible results.')
@click.option('--fade-duration', type=click.FloatRange(min=0.0), default=0.1, show_default=True, help='Duration of crossfade between sections in seconds.')
@click.option('--suggest-ranges', is_flag=True, default=False, help='Display recommended parameter ranges and exit.')
@click.pass_obj
def jukebox(config, **kwargs):
    """Create an Infinite Jukebox-style remix by rearranging similar sections of the song."""
    # If user only wants the suggested ranges, show them and exit early.
    if kwargs.pop("suggest_ranges", False):
        rich_console.print("[bold cyan]Recommended Parameter Ranges[/]")
        rich_console.print("• min-section-duration: 0.25 – 2.0 s (smaller enables more, shorter sections)")
        rich_console.print("• max-section-duration: 4 – 12 s (upper bound for section length)")
        rich_console.print("• similarity-threshold: 0.40 – 0.80 (lower = more connections, higher = stricter)")
        rich_console.print("• jump-probability: 0.20 – 0.50 (chance of jumping vs. sequential play)")
        rich_console.print("• max-connections: 5 – 20 (connections kept per section)")
        rich_console.print("• fade-duration: 0.05 – 0.50 s (cross-fade length between sections)")
        rich_console.print("\nTune these depending on song tempo/structure; shorter sections and lower similarity make a more chaotic remix, higher values create fewer, longer jumps.")
        return

    try:
        if kwargs.get("url", None) is not None:
            kwargs["output_dir"] = mk_outputdir(os.getcwd(), kwargs["output_dir"])
            kwargs["path"] = download_audio(kwargs["url"], kwargs["output_dir"], verbose=config.verbose)
        else:
            kwargs["output_dir"] = mk_outputdir(kwargs["path"], kwargs["output_dir"])

        if os.path.isfile(kwargs["path"]):
            with Progress(
                SpinnerColumn(),
                *Progress.get_default_columns(),
                TimeElapsedColumn(),
                console=rich_console,
                transient=True
            ) as progress:
                progress.add_task("Analyzing song structure...", total=None)
                jukebox_handler = JukeboxHandler(config=config, **kwargs)
            jukebox_handler.run()
        else:
            rich_console.print(f"[red]Error: File not found: {kwargs['path']}[/]")
    except (AudioLoadError, LoopNotFoundError, Exception) as e:
        print_exception(e, config.debug)


def run_handler(config, **kwargs):
    try:
        if kwargs.get("url", None) is not None:
            kwargs["output_dir"] = mk_outputdir(os.getcwd(), kwargs["output_dir"])
            kwargs["path"] = download_audio(kwargs["url"], kwargs["output_dir"], verbose=config.verbose)
        else:
            kwargs["output_dir"] = mk_outputdir(kwargs["path"], kwargs["output_dir"])

        if os.path.isfile(kwargs["path"]):
            with Progress(
                SpinnerColumn(),
                *Progress.get_default_columns(),
                TimeElapsedColumn(),
                console=rich_console,
                transient=True
            ) as progress:
                progress.add_task("Processing", total=None)
                export_handler = LoopExportHandler(config=config, **kwargs)
            export_handler.run()
        else:
            batch_handler = BatchHandler(config=config, **kwargs)
            batch_handler.run()
    except YoutubeDLError:
        # Already logged from youtube.py
        pass
    except (AudioLoadError, LoopNotFoundError, Exception) as e:
        print_exception(e, config.debug)

def print_exception(e: Exception, debug: bool = False):
    if debug:
        rich_console.print_exception(suppress=[click])
    else:
        logging.error(e)

if __name__ == "__main__":
    cli_main()
