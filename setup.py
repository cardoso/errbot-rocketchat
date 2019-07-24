# coding: utf-8
"""
Setup module.
"""
from __future__ import absolute_import

# Standard imports
#
from glob import glob
import os

# External imports
from setuptools import find_packages
from setuptools import setup
import setuptools.command.build_py
import setuptools.command.sdist


# ----- Patch setuptools `sdist` command to include custom files -----
# Store original `add_defaults` function
_orig_add_defaults = setuptools.command.sdist.sdist.add_defaults


# Create custom `add_defaults` function
def add_defaults(self):
    """
    Add default file paths for the source distribution.

    :return: None.
    """
    # Delegate to original `add_defaults` function
    _orig_add_defaults(self)

    # Add `.plug` files.
    #
    # Notice `glob` does not support `**` for matching multiple levels of
    # directories.
    #
    # For each `.plug` file path
    for path in glob('src/*/*/*.plug'):
        # Add to list
        self.filelist.append(path)

    # Add `.gitignore` files.
    #
    # For each `.gitignore` file path
    for path in glob('src/*/*/.gitignore'):
        # Add to list
        self.filelist.append(path)


# Replace original `add_defaults` function
setuptools.command.sdist.sdist.add_defaults = add_defaults
# ===== Patch setuptools `sdist` command to include custom files =====


# ----- Patch setuptools `bdist_*` commands to include custom files -----
# Create custom `find_data_files` function
def find_data_files(self, package, src_dir):
    """
    Find data file paths in given package.

    :param package: Package name.

    :param src_dir: Package directory path.

    :return: Accepted data file path list.
    """
    # Accepted data file path list
    accepted_file_path_s = []

    # For each file in the package directory
    for file_bare_name in os.listdir(src_dir):
        # Get file path
        file_path = os.path.join(src_dir, file_bare_name)

        # If the file is regular file
        if os.path.isfile(file_path):
            # Get filename extension
            _, filename_ext = os.path.splitext(file_bare_name)

            # If the filename is `.gitignore`,
            # or the filename extension is one of these.
            if file_bare_name == '.gitignore' \
                    or filename_ext in ['.py', '.plug']:
                # Accept the file path
                accepted_file_path_s.append(file_path)

    # Return accepted data file path list
    return accepted_file_path_s


# Replace original `find_data_files` function.
setuptools.command.build_py.build_py.find_data_files = find_data_files
# ===== Patch setuptools `bdist_*` commands to include custom files =====


# Run setup
setup(
    name='RocketChat',

    version='0.1.0',

    description=(
        'Rocket.Chat backend for Errbot.'
    ),

    long_description="""`Documentation on Github
<https://github.com/AoiKuiyuyou/AoikRocketChatErrbot>`_""",

    url='https://github.com/AoiKuiyuyou/AoikRocketChatErrbot',

    author='Aoi.Kuiyuyou',

    author_email='aoi.kuiyuyou@google.com',

    license='MIT',

    classifiers=[
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.5',
    ],

    keywords='errbot rocket.chat',

    package_dir={
        '': 'src'
    },

    packages=find_packages('src'),

    include_package_data=True,

    install_requires=[
        'python-meteor >= 0.1.6',
        'errbot >= 4.3.4',
    ],
)
