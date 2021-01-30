import os
from setuptools import setup
from distutils.cmd import Command
from bluesend import __version__


def readme():
    with open('README.md') as f:
        return f.read()

setup(
    name='bluesend',
    version=__version__,
    description = 'Send files via Bluetooth',
    long_description = readme(),
    long_description_content_type = 'text/markdown',
    keywords = 'pyqt pyqt5 bluetooth',
    url='http://github.com/ksharindam/bluesend',
    author='Arindam Chaudhuri',
    author_email='ksharindam@gmail.com',
    license='GNU GPLv3',
    packages=['bluesend'],
    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'Environment :: X11 Applications :: Qt',
        'License :: OSI Approved :: GNU General Public License v3 (GPLv3)',
        'Operating System :: POSIX :: Linux',
        'Programming Language :: Python :: 3.7',
        'Topic :: Multimedia :: Graphics',
    ],
    entry_points={
      'console_scripts': ['bluesend=bluesend.main:main'],
    },
    data_files=[
             ('share/applications', ['data/bluesend.desktop']),
             ('share/file-manager/actions', ['data/bluetooth-share.desktop'])
    ],
    include_package_data=True,
    zip_safe=False
)
