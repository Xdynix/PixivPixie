from pixiv_pixie.cli import main as cli_main
from pyinstaller_tools import build, is_packaged


def main():
    if not is_packaged():
        build(
            __file__,
            name='PixivPixieCLI',
            one_file=True,
            addition_binary=[
                ('freeimage-3.15.1-win64.dll', '')
            ],
            addition_args=[
                '-y',
                '--clean',
            ],
        )
    else:
        cli_main()


if __name__ == '__main__':
    main()
