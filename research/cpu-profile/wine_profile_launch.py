"""Pass a preload across macOS's protected shell, preserving the original wrapper."""
from pathlib import Path


def wrapper_command(wrapper: Path, library: Path, *arguments: str):
    # A protected /bin/bash removes DYLD_* inherited through its environment.
    # Set it after interpreter startup, then source (do not re-exec) the wrapper.
    # Its $0 and positional arguments retain their normal script meanings.
    return ['/bin/bash', '-c', 'export DYLD_INSERT_LIBRARIES="$1"\nshift\nsource "$0" "$@"',
            str(wrapper), str(library), *arguments]
