from setuptools import setup, find_packages

setup(
    name="SCALE",
    version="0.0.1",
    packages=find_packages(),
    package_data = {'':['*.txt']},
    test_suite="scale.test_dsl.test_suite",
)
