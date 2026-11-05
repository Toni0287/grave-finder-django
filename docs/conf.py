"""Sphinx configuration. Build with: ``sphinx-build -b html docs docs/_build``."""

import os
import sys

import django

sys.path.insert(0, os.path.abspath(".."))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "gravefinder.settings")
django.setup()

project = "Grave Finder"
author = "Luvuyo Toni"
release = "2.0"

extensions = ["sphinx.ext.autodoc", "sphinx.ext.viewcode", "sphinx.ext.napoleon"]
exclude_patterns = ["_build"]
autodoc_member_order = "bysource"

try:
    import sphinx_rtd_theme  # noqa: F401

    html_theme = "sphinx_rtd_theme"
except ImportError:
    html_theme = "alabaster"
