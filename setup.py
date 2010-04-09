#!/usr/bin/python

from distutils.core import setup

PYTHON_KILLSWITCH_VERSION='0.2'

dist = setup(name='python-killswitch',
    version=PYTHON_KILLSWITCH_VERSION,
    author='Holger Macht',
    author_email='holger@homac.de',
    maintainer='Holger Macht',
    maintainer_email='holger@homac.de',
    description='Python module providing functions for killswitches',
    long_description='Python module providing convenient function for managing killswitches',
    url='http://blog.homac.de',
    download_url='http://blog.homac.de',
    license='WTFPL',
    platforms='linux',
    py_modules = ['killswitch'],
)
