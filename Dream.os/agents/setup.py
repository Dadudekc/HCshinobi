from setuptools import setup, find_packages

setup(
    name="dreamforge-social",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "jinja2>=3.0.0",
        "facebook-sdk>=3.1.0",  # For Facebook integration
        "linkedin-api>=2.0.0",  # For LinkedIn integration
        "instabot>=0.117.0",    # For Instagram integration
        "tweepy>=4.0.0",        # For Twitter integration
        "pillow>=9.0.0",        # For image generation
    ],
    author="DreamOS Team",
    description="Social media integration for DreamOS",
    python_requires=">=3.7",
) 