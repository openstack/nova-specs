# -*- coding: utf-8 -*-

import datetime
import sys
import os

# If extensions (or modules to document with autodoc) are in another directory,
# add these directories to sys.path here. If the directory is relative to the
# documentation root, use os.path.abspath to make it absolute, like shown here.
sys.path.insert(0, os.path.abspath('.'))

# -- General configuration ----------------------------------------------------

# Add any Sphinx extension module names here, as strings. They can be
# extensions coming with Sphinx (named 'sphinx.ext.*') or your custom ones.
extensions = [
    'redirect',
    'sphinx.ext.todo',
    'openstackdocstheme',
    'yasfb',
    'sphinxcontrib.seqdiag',
]

todo_include_todos = True

# The master toctree document.
master_doc = 'index'

# General information about the project.
project = u'Nova Specs'
copyright = u'%s, OpenStack Nova Team' % datetime.date.today().year

# The name of the Pygments (syntax highlighting) style to use.
pygments_style = 'native'

# A list of ignored prefixes for module index sorting.
modindex_common_prefix = ['nova-specs.']

version = ''
release = ''

# -- Options for HTML output --------------------------------------------------

# The theme to use for HTML and HTML Help pages.  See the documentation for
# a list of builtin themes.
html_theme = 'openstackdocs'

# If false, no module index is generated.
html_domain_indices = False

# If false, no index is generated.
html_use_index = False


# -- openstackdocstheme configuration -----------------------------------------

openstackdocs_repo_name = 'openstack/nova-specs'
openstackdocs_bug_project = 'nova'
openstackdocs_bug_tag = 'specs'
openstackdocs_auto_name = False
openstackdocs_auto_version = False

# -- yasfb configuration ------------------------------------------------------

feed_base_url = 'https://specs.openstack.org/openstack/nova-specs'
feed_author = 'OpenStack Nova Team'


# -- seqdiag configuration ----------------------------------------------------

seqdiag_html_image_format = 'SVG'
seqdiag_antialias = True
