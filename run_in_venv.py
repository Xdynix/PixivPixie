#!/usr/bin/env python3
"""Activate virtualenv before executing command."""

import os
import subprocess
import sys
from pathlib import Path

VIRTUALENV_DIR = os.environ.get('VIRTUAL_ENV') or 'venv'


def main():
    """Main function."""

    activate_this = Path(__file__).parent / VIRTUALENV_DIR / ('Scripts' if os.name == 'nt' else 'bin') / 'activate_this.py'
    activate_this = activate_this.absolute()
    with activate_this.open('rt', encoding='utf-8') as f:
        exec(f.read(), {'__file__': str(activate_this)})  # pylint: disable=exec-used
    try:
        subprocess.run(sys.argv[1:], check=True)
    except subprocess.CalledProcessError as error:
        sys.exit(error.returncode)


if __name__ == '__main__':
    main()
