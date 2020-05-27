import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="squealy",
    version="0.2.1",
    author="Sripathi Krishnan",
    author_email="sripathi.krishnan@hashedin.com",
    description="A small example package",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/hashedin/squealy",
    packages=setuptools.find_packages(),
    install_requires=['jinjasql>=0.1.7', 'PyYAML'],
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires='>=3.6',
)