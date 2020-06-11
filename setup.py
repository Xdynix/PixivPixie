"""Build script for PyPI."""

from pathlib import Path

import setuptools

import pixiv_pixie

HERE = Path(__file__).parent

with (HERE / 'README.md').open('rt', encoding='utf-8') as f:
    LONG_DESCRIPTION = f.read()

with (HERE / 'requirements.txt').open('rt', encoding='utf-8') as f:
    INSTALL_REQUIRES = [line.strip() for line in f]

setuptools.setup(
    name='PixivPixie',
    version=pixiv_pixie.__version__,
    description='User-friendly Pixiv API based on PixivPy',
    long_description=LONG_DESCRIPTION,
    long_description_content_type='text/markdown',
    author='Xdynix',
    author_email='Lizard.rar@gmail.com',
    url='https://github.com/Xdynix/PixivPixie',
    packages=['pixiv_pixie'],
    scripts=[],
    classifiers=[
        'Development Status :: 3 - Alpha',
        'License :: OSI Approved :: Apache Software License',
        'Operating System :: OS Independent',
        'Programming Language :: Python :: 3',
        'Topic :: Utilities',
    ],
    license='Apache 2.0',
    keywords=['pixiv', 'api', 'pixivpy', 'pixiv_pixie'],
    platforms=['any'],
    python_requires='>=3.6',
    install_requires=INSTALL_REQUIRES,
)
