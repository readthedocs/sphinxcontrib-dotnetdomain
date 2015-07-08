import unittest
import os
import shutil
from textwrap import dedent

from mock import Mock, patch

from docutils.io import StringOutput

from sphinx.builders.text import TextBuilder
from sphinx.application import Sphinx
from sphinx.environment import SphinxFileInput

from sphinxcontrib.dotnetdomain import DotNetDomain


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


class MockWithReturn(Mock):
    '''Mock with return value tracking

    Return values are stored in :py:attr:`call_return_list`, as a list of tuples.
    Tuples consist of ``(call_params, return_value)``, where:

        call_params
            A list of call params to match using :py:meth:`Mock.assert_has_calls`

        return_value
            The return value from the call with ``call_params``
    '''

    def __init__(self, *args, **kwargs):
        super(MockWithReturn, self).__init__(*args, **kwargs)
        self.call_return_list = []

    def __call__(self, *args, **kwargs):
        ret = super(MockWithReturn, self).__call__(*args, **kwargs)
        self.call_return_list.append((self.call_args, ret))
        return ret


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

        self.patch = patch.object(DotNetDomain, 'find_obj',
                                  wraps=self.app.env.domains['dn'].find_obj,
                                  new_callable=MockWithReturn)
        self.mocked_find_obj = self.patch.start()

    def tearDown(self):
        shutil.rmtree(os.path.join(os.path.dirname(__file__), 'fixtures',
                                   'example', '_build'))
        self.patch.stop()

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

    def assertXRef(self, name, prefix=None, obj_type=None, doc='index',
                   ret_name=None):
        '''Assert mocked find_obj was called correctly

        Test that inline references generate the correct calls and return to
        :py:meth:`DotNetDomain.find_obj`. This requires testing data with inline
        references.

        :param name: Reference name
        :param prefix: Reference prefix
        :param obj_type: Reference type
        :param doc: Document name as part of the reference return
        :param ret_name: Name of object that is found during search, this
                         defaults to ``<prefix>.<name>``, but may differ if
                         doing a reverse search
        '''
        # Assert called correctly and return exists
        args = (self.app.env, prefix, name, obj_type, 0)
        self.mocked_find_obj.assert_has_calls(calls=[(args, {})])
        found = None
        for (mock_call, mock_return) in self.mocked_find_obj.call_return_list:
            if mock_call == (args, {}):
                found = mock_return
        if found is None:
            raise AssertionError('Return not found')

        # Check return
        if ret_name is None:
            ret_name = name
            if prefix is not None:
                ret_name = '.'.join([prefix, name])
        (found_name, found_meta) = found
        self.assertIsNotNone(found_name,
                             'XRef {0} not found'.format(ret_name))
        (found_doc, found_type) = found_meta
        self.assertEqual(found_name, ret_name)
        self.assertEqual(found_doc, doc)
        self.assertTrue(any(cls.short_name == obj_type
                            for (long_name, cls)
                            in self.app.env.domains['dn'].directives.items()
                            if long_name == found_type))

    def assertNoXRef(self, *args, **kwargs):
        '''Inverse of :py:meth:`assertXRef`'''
        try:
            self.assertXRef(*args, **kwargs)
        except AssertionError:
            pass
        else:
            AssertionError('XRef match found')