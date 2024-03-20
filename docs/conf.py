import os
import yaml
import sys


default_path = os.path.dirname(__file__)
sys.path.insert(0, os.path.abspath(default_path + "/../src"))


# We get the version and language from the environment variables
current_language = os.environ.get("current_language")
current_version = os.environ.get("current_version")


# Main project configurations
project = "CALLISTO"
copyright = "2024, C12 Quantum Electronics"
author = "C12 Quantum Electronics"
release = f"{current_version}"


extensions = ["sphinx.ext.autodoc", "myst_parser", "nbsphinx"]
templates_path = ["_templates"]
exclude_patterns = ["_build", "Thumbs.db", ".DS_Store"]


# HTML theme options
html_theme = "furo"
html_static_path = ["_static"]
html_favicon = "_static/favicon.png"
html_theme_options = {
    f"announcement": f"We're pleased to announce that <bold>CALLISTO {current_version}</bold> is now released!",
    "light_css_variables": {
        "color-brand-primary": "#3A3938",
        "color-brand-content": "#D6A018",
        "color-brand-visited": "#A09D98",
        "font-stack": "Formular, Cardone Micro Trial, Inconsolata, monospace",
        "font-stack--monospace": "Fira Code, Courier, monospace",
    },
    "dark_css_variables": {
        "color-brand-primary": "#C6E5E1",
        "color-brand-content": "#D6A018",
        "color-brand-visited": "#A09D98",
        "font-stack": "Formular, Cardone Micro Trial, Inconsolata, monospace",
        "font-stack--monospace": "Fira Code, Courier, monospace",
    },
    "light_logo": "logo_black.svg",
    "dark_logo": "logo_white.svg",
}

html_css_files = [
    "css/custom.css",
]


# Versioning part

html_context = {
    "current_language": current_language,
    "languages": [],
    "current_version": current_version,
    "versions": [],
}
pages_root = os.environ.get("pages_root", "")


if current_version == "latest":
    html_context["languages"].append(["en", pages_root])

if current_language == "en":
    html_context["versions"].append(["latest", pages_root])

# and loop over all other versions from our yaml file
# to set versions and languages
with open("versions.yaml", "r") as yaml_file:
    docs = yaml.safe_load(yaml_file)

if current_version != "latest":
    for language in docs[current_version].get("languages", []):
        html_context["languages"].append(
            [language, pages_root + "/" + current_version + "/" + language]
        )

for version, details in docs.items():
    html_context["versions"].append([version, pages_root + "/" + version + "/" + current_language])
