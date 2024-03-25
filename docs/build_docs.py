import os
import yaml
import subprocess


def build_doc(version, language, tag):
    os.environ["current_version"] = version
    os.environ["current_language"] = language

    subprocess.run(f"git checkout {tag}", shell=True)
    subprocess.run("git checkout docs -- conf.py", shell=True)
    subprocess.run("git checkout docs -- versions.yaml", shell=True)
    subprocess.run("make html", shell=True)


def move_dir(src, dst):
    subprocess.run(["mkdir", "-p", dst])
    subprocess.run("mv " + src + "* " + dst, shell=True)


os.environ["pages_root"] = "https://c12qe.github.io/c12-callisto-clients/"


build_doc("latest", "en", "master")
move_dir("./_build/html/", "../pages/")


with open("./versions.yaml", "r") as yaml_file:
    docs = yaml.safe_load(yaml_file)

if docs.items() is not None:
    for version, details in docs.items():
        tag = details.get("tag", "")
        for language in details.get("languages", []):
            build_doc(version, language, version)
            move_dir("./_build/html/", "../pages/" + version + "/" + language + "/")
