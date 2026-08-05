from setuptools import find_packages, setup

setup(
    name = "ShopBuddy",
    version = "0.0.1",
    author = "Syed Areeb Ahmad",
    author_email = "ahmad.syedareeb7@gmail.com",
    packages = find_packages(),
    install_requires=[
        "langchain-astradb",
        "langchain",
        "langchain-google-genai",
        "langchain-core",
        "fastapi",
        "uvicorn",
        "python-multipart",
        "jinja2",
        "python-dotenv",
        "pandas",
        "undetected-chromedriver",
        "selenium",
        "beautifulsoup4",
    ]
)