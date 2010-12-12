# -*- coding: utf-8 -*-
#
# habitat documentation build configuration file, created by
# sphinx-quickstart on Sat Dec 11 14:40:10 2010.

import sys, os

sys.path.insert(0, os.path.abspath(os.path.join(__file__, "..", "..")))
import habitat

needs_sphinx = '1.0'

extensions = ['sphinx.ext.autodoc', 'sphinx.ext.viewcode',
              'sphinx.ext.intersphinx']


source_suffix = '.rst'
#source_encoding = 'utf-8-sig'

master_doc = 'index'

project = habitat.__name__
copyright = habitat.__copyright__

# The short X.Y version.
version = habitat.__version__
# The full version, including alpha/beta/rc tags.
release = habitat.__version__

#language = None

pygments_style = 'sphinx'

html_theme = 'default'
#html_logo = None
#html_favicon = None

# Base URL from which the finished HTML is served
html_use_opensearch = 'http://habitat.habhub.org/docs/'

# Output file base name for HTML help builder.
htmlhelp_basename = 'habitatdoc'

autodoc_default_flags = ["members"]
autodoc_member_order = "bysource"
autoclass_content = "both"

intersphinx_mapping = {'python': ('http://docs.python.org/2.7', None)}
