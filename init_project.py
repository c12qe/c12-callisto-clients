import re
import os
from typing import Optional, Dict
import re
import subprocess

PYPROJECT_TOML_PATH = "./pyproject.toml"
CI_WORKFLOW_PATH = "./.github/workflows/ci.yml"
CONDA_ENV_PATH = "./environment.yml"


def get_black_python_version(py_version: str):
    # Currently supported black python versions (8/2/2023):
    # 'py33', 'py34', 'py35', 'py36', 'py37', 'py38', 'py39', 'py310', 'py311'

    supported_versions = ['py33', 'py34', 'py35', 'py36', 'py37', 'py38', 'py39', 'py310', 'py311']

    python_version_regex = "^([2-3])(\.([0-9]{1,2})+)?(.([0-9]{1,2})+)?$"
    matcher = re.match(python_version_regex, py_version)
    black_python_version = f"py{matcher.group(1)}{matcher.group(3)}"

    if black_python_version not in supported_versions:
        raise ValueError(f'Chosen python error not supported by black. Supported versions are {supported_versions}')

    return black_python_version


def ask(question: str, pattern: Optional[str] = None, pattern_hint: Optional[str] = None) -> str:
    regex = re.compile(pattern) if pattern is not None else None
    while True:
        answer = input(question)
        if pattern is None:
            return answer
        regex_match = regex.match(answer)
        if bool(regex_match) is True:
            return answer
        if pattern_hint is not None:
            print(pattern_hint)


def replace_in_file(file_path: str, replacement_dict: Dict[str, str]):
    # Read in the file
    with open(file_path, "r") as file:
        data = file.read()

    # Replace the target string
    for k, v in replacement_dict.items():
        data = data.replace(k, v)

    # Write the file out again
    with open(file_path, "w") as file:
        file.write(data)


project_name = ask("What is your project name ?", "^[a-z][a-z0-9-]{2,}$", "minimum 3 characters ([a-z][a-z0-9-]{2,}")
author = ask("What is the author name ?")
python_version = ask(
    "What python version will you use ?",
    "^([2-3])(\.([0-9]{1,2})+)?(.([0-9]{1,2})+)?$",
    "Valid version examples: '3', '3.1', '3.8.12'",
)


replace_in_file(
    PYPROJECT_TOML_PATH,
    {
        "{{PROJECT_NAME}}": project_name,
        "{{PYTHON_VERSION}}": python_version,
        "{{AUTHOR_NAME}}": author if author is not None else "c12dev",
        "{{BLACK_PYTHON_VERSION}}": get_black_python_version(python_version)
    },
)

replace_in_file(
    CI_WORKFLOW_PATH,
    {
        "{{PYTHON_VERSION}}": python_version,
    },
)

replace_in_file(
    CONDA_ENV_PATH,
    {
        "{{PROJECT_NAME}}": project_name,
        "{{PYTHON_VERSION}}": python_version,
    },
)

dir_path = os.path.dirname(os.path.realpath(__file__))

subprocess.run(
    ["git", "add", PYPROJECT_TOML_PATH, CI_WORKFLOW_PATH, CONDA_ENV_PATH],
    check=True
)
subprocess.run(
    ["git", "commit", "-m", "'setup variables for project'"],
    check=True
)
