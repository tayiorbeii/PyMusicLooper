"""Main entry point for PyMusicLooper."""

import sys
from pymusiclooper.core.core import MusicLooper
from pymusiclooper.utils.handler import CLIHandler

def main():
    """Main entry point for the application."""
    handler = CLIHandler()
    handler.run()

if __name__ == "__main__":
    main()
