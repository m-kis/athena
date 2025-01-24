from setuptools import setup, find_packages

setup(
   name="athena-log",
   version="0.1.0",
   packages=find_packages(),
   install_requires=[
       "athena-core",
       "pandas>=2.0.0",
       "scipy>=1.10.0",
       "numpy>=1.24.0"
   ],
)
