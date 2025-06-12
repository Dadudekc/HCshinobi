"""
Setup script for AutoBlogger.
"""

from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

with open("requirements.txt", "r", encoding="utf-8") as fh:
    requirements = [
        line.strip() for line in fh if line.strip() and not line.startswith("#")
    ]

setup(
    name="autoblogger",
    version="0.1.0",
    author="Your Name",
    author_email="your.email@example.com",
    description="An AI-powered blog generation and management system",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/yourusername/autoblogger",
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
        "Programming Language :: Python :: 3.11",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Topic :: Internet :: WWW/HTTP :: Dynamic Content",
        "Topic :: Text Processing :: Markup",
    ],
    python_requires=">=3.8",
    install_requires=requirements,
    entry_points={
        "console_scripts": [
            "autoblogger=autoblogger.main:main",
            "verify-beta=autoblogger.verify_beta:main",
        ],
    },
    include_package_data=True,
    package_data={
        "autoblogger": ["py.typed"],
    },
    zip_safe=False,
)
