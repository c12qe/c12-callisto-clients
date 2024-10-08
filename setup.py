import os
from setuptools import setup

try:
    with open("README.md", "r") as fp:
        README = fp.read()
except FileNotFoundError:
    README = ""


# Get version from the environment variable
version = os.environ.get("SOURCE_TAG", "2.1.0")


setup(
    name="c12_callisto_clients",
    version=f"{version}",
    author="C12 Quantum Electronics",
    author_email="viktor@c12qe.com",
    description="Different clients for access to the C12 simulator",
    long_description=README,
    long_description_content_type="text/markdown",
    url="https://github.com/c12qe/c12simulator-clients",
    project_urls={
        "Homepage": "https://www.c12qe.com",
        "Source code": "https://github.com/c12qe/c12simulator-clients",
        "Issues": "https://github.com/c12qe/c12simulator-clients/issues",
        "Documentation": "https://c12qe.github.io/c12-callisto-clients/",
    },
    classifiers=[
        "Programming Language :: Python :: 3 :: Only",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Intended Audience :: Developers",
        "Intended Audience :: Science/Research",
        "Operating System :: Microsoft :: Windows",
        "Operating System :: MacOS",
        "Operating System :: POSIX :: Linux",
        "Environment :: Console",
        "Topic :: Scientific/Engineering",
    ],
    keywords="qiskit quantum c12 simulator",
    install_requires=[
        "requests~=2.32",
        "qiskit~=1.2",
        "pydantic~=2.9",
        "pytket~=1.33.0",
        "pydantic-settings~=2.5",
    ],
    python_requires=">=3.7",
    include_package_data=False,
    package_dir={"c12_callisto_clients": "src/c12_callisto_clients"},
    packages=[
        "c12_callisto_clients.api",
        "c12_callisto_clients.qiskit_back",
        "c12_callisto_clients.qiskit",
        "c12_callisto_clients.pytket",
        "c12_callisto_clients.pytket.extensions",
        "c12_callisto_clients.pytket.extensions.callisto",
        "c12_callisto_clients.pytket.extensions.callisto.backends",
        "c12_callisto_clients",
    ],
    license="MIT",
    options={"bdist_wheel": {"universal": True}},
)
