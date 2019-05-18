import setuptools

with open('README.md', 'rt', encoding='utf-8') as f:
    long_description = f.read()

with open('requirements.txt', 'rt', encoding='utf-8') as f:
    install_requires = [line.strip() for line in f]

setuptools.setup(
    name='PixivPixie',
    version='0.1.2',
    description='User-friendly Pixiv API based on PixivPy',
    long_description=long_description,
    long_description_content_type='text/markdown',
    url='https://github.com/Xdynix/PixivPixie',
    author='Xdynix',
    author_email='Lizard.rar@gmail.com',
    classifiers=[
        'Development Status :: 3 - Alpha',
        'License :: OSI Approved :: Apache Software License',
        'Operating System :: OS Independent',
        'Programming Language :: Python :: 3',
    ],
    keywords=['pixiv', 'api', 'pixivpy', 'pixiv_pixie'],
    platforms=['any'],
    license='Apache 2.0',
    packages=['pixiv_pixie'],
    install_requires=install_requires,
    python_requires='>=3.4',
)
