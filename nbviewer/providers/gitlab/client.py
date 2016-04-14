#-----------------------------------------------------------------------------
#  Copyright (C) 2013 The IPython Development Team
#
#  Distributed under the terms of the BSD License.  The full license is in
#  the file COPYING, distributed as part of this software.
#-----------------------------------------------------------------------------

import json
import os

try: # py3
    from urllib.parse import urlparse
except ImportError:
    from urlparse import urlparse

from tornado.concurrent import Future
from tornado.httpclient import AsyncHTTPClient, HTTPError
from tornado.httputil import url_concat
from tornado.log import app_log

from ...utils import url_path_join, quote, response_text

#-----------------------------------------------------------------------------
# Async GitLab Client
#-----------------------------------------------------------------------------

class AsyncGitLabClient(object):
    """AsyncHTTPClient wrapper with methods for common requests"""
    auth = None
    
    def __init__(self, client=None):
        self.client = client or AsyncHTTPClient()
        self.gitlab_url = os.environ.get('GITLAB_URL', '')
        self.gitlab_api_url = url_path_join(self.gitlab_url, quote("/api/v3"))
        self.authenticate()

    def authenticate(self):
        self.auth = {
            'private_token' : os.environ.get('GITLAB_API_TOKEN', ''),
        }
        self.auth = {k:v for k,v in self.auth.items() if v}
    
    def fetch(self, url, callback=None, params=None, **kwargs):
        """Add GitHub auth to self.client.fetch"""

        if not url.startswith(self.gitlab_api_url):
            raise ValueError(
                "Only fetch GitHub urls with GitHub auth (%s)" % url
            )
        params = {} if params is None else params
        kwargs.setdefault('user_agent', 'Tornado-Async-GitLab-Client')
        if self.auth:
            params.update(self.auth)
        url = url_concat(url, params)
        app_log.info(url)
        future = self.client.fetch(url, callback, **kwargs)
        return future

    def gitlab_api_request(self, path, callback=None, **kwargs):
        """Make a GitHub API request to URL
        
        URL is constructed from url and params, if specified.
        callback and **kwargs are passed to client.fetch unmodified.
        """
        url = url_path_join(self.gitlab_api_url, quote(path))
        return self.fetch(url, callback, **kwargs)


    def get_projects(self, user, callback=None, **kwargs):
        """List a user's repos"""
        path = u"projects"
        params = kwargs.setdefault('params', {})
        params['sudo'] = user
        return self.gitlab_api_request(path, callback, **kwargs)

    def get_file(self, user, repo, path, callback=None, ref=None, **kwargs):
        api = u'projects/{user}%2F{repo}/repository/files'.format(**locals())
        params = kwargs.setdefault('params', {})
        params['ref'] = ref
        params['file_path'] = path
        #return self.gitlab_api_request(api, callback, **kwargs)
        # this is to work around lack of support for namespace/repo in gitlab (see https://github.com/gitlabhq/gitlabhq/issues/8290)
        url = url_path_join(self.gitlab_api_url, api)
        return self.fetch(url, callback, **kwargs)


## TODO - is this even needed?
    def get_contents(self, user, repo, path, callback=None, ref=None, **kwargs):
        """Make contents API request - either file contents or directory listing"""
        path = u'repos/{user}/{repo}/contents/{path}'.format(**locals())
        if ref is not None:
            params = kwargs.setdefault('params', {})
            params['ref'] = ref
        return self.gitlab_api_request(path, callback, **kwargs)

    def get_tree(self, user, repo, path, ref=None, callback=None, **kwargs):
        """Get a git tree"""
        api = u"projects/{user}%2F{repo}/repository/tree".format(**locals())
        params = kwargs.setdefault('params', {})
        if path:
            params['path'] = path
        if ref:
            params['ref_name'] = ref
        #return self.gitlab_api_request(path, callback, **kwargs)
         # this is to work around lack of support for namespace/repo in gitlab (see https://github.com/gitlabhq/gitlabhq/issues/8290)
        url = url_path_join(self.gitlab_api_url, api)
        return self.fetch(url, callback, **kwargs)

    
    def _extract_tree_entry(self, path, tree_response):
        """extract a single tree entry from a file list
        
        For use as a callback in get_tree_entry
        raises 404 if not found
        """
        tree_response.rethrow()
        jsondata = response_text(tree_response)
        data = json.loads(jsondata)
        for entry in data:
            if entry['path'] == path:
                return entry
        
        raise HTTPError(404, "%s not found among %i files" % (path, len(data['tree'])))
    
    def get_tree_entry(self, user, repo, path, ref='master', callback=None, **kwargs):
        """Get a single tree entry for a path
        
        Useful for finding the blob url for a given path.
        """
        # only need a recursive fetch if it's not in the top-level dir
        if '/' in path:
            kwargs['recursive'] = True

        f = Future()
        def cb(response):
            try:
                tree_entry = self._extract_tree_entry(path, response)
            except Exception as e:
                f.set_exception(e)
                return
            if callback:
                result = callback(tree_entry)
            else:
                result = tree_entry
            f.set_result(result)
        
        self.get_tree(user, repo, ref=ref, callback=cb, **kwargs)
        return f
    
