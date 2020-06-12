"""Run pytest and open coverage report in browser."""

import webbrowser
from pathlib import Path

import pytest


def main():
    """Main function."""

    pytest.main([
        '-m', 'not webtest',
        '--cov', 'pixiv_pixie',
        '--cov-report', 'html',
    ])
    report_path = Path(__file__).parent / 'htmlcov' / 'index.html'
    webbrowser.open(report_path.as_uri())


if __name__ == '__main__':
    main()
