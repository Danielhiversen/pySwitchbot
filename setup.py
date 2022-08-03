from setuptools import setup

setup(
    name = 'PySwitchbot',
    packages = ['switchbot'],
    install_requires=['async_timeout>=4.0.1', 'bleak', 'bleak-retry-connector>=1.2.0'],
    version = '0.17.3',
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
