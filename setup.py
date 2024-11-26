from pathlib import Path

from setuptools import setup

this_directory = Path(__file__).parent
long_description = (this_directory / "README.md").read_text()

setup(
    name="PySwitchbot",
    packages=["switchbot", "switchbot.devices", "switchbot.adv_parsers"],
    install_requires=[
        "aiohttp>=3.9.5",
        "bleak>=0.19.0",
        "bleak-retry-connector>=3.4.0",
        "cryptography>=39.0.0",
        "pyOpenSSL>=23.0.0",
    ],
    version="0.54.0",
    description="A library to communicate with Switchbot",
    long_description=long_description,
    long_description_content_type="text/markdown",
    author="Daniel Hjelseth Hoyer",
    url="https://github.com/sblibs/pySwitchbot/",
    license="MIT",
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Environment :: Other Environment",
        "Intended Audience :: Developers",
        "Operating System :: OS Independent",
        "Programming Language :: Python",
        "Topic :: Home Automation",
        "Topic :: Software Development :: Libraries :: Python Modules",
    ],
)
