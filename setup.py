from setuptools import setup

setup(
    name = 'switchbotPatched',
    packages = ['switchbotPatched'],
    install_requires=['bluepy'],
    version = '0.13.6',
    description = 'A Unofficial library to communicate with Switchbot',
    author='Ninad',
    author_email='ninadpchaudhari@gmail.com',
    url='https://github.com/Switchbot-Python/pySwitchbot-patched',
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
