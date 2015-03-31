'''Sphinx .NET domain

Domain to support .NET languages.
'''

import sys

from setuptools import setup, find_packages


setup(
    name='sphinxcontrib-dotnetdomain',
    version='0.1',
    url='http://github.com/agjohnson/sphinxcontrib-dotnetdomain',
    download_url='http://pypi.python.org/pypi/sphinxcontrib-dotnetdomain',
    license='MIT',
    author='Anthony Johnson',
    author_email='aj@ohess.org',
    description='Sphinx "dotnetdomain" extension',
    long_description=sys.modules[__name__].__doc__,
    zip_safe=False,
    classifiers=[
        'Development Status :: 2 - Pre-Alpha',
        'Environment :: Console',
        'Environment :: Web Environment',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Topic :: Documentation',
        'Topic :: Utilities',
    ],
    platforms='any',
    packages=find_packages(),
    include_package_data=True,
    install_requires=['Sphinx>=0.6'],
    namespace_packages=['sphinxcontrib'],
    test_suite='nose.collector',
    tests_require=['nose'],
)
