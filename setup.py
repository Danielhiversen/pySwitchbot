from setuptools import setup

setup(
    name = 'PySwitchbot',
    packages = ['switchbot'],
    install_requires=['bluepy'],
    version = '0.13.0',
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
