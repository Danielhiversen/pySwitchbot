from setuptools import setup

setup(
    name = 'PySwitchbot',
    packages = ['switchbot'],
    install_requires=['bluepy', 'func_timeout'],
    version = '0.8.0',
    description = 'A library to communicate with Switchbot',
    author='Daniel Hoyer Iversen',
    url='https://github.com/Danielhiversen/pySwitchbot/',
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
