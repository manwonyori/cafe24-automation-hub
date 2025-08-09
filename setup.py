from setuptools import setup, find_packages

setup(
    name="cafe24-automation-hub",
    version="2.0.0",
    packages=find_packages(),
    install_requires=[
        "fastapi>=0.104.1",
        "uvicorn[standard]>=0.24.0",
        "python-dotenv>=1.0.0",
        "pydantic>=2.8.0",
        "cryptography>=42.0.0",
        "httpx>=0.27.0",
        "jinja2>=3.1.2",
        "python-multipart>=0.0.6",
        "tenacity>=8.2.3",
        "requests>=2.31.0",
    ],
    python_requires=">=3.8",
)