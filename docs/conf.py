"""Sphinx configuration for the texport documentation."""

from importlib.metadata import version as _package_version

project = "texport"
author = "Joseph Bak-coleman"
copyright = "2026, Joseph Bak-coleman"
release = _package_version("texport")
version = release

extensions = [
    "myst_parser",
    "sphinx.ext.autodoc",
    "sphinx.ext.napoleon",
    "sphinx.ext.githubpages",
]
exclude_patterns = ["_build"]
napoleon_google_docstring = False
autodoc_typehints = "description"
html_theme = "furo"
html_title = "texport"
html_baseurl = "https://joebakcoleman.com/texport/"
