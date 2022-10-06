from setuptools import setup, find_packages

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
    install_requires=[
        "pydantic==1.9.0",
        "Click==8.0.3",
        "PyYAML==5.3b1",
    ],
    entry_points={
        "console_scripts": [
            "dreamtools = deeppavlov_dreamtools.cmd:cli",
        ],
    },
)
