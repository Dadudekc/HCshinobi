from setuptools import setup, find_packages

setup(
    name="trinity-core",
    version="0.1.0",
    package_dir={'': 'src'},
    packages=find_packages(where='src'),
    install_requires=[
        "pydantic>=2.2.1",
        "loguru>=0.7.3",
        "psutil>=7.0.0",
    ],
    author="Dream.OS Team",
    author_email="team@dream.os",
    description="Core functionality for the Dream.OS system",
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    url="https://github.com/dream-os/trinity-core",
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3.11",
    ],
    python_requires=">=3.11",
) 