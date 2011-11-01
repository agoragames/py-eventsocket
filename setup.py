import os
from distutils.core import setup

requirements = map(str.strip, open('requirements.txt').readlines())

setup(
    name='py_eventsocket',
    version='0.1.5',
    author="Aaron Westendorf",
    author_email="aaron@agoragames.com",
    url='https://github.com/agoragames/py-eventsocket',
    license='LICENSE.txt',
    py_modules = ['eventsocket'],
    description='Easy to use TCP socket based on libevent',
    install_requires = requirements,
    long_description=open('README.rst').read(),
    keywords=['socket', 'event'],
    classifiers=[
        'Development Status :: 4 - Beta',
        'License :: OSI Approved :: BSD License',
        "Intended Audience :: Developers",
        "Operating System :: POSIX",
        "Topic :: Communications",
        "Topic :: Software Development :: Libraries :: Python Modules",
        'Programming Language :: Python',
        'Topic :: Software Development :: Libraries'
    ]
)
