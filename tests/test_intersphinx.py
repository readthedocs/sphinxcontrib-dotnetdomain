import os
import unittest

import mock

from util import SphinxTestCase, MockTestXMLBuilder, MockWithReturn, MockSphinx
from sphinxcontrib.dotnetdomain import DotNetDomain


def intersphinx_load_mappings(app):
    app.builder.env.intersphinx_inventory = {
        u'dn:class': {
            u'InterClass': (
                u'Test',
                u'0.1',
                u'http://example.com/en/latest/index.html#InterClass',
                u'-'
            ),
        },
    }
    app.builder.env.named_intersphinx_inventory = {
        'test': app.builder.env.intersphinx_inventory
    }


class IntersphinxTests(SphinxTestCase):
    '''Intersphinx linking correctly'''

    def setUp(self):
        super(IntersphinxTests, self).setUp()
        self.app.builder = MockTestXMLBuilder(self.app)
        self.app.setup_extension('sphinx.ext.intersphinx')
        intersphinx_load_mappings(self.app)

    def test_intersphinx(self):
        '''Basic cross references, not nested'''
        self.app._mock_build(
            '''
            :dn:class:`InterClass`
            :dn:cls:`InterClass`
            ''')
        self.assertNoXRef('InterClass', obj_type='class', obj_ref_type='cls')
        self.assertIn(
            ('<reference internal="False" '
             'reftitle="(in Test v0.1)" '
             'refuri="http://example.com/en/latest/index.html#InterClass">'
             '<literal classes="xref dn dn-class">InterClass</literal>'
             '</reference>'),
            self.app.builder.output['index'],
        )
        self.assertIn(
            ('<reference internal="False" '
             'reftitle="(in Test v0.1)" '
             'refuri="http://example.com/en/latest/index.html#InterClass">'
             '<literal classes="xref dn dn-cls">InterClass</literal>'
             '</reference>'),
            self.app.builder.output['index'],
        )
