"""CLI configuration object for Click context.

This module provides a Config dataclass to hold CLI flags and options,
eliminating the need for os.environ side effects and enabling explicit
dependency injection into handlers.
"""

from dataclasses import dataclass


@dataclass
class CliConfig:
    """Holds CLI-level configuration flags.
    
    Attributes:
        debug: Enable debug mode (full tracebacks).
        verbose: Enable verbose logging output.
        interactive_mode: Enable interactive mode for loop point selection.
        display_samples: Display times in sample units instead of mm:ss.sss.
    """
    debug: bool = False
    verbose: bool = False
    interactive_mode: bool = False
    display_samples: bool = False
