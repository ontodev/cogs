from setuptools import setup, find_packages
from os import path

here = path.abspath(path.dirname(__file__))

with open(here + "/README.md", "r") as fh:
    long_description = fh.read()

setup(
    name="ontodev-cogs",
    version="0.2.0",
    description="COGS Operates Google Sheets",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/ontodev/cogs",
    author="Rebecca C Jackson",
    author_email="rbca.jackson@gmail.com",
    license="",
    classifiers=[
        "Programming Language :: Python :: 3",
        "Environment :: Console",
        "Operating System :: OS Independent",
        "License :: OSI Approved :: BSD License",
    ],
    packages=find_packages(exclude="tests"),
    python_requires=">=3.6, <4",
    install_requires=[
        "daff",
        "google",
        "google-api-python-client",
        "gspread",
        "gspread-formatting",
        "requests",
        "tabulate",
        "termcolor",
    ],
    entry_points={"console_scripts": ["cogs=cogs.cli:main"]},
)
