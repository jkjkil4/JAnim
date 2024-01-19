# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

import os
import sys

# -- Project information -----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information

project = 'JAnim'
copyright = '2023, jkjkil4'
author = 'jkjkil4'
release = '0.0.1'

# -- General configuration ---------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#general-configuration

extensions = ['sphinx.ext.autodoc']
autodoc_member_order = 'bysource'
# autodoc_default_flags = ['members', 'show-inheritance']

templates_path = ['_templates']
exclude_patterns = []

language = 'zh_CN'
locale_dirs = ['locales/']
gettext_compact = False     # optional

# -- Options for HTML output -------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output

html_theme = 'furo'
html_static_path = ['_static']
html_css_files = [
    'custom.css',
    'colors.css'
]

sys.path.insert(0, os.path.abspath('../..'))
