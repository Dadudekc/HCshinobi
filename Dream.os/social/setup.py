"""Setup file for the social package."""

from setuptools import setup, find_packages

setup(
    name="social",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "selenium>=4.0.0",
        "aiohttp>=3.8.0",
        "pytest>=7.0.0",
        "pytest-asyncio>=0.18.0",
        "pytest-mock>=3.6.0",
    ],
    python_requires=">=3.8",
) 