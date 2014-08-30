from setuptools import setup, find_packages
from codecs import open
from os import path

here = path.abspath(path.dirname(__file__))

with open(path.join(here, 'DESCRIPTION.rst'), encoding='utf-8') as f:
    long_description = f.read()
    
with open(path.join(here, 'requirements.txt'), encoding='utf-8') as f:
    requirements = f.readlines().replace("\n","")

setup(
    name='har2python',
    version='0.7.0',
    description='Tool for corvert har file to python code',
    long_description=long_description,
    url='',
    author='Michal Cáb',
    author_email='majkl.cab@gmail.com',
    license='MIT',
    classifiers=[
        'Development Status :: 4 - Beta',
        'Intended Audience :: Developers',
        'Topic :: Software Development :: Build Tools',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 2.7',
    ],

    keywords='har request http generate code',
    packages=find_packages(exclude=['contrib', 'docs', 'tests*']),
    install_requires=requirements,
    package_data={
        'sample': [''],
    }
)
