from setuptools import setup

setup(
    name = 'PySwitchbot',
    packages = ['switchbot'],
    install_requires=['bleak', 'bleak-retry-connector'],
    version = '0.15.1',
    description = 'A library to communicate with Switchbot',
    author='Daniel Hjelseth Hoyer',
    url='https://github.com/Danielhiversen/pySwitchbot/',
    license='MIT',
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Environment :: Other Environment',
        'Intended Audience :: Developers',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Topic :: Home Automation',
        'Topic :: Software Development :: Libraries :: Python Modules'
        ]
)
