from setuptools import setup, find_packages

setup(
    name="airqual-data-fetcher",                  
    version="0.1.0",                              
    description="Fetch, clean, merge, and explore city-level air quality + climate datasets.",
    long_description=open("README.md", encoding="utf-8").read(),
    long_description_content_type="text/markdown",
    author="Yuxi Xiao",
    license='MIT',
    packages=find_packages(exclude=("tests", "testing", "notebooks")),
    include_package_data=True,


    package_data={
        "airqual_data_fetcher": ["*.txt", "*.csv"],
    },

    install_requires=[
        "pandas",
        "numpy",
        "requests",
        "beautifulsoup4",
        "lxml",
        "matplotlib",
        "pycountry",
    ],

    python_requires=">=3.10",


)
