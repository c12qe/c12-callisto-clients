from setuptools import setup

with open("README.MD", "r") as fp:
    README = fp.read()


setup(
    name="c12simulator_clients",
    version="0.0.22",
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
        "Documentation": "https://github.com/c12qe/c12simulator-clients/tree/master/docs",
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
    install_requires=["requests~=2.28", "qiskit~=0.41", "pydantic~=1.10"],
    python_requires=">=3.7",
    include_package_data=False,
    package_dir={"c12simulator_clients": "src/c12simulator_clients"},
    packages=[
        "c12simulator_clients.api",
        "c12simulator_clients.qiskit_back",
        "c12simulator_clients",
    ],
    license="MIT",
    options={"bdist_wheel": {"universal": True}},
)
