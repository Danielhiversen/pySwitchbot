from setuptools import setup

setup(
    name="PySwitchbot",
    packages=["switchbot", "switchbot.devices", "switchbot.adv_parsers"],
    install_requires=[
        "bleak>=0.19.0",
        "bleak-retry-connector>=3.4.0",
        "cryptography>=39.0.0",
        "pyOpenSSL>=23.0.0",
        "boto3>=1.20.24",
        "requests>=2.28.1",
    ],
    version="0.44.1",
    description="A library to communicate with Switchbot",
    author="Daniel Hjelseth Hoyer",
    url="https://github.com/Danielhiversen/pySwitchbot/",
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
