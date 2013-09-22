# -*- coding: utf-8 -*-
#
# habitat documentation build configuration file, created by
# sphinx-quickstart on Sat Dec 11 14:40:10 2010.

import inspect
import sys
import os

class Mock(object):
    """
    Mock out external modules that might annoy documentation build
    systems.
    """
    def __init__(self, *args, **kwargs):
        pass
    def __call__(self, *args, **kwargs):
        code = inspect.stack()[1][4][0].strip()
        if code[0] == '@':
            def dec(f):
                return f
            return dec
        else:
            return None
    @classmethod
    def __getattr__(cls, name):
        if name in ('__file__', '__path__'):
            return '/dev/null'
        else:
            return Mock()

MOCK_MODULES = [
    'M2Crypto', 'crcmod', 'couchdbkit', 'jsonschema', 'yaml',
    'couch_named_python', 'statsd', 'pytz', 'couchdbkit.exceptions',
    'restkit', 'restkit.errors', 'strict_rfc3339'
]

for mod in MOCK_MODULES:
    sys.modules[mod] = Mock()

sys.path.insert(0, os.path.abspath(os.path.join(__file__, "..", "..")))

import habitat


needs_sphinx = '1.0'

extensions = ['sphinx.ext.autodoc', 'sphinx.ext.viewcode',
              'sphinx.ext.autosummary', 'sphinx.ext.intersphinx']


source_suffix = '.rst'
#source_encoding = 'utf-8-sig'

master_doc = 'index'

project = habitat.__name__
copyright = habitat.__short_copyright__

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
autosummary_generate = True

intersphinx_mapping = {'python': ('http://docs.python.org/2.7', None)}
