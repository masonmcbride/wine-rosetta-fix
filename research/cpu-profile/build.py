#!/usr/bin/env python3
"""Build the MIT guest and record source/binary identity for capture preflight."""
import hashlib
import json
import pathlib
import subprocess
HERE = pathlib.Path(__file__).resolve().parent

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def main():
    command = ['x86_64-w64-mingw32-gcc', '-O2', '-g', '-Wall', '-Wextra', '-Werror',
               str(HERE/'events.c'), '-o', str(HERE/'events.exe')]
    subprocess.run(command, check=True)
    version = subprocess.run([command[0], '--version'], check=True, capture_output=True, text=True)
    (HERE/'build.json').write_text(json.dumps(dict(command=command, compiler=version.stdout,
        source_sha256=sha(HERE/'events.c'), executable_sha256=sha(HERE/'events.exe')), indent=2)+'\n')

if __name__ == '__main__':
    main()
