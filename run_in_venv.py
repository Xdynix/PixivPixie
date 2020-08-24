"""Activate virtualenv before executing command."""

import os
import subprocess
import sys
from pathlib import Path

VIRTUALENV_DIR = 'venv'


def main():
    """Main function."""

    activate_this = Path(__file__).parent / VIRTUALENV_DIR / ('Scripts' if os.name == 'nt' else 'bin') / 'activate_this.py'
    activate_this = activate_this.absolute()
    with activate_this.open('rt', encoding='utf-8') as f:
        exec(f.read(), {'__file__': str(activate_this)})  # pylint: disable=exec-used
    subprocess.run(sys.argv[1:], check=True)


if __name__ == '__main__':
    main()
