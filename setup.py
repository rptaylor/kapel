#!/usr/bin/env python3

from setuptools import setup, find_packages
from os import environ

environ['PIP_NO_WARN_SCRIPT_LOCATION'] = "0"

setup(name='kapel',
#      version='0.1',
      packages = find_packages(),
      install_requires=['environs', 'dirq', 'prometheus-api-client']
      )
