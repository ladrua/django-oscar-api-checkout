#!/usr/bin/env python
from setuptools import setup, find_packages, Distribution
import codecs
import os.path

# Make sure versiontag exists before going any further
Distribution().fetch_build_eggs("versiontag>=1.2.0")

from versiontag import get_version, cache_git_tag  # NOQA


packages = find_packages("src")

install_requires = [
    "Django>=3.2",
    "django-oscar>=3.0",
    "django-oscar-api>=2.0.0",
]

extras_require = {
    "development": [
        "coverage>=4.4.2",
        "flake8>=3.2.1",
        "psycopg2-binary>=2.8.3",
        "PyYAML>=3.12",
        "sorl-thumbnail>=11.04",
        "sphinx>=1.5.2",
        "tox>=2.6.0",
        "unittest-xml-reporting>=3.0.4",
        "versiontag>=1.2.0",
    ],
}


def fpath(name):
    return os.path.join(os.path.dirname(__file__), name)


def read(fname):
    return codecs.open(fpath(fname), encoding="utf-8").read()


cache_git_tag()

setup(
    name="django-oscar-api-checkout",
    description="An extension on top of django-oscar-api providing a more flexible checkout API with a pluggable payment methods interface.",
    version=get_version(pypi=True),
    long_description=open("README.rst").read(),
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Environment :: Web Environment",
        "Framework :: Django",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: ISC License (ISCL)",
        "Operating System :: Unix",
        "Programming Language :: Python",
        "Programming Language :: Python :: 3",
    ],
    author="Craig Weber",
    author_email="crgwbr@gmail.com",
    url="https://gitlab.com/thelabnyc/django-oscar/django-oscar-api-checkout",
    license="ISC",
    package_dir={"": "src"},
    packages=packages,
    include_package_data=True,
    install_requires=install_requires,
    extras_require=extras_require,
)
