"""Activate virtualenv before executing command."""

import os
import subprocess
import sys
from pathlib import Path

VIRTUALENV = 'venv'


def main():
    """Main function."""

    activate_this = Path(__file__).parent / VIRTUALENV / ('Scripts' if os.name == 'nt' else 'bin') / 'activate_this.py'
    activate_this = activate_this.absolute()
    with activate_this.open('rt', encoding='utf-8') as f:
        exec(f.read(), {'__file__': str(activate_this)})
    subprocess.run(sys.argv[1:])


if __name__ == '__main__':
    main()
