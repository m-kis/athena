from setuptools import setup, find_packages

setup(
   name="athena-security",
   version="0.1.0",
   packages=find_packages(),
   install_requires=[
       "athena-core",
       "scipy>=1.10.0",
       "numpy>=1.24.0"
   ],
)
