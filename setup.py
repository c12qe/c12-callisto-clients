import os

from setuptools import setup

try:
    with open("README.md") as fp:
        README = fp.read()
except FileNotFoundError:
    README = ""


# Get version from the environment variable
version = os.environ.get("SOURCE_TAG", "2.1.0")

setup()
