#!/usr/bin/env python
from pathlib import Path

from setuptools import setup

long_description = (Path(__file__).parent / "README.md").read_text(encoding="utf-8")


setup(
    name="thermia-genesis-modbus",
    version="1.1.0",
    author="Johan Isaksson",
    author_email="johan@generatorhallen.se",
    description="Python wrapper for getting data from Thermia Mega and Inverter heat pumps \
        via Modbus TCP.",
    long_description=long_description,
    long_description_content_type="text/markdown",
    include_package_data=True,
    url="https://github.com/JanJoh/thermia-genesis-modbus",
    license="MIT",
    packages=["thermia_genesis_modbus"],
    python_requires=">=3.6",
    install_requires=["pymodbustcp==0.1.10"],
    classifiers=[
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python",
        "Operating System :: OS Independent",
    ],
    setup_requires=("pytest-runner"),
    tests_require=(
        "asynctest",
        "pytest-cov",
        "pytest-asyncio",
        "pytest-trio",
        "pytest-tornasync",
    ),
)
