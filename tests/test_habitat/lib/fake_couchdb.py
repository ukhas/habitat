# Copyright 2010 (C) Adam Greig
#
# This file is part of habitat.
#
# habitat is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# habitat is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with habitat.  If not, see <http://www.gnu.org/licenses/>.

"""
A mock couchdbkit.client.Database object that supports views and
fetching documents.
"""

import uuid

class ViewResults(object):
    """
    Fake view results which will return what they are initialised with
    when first() is called.
    """
    def __init__(self, result=None):
        self.result = result
        self.results = {}
    def first(self):
        return self.result

class Database(object):
    """A fake Database which implements __getitem__, save_doc and view."""
    def __init__(self, docs=None):
        if docs:
            self.docs = docs
        else:
            self.docs = {}
        self.saved_docs = []
        self.view_string = None
        self.view_params = None
        self.view_results = {}
        self.default_view_results = ViewResults()
    def __getitem__(self, key):
        return self.docs[key]
    def __setitem__(self, key, item):
        self.docs[key] = item
    def __contains__(self, key):
        return key in self.docs
    def save_doc(self, doc):
        doc_id = unicode(uuid.uuid4())
        self.docs[doc_id] = doc
        self.saved_docs.append(doc)
    def view(self, view, **params):
        self.view_string = view
        self.view_params = params
        if view in self.view_results:
            return self.view_results[view]
        else:
            return self.default_view_results
