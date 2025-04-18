"""Setup script for HCshinobi package.

This script handles the installation of the HCshinobi package
and its dependencies.
"""
from setuptools import setup, find_packages

# Read README for long description
with open("README.md", "r", encoding="utf-8") as f:
    long_description = f.read()

setup(
    name="HCshinobi",
    version="1.0.0",
    author="Victor",
    description="Discord bot for Shinobi RPG system",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/yourusername/HCshinobi",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Topic :: Games/Entertainment :: Role-Playing",
    ],
    python_requires=">=3.8",
    install_requires=[
        "discord.py>=2.0.0",
        "python-dotenv>=0.19.0",
        "aiohttp>=3.8.0",
        "dataclasses-json>=0.5.7",
    ],
    extras_require={
        "dev": [
            "pytest>=6.0.0",
            "pytest-asyncio>=0.18.0",
            "pytest-cov>=2.12.0",
            "black>=22.0.0",
            "isort>=5.10.0",
            "flake8>=4.0.0",
            "mypy>=0.910",
        ],
    },
    entry_points={
        "console_scripts": [
            "hcshinobi=HCshinobi.run:main",
        ],
    },
) 