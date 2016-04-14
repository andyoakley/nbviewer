# encoding: utf-8

import mock

from unittest import TestCase

from ....utils import transform_ipynb_uri
from ..handlers import uri_rewrites



class TestRewrite(TestCase):
    def setUp(self):
        with mock.patch('os.environ.get', return_value='https://gitlab.com'):
            self.uri_rewrite_list = uri_rewrites()
        print(self.uri_rewrite_list)


    ## TODO test case for trailing various forms of Gitlab URL

    def assert_rewrite(self, uri, rewrite):
        new = transform_ipynb_uri(uri, self.uri_rewrite_list)
        self.assertEqual(new, rewrite)


    def test_blob(self):
        uri = u'https://gitlab.com/user/reopname/blob/deadbeef/a mřížka.ipynb'
        rewrite = u'/gitlab/user/reopname/blob/deadbeef/a mřížka.ipynb'
        self.assert_rewrite(uri, rewrite)

    def test_raw_uri(self):
        uri = u'https://gitlab.com/user/reopname/raw/deadbeef/a mřížka.ipynb'
        rewrite = u'/gitlab/user/reopname/blob/deadbeef/a mřížka.ipynb'
        self.assert_rewrite(uri, rewrite)

    def test_tree(self):
        uri = u'https://gitlab.com/user/reopname/tree/deadbeef/a mřížka.ipynb'
        rewrite = u'/gitlab/user/reopname/tree/deadbeef/a mřížka.ipynb'
        self.assert_rewrite(uri, rewrite)
