from setuptools import setup, find_packages

setup(
    name='sparnord',
    version='0.2',
    description='SparNord home banking screen scraper',
    author='Soren Hansen',
    author_email='soren@linux2go.dk',
    url='http://github.com/sorenh/python-sparnord',
    packages=find_packages(),
    include_package_data=True,
    license='Apache 2.0',
    keywords='selenium screenscraping sparnord',
    install_requires=[
        'selenium',
        'pyrex',
        'xtest'
    ],
)
