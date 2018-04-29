import os
import subprocess
import sys

from pixiv_pixie.cli import main as cli_main, NAME

BINARY_PATH = 'lib'
DATA_PATH = 'data'


def is_packaged():
    # Return true if executing from packaged file
    return hasattr(sys, 'frozen')


def get_path(path, package_prefix=DATA_PATH):
    if os.path.isabs(path) or not is_packaged():
        return path
    else:
        return os.path.join(
            sys.prefix,
            os.path.join(package_prefix, path)
        )


def build(
        script, name=None, one_file=False, no_console=False, icon=None,
        binary_path=BINARY_PATH, addition_binary=None,
        data_path=DATA_PATH, addition_data=None,
        hidden_import=None,
        distpath=None, workpath=None, specpath=None,
        addition_args=None,
):
    args = []

    if name is not None:
        args.extend(('-n', name))
    if one_file:
        args.append('-F')
    if no_console:
        args.append('-w')
    if icon is not None:
        args.extend(('-i', icon))
    if addition_args is None:
        addition_args = []

    def add_resource(add_type, path, resources):
        for resource in resources:
            args.append('--add-{}'.format(add_type))
            if isinstance(resource, tuple) or isinstance(resource, list):
                src = resource[0]
                dest = resource[1]
                args.append(src + os.path.pathsep + os.path.join(path, dest))
            else:
                args.append(
                    resource + os.path.pathsep + os.path.join(path, resource),
                )

    if addition_binary is not None:
        add_resource(
            add_type='binary',
            path=binary_path,
            resources=addition_binary,
        )
    if addition_data is not None:
        add_resource(
            add_type='data',
            path=data_path,
            resources=addition_data,
        )

    if hidden_import is not None:
        for m in hidden_import:
            args.extend(('--hidden-import', m))

    if distpath is not None:
        args.extend(('--distpath', distpath))
    if workpath is not None:
        args.extend(('--workpath', workpath))
    if specpath is not None:
        args.extend(('--specpath', specpath))

    subprocess.call(['pyinstaller'] + args + addition_args + [script])


def main():
    if not is_packaged():
        build(
            __file__,
            name=NAME,
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
