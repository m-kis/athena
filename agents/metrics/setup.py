from setuptools import setup, find_packages

setup(
   name="athena-metrics",
   version="0.1.0",
   packages=find_packages(),
   install_requires=[
       "athena-core",
       "prophet>=1.1.4",
       "pandas>=2.0.0",
       "numpy>=1.24.0"
   ],
)
