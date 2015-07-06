import unittest
import os
import shutil
from textwrap import dedent

from mock import patch

from docutils.io import StringOutput

from sphinx.builders.text import TextBuilder
from sphinx.application import Sphinx
from sphinx.environment import SphinxFileInput


class MockSphinx(Sphinx):
    '''Patches Sphinx application with MockBuilder'''

    def __init__(self, *args, **kwargs):
        kwargs['warning'] = None
        super(MockSphinx, self).__init__(*args, **kwargs)

    def _init_builder(self, buildername):
        self.builder = MockTestBuilder(self)
        self.emit('builder-inited')

    def _mock_build(self, input_lines):
        '''Mocks return of index.rst'''
        # TODO allow patching in of arbitrary files, not just index.rst
        input_lines = dedent(input_lines)
        with patch.object(SphinxFileInput, 'read') as mock_read:
            mock_read.return_value = input_lines
            self.build(force_all=True)


class MockTestBuilder(TextBuilder):
    '''Saves writer output locally, don't output to disk'''

    def __init__(self, *args, **kwargs):
        self.output = {}
        super(MockTestBuilder, self).__init__(*args, **kwargs)

    def write_doc(self, docname, doctree):
        self.current_docname = docname
        destination = StringOutput(encoding='utf-8')
        self.writer.write(doctree, destination)
        self.output[docname] = self.writer.output


class SphinxTestCase(unittest.TestCase):
    '''Test case that processes build input/output in memory for the most part

    Sets up a mocked out Sphinx application with a custom builder and string
    input to the build process.
    '''

    def setUp(self):
        os.chdir(os.path.join(os.path.dirname(__file__), 'fixtures', 'example'))
        self.app = MockSphinx(
            srcdir='.',
            confdir='.',
            outdir='_build/text',
            doctreedir='_build/.doctrees',
            buildername=None,
        )

    def tearDown(self):
        shutil.rmtree(os.path.join(os.path.dirname(__file__), 'fixtures',
                                   'example', '_build'))

    def assertRef(self, refname, type_=None, docname=None, domain='dn'):
        '''Assert reference is found and matches criteria

        :param refname: Reference name to lookup
        :param type_: Reference type to match
        :param docname: Reference docname
        :param domain: Domain moniker to use on lookup (default: dn)
        '''
        try:
            ref = self.app.env.domaindata[domain]['objects'][refname]
            (ref_docname, ref_type) = ref
            if type_ is not None and ref_type != type_:
                raise AssertionError('Reference type mismatch: {0} != {1}'
                                     .format(type_, ref_type))
            if docname is not None and ref_docname != docname:
                raise AssertionError('Reference docname mismatch: {0} != {1}'
                                     .format(docname, ref_docname))
        except KeyError:
            raise AssertionError('Reference not found: {0}'.format(refname))

    def assertNotRef(self, *args, **kwargs):
        '''Inverse of :py:meth:`assertRef`'''
        try:
            self.assertRef(*args, **kwargs)
        except AssertionError:
            pass
        else:
            AssertionError('Reference match found')
