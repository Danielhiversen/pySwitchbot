from setuptools import setup

setup(
    name="PySwitchbot",
    packages=["switchbot", "switchbot.devices", "switchbot.adv_parsers"],
    install_requires=["async_timeout>=4.0.1", "bleak>=0.17.0", "bleak-retry-connector>=1.17.1"],
    version="0.20.7",
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
