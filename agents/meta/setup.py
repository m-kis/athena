from setuptools import setup, find_packages

setup(
   name="athena-meta",
   version="0.1.0",
   packages=find_packages(),
   install_requires=[
       "athena-core",
       "transformers>=4.0.0",
       "torch>=2.0.0"
   ],
)
