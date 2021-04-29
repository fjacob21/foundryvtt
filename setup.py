import setuptools

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setuptools.setup(
    name="foundryvtt", # Replace with your own username
    version="0.1.0",
    author="Frederic Jacob",
    author_email="fjacob21@hotmail.com",
    description="A package to manage a FoundryVTT service and data",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/fjacob21/foundryvtt",
    project_urls={
        "Bug Tracker": "https://github.com/fjacob21/foundryvtt/issues",
    },
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: Centos 8",
    ],
    package_dir={"": "src"},
    scripts=['bin/fvtt'],
    packages=setuptools.find_packages(where="src"),
    python_requires=">=3.6",
)