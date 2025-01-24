from setuptools import setup, find_packages

setup(
    name="athena-core",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "fastapi>=0.104.0",
        "langchain>=0.0.330",
        "chromadb>=0.4.14",
        "psycopg2-binary>=2.9.9",
        "pydantic>=2.4.2",
        "redis>=4.5.5",
        "ollama>=0.1.0"
    ],
)
