#!/usr/bin/env python
# -*- coding:utf-8 -*-

import sys
from setuptools import setup, find_packages
PY3 = sys.version_info.major == 3

requirements = ["requests>=2.3.0",
                "paramiko>=1.15.2",
                "pexpect>=3.3",
                "ujson>=1.33",
                "xmltodict>=0.9.2",
                "hexdump>=3.2",
                "lxml>=3.4.4",
                "fluent-logger>=0.4.0",
                ]
if PY3:
    requirements.append("osspy3k>=0.4.0")
else:
    requirements.append("oss")

setup(
    name="cocommon",
    version="0.13.1",
    packages=find_packages(),
    zip_safe=False,

    description="Common Utils and Tricks",
    long_description="Common Utils and Tricks",
    author="coppla",
    author_email="januszry@gmail.com",

    license="GPL",
    keywords=("utils"),
    platforms="Independant",
    url="",
    entry_points={'console_scripts': [
        ]},

    install_requires=requirements)
