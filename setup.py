from setuptools import setup, find_packages

with open('README.md') as readme_file:
    readme = readme_file.read()

with open('LICENSE.md') as license_file:
    license = license_file.read()

setup(
    name='tempest',
    url='https://github.com/rwails/tempest',
    packages=find_packages()
)
