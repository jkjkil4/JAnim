# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

import os
import sys

from janim import __version__

# -- Project information -----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information

project = 'JAnim'
copyright = '2023, jkjkil4'
author = 'jkjkil4'
release = __version__

# -- General configuration ---------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#general-configuration

extensions = [
    'sphinx.ext.autodoc',
    'sphinx_copybutton',
    'sphinx_tabs.tabs',
    'extensions.janim_example_ext',
    'extensions.code_desc_ext',
    'extensions.translatable_tab_ext',
    'extensions.random_choice'
]
autodoc_member_order = 'bysource'
# autodoc_default_flags = ['members', 'show-inheritance']

templates_path = ['_templates']
exclude_patterns = ['._*', '**/._*']

language = 'zh_CN'
locale_dirs = ['locales/']
gettext_compact = False     # optional

# -- Options for HTML output -------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output

html_theme = 'furo'
html_static_path = ['_static']
html_css_files = [
    'layout.css',
    'colors.css',
    'custom.css',
    'animation_timing_example.css',
    'janim_box.css',
    'random_choice.css'
]
html_favicon = '_static/favicon.ico'

sys.path.insert(0, os.path.abspath('../..'))
sys.path.insert(0, os.path.abspath('.'))
