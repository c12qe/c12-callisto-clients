# template for new python project

## Usage

1) On github click on the "Use this template" button  
2) Choose the repository name
3) Clone the repository on you local computer
4) Run `python init_project.py` This will ask you a few questions to init the templates.
5) Create the conda environment with `conda env create -f environment.yml`
6) Activate the conda environment with `conda activate {name you gave to the project in 4)}`
7) Install the dependencies with `poetry install`
8) You are good to go

## What's in it

### directory structure

src = source files. Your code goes here.  
tests = test files. Your tests go here (try to replicate your src structure).  


### conda for the python environment
We use [conda](https://docs.conda.io/en/latest/miniconda.html) to create independent virtual environment with the right python version.  
When you do `conda env create -f environment.yml` this will create a virtual environment  
named after the name in [environment.yml](./environment.yml) with the python version defined in [environment.yml](./environment.yml)  
Once the environment is created you need to activate it by doing a  `conda activate {name you gave to the project in 4)}`

### poetry for package management
We use [poetry](https://python-poetry.org/) to manage package dependencies.
Your dependencies are defined in [pyproject.toml](./pyproject.toml) under the [tool.poetry.dependencies] section  
To add a new dependency to the project use `poetry add {package_name}={package_version}`.  
This will add the dependency to the [pyproject.toml](./pyproject.toml) and to the [poetry.lock](./poetry.lock) files.  
The [poetry.lock](./poetry.lock) contains all the dependencies (recursively) of your project, with their version pinned.  
This way when the next person `poetry install` it will be able to reproduce the exact same environment.

### black for formatting
[black](https://github.com/psf/black) is a python code formatter.  
It allows to have consistent code formatting accross the project (easier to read, compare, etc).  
It is enforced by a github action check.  
It is **highly recommended** that you [configure your IDE](https://black.readthedocs.io/en/stable/integrations/editors.html) to apply black after you save a file.  
You can run it manually by doing `black src`.  

### pylint for linting
[pylint](https://pylint.pycqa.org/en/latest/) is a python linter.
It analyse the code and enforce best practices.  
It is enforced by a github action check.  
You can run it manually by doing `pylint src`.  

### pytest for testing
[pytest](https://docs.pytest.org/en/7.1.x/)
Allows you to run tests suites.  
It is enforced by a github action check.  
You can run it manually by doing `pytest`.  
