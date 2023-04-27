from setuptools import setup, find_packages
from pathlib import Path

with open(Path(__file__).resolve().parent / 'requirements.txt') as fin:
    requirements = fin.readlines()

authors = [
    "Maxim Talimanchuk <mtalimanchuk@gmail.com>",
    "Dilyara Baymurzina <dilyara.rimovna@gmail.com>",
    "Denis Kuznetsov <kuznetsov.den.p@gmail.com>",
]

setup(
    name="deeppavlov-dreamtools",
    author=", ".join(authors),
    version="0.0.1",
    packages=find_packages(),
    include_package_data=True,
    install_requires=requirements,
    entry_points={
        "console_scripts": [
            "dreamtools = deeppavlov_dreamtools.cmd:cli",
        ],
    },
)
