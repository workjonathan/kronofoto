# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Project information -----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information
import os, sys, django
sys.path.insert(0, os.path.abspath('..'))
#os.environ['DJANGO_SETTINGS_MODULE'] = 'tests.settings'
#django.setup()
django_settings = "tests.settings"

project = 'kronofoto'
copyright = '2025, fortepan_us'
author = 'fortepan_us'

# -- General configuration ---------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#general-configuration

extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.napoleon",
    "sphinxcontrib_django",
]

templates_path = ['_templates']
exclude_patterns = ['_build', 'Thumbs.db', '.DS_Store']

napoleon_google_docstring = True
napoleon_use_param = True
napoleon_use_rtype = True
django_show_db_tables = True



# -- Options for HTML output -------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output

html_theme = 'alabaster'
html_static_path = ['_static']
