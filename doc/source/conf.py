# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

import os
import sys

from janim import __version__

os.environ['JANIM_SPHINX_BUILD'] = '1'

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
    'extensions.bili_example',
    'extensions.code_desc_ext',
    'extensions.translatable_tab_ext',
    'extensions.random_choice',
    'extensions.gettext_filters',
]
autodoc_member_order = 'bysource'
# autodoc_default_flags = ['members', 'show-inheritance']
# autodoc_inherit_docstrings = False

templates_path = ['_templates']
exclude_patterns = ['._*', '**/._*']

language = 'zh_CN'
locale_dirs = ['locales/']
gettext_compact = False  # optional
gettext_additional_targets = ['literal-block']  # make code-block translatable

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
    'random_choice.css',
]
html_js_files = [
    'auto-scroll-current.js',
]
html_favicon = '_static/favicon.ico'

# 对预发布版给出提示
IS_PRERELEASE = '-' in release

html_theme_options = {
    'announcement': (
        '🚧 <strong>预发布版本文档</strong> — '
        '可能与稳定版存在一定差异，'
        '你可以通过角落的悬浮菜单切换到稳定版本。'
        '<br><br>'
        '🚧 <strong>Pre-release documentation</strong> — '
        'This may differ from the stable version. '
        'You can switch to the stable version via the corner flyout menu.'
    )
    if IS_PRERELEASE
    else None
}

sys.path.insert(0, os.path.abspath('../..'))
sys.path.insert(0, os.path.abspath('.'))
