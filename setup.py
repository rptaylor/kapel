#!/usr/bin/env python3

from setuptools import setup, find_packages
from os import environ

setup(
    name='kapel',
    version='0.1',
    packages = ['kapel'],
    install_requires=[
        'environs',			# for handling configuration
        'dirq',				# for sending messages
        'prometheus-api-client'		# for querying Prometheus
    ],
    entry_points={
        'console_scripts': [
            'kapel = kapel:main',
        ],
    },
)
