#!/usr/bin/env python
# -*- coding:utf-8 -*-

from setuptools import setup, find_packages

setup(
    name="cocommon",
    version="0.9.4",
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
        'auprober=cocommon.audio.auprober:main',
        'wavanalyze=cocommon.audio.wavfile:main',
        ]},

    install_requires=["requests>=2.3.0",
                      "pexpect>=3.3",
                      "ujson>=1.33",
                      "hexdump>=3.2"])
