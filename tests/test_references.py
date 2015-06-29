import json
import os
import shutil
import unittest
from contextlib import contextmanager

from util import MockSphinx


class ReferenceTests(unittest.TestCase):
    '''Parse sphinx project, test references are generated'''

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
        '''Assert reference is found and matches criteria'''
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
        except:
            pass
        else:
            AssertionError('Reference match found')

    def test_namespace_valid(self):
        '''Namespace valid parsing'''
        self.app._mock_build(
            '''
            .. dn:namespace:: NamespaceValid

            .. dn:namespace:: NamespaceValid.More

            ''')
        self.assertRef('NamespaceValid', 'namespace')
        self.assertRef('NamespaceValid.More', 'namespace')

    def test_namespace_invalid(self):
        '''Invalid namespaces raise warnings'''
        self.app._mock_build(
            '''
            .. dn:namespace:: Namespace Invalid

            ''')
        warnings = self.app._warning.getvalue()
        assert 'WARNING: Parsing signature failed: "Namespace Invalid"' in warnings
        self.assertNotRef('Namespace Invalid')

    def test_namespace_nested(self):
        '''Namespace nested in namespace retains compound namespace name'''
        self.app._mock_build(
            '''
            .. dn:namespace:: NamespaceValid

                .. dn:namespace:: More

                    .. dn:namespace:: EvenMore

            ''')
        self.assertRef('NamespaceValid', 'namespace')
        self.assertRef('NamespaceValid.More', 'namespace')
        self.assertRef('NamespaceValid.More.EvenMore', 'namespace')

    def test_class_valid(self):
        '''Valid class parsing'''
        self.app._mock_build(
            '''
            .. dn:class:: ClassValid

            .. dn:class:: ClassValid<T>

            .. dn:class:: ClassValid`1

            '''
        )
        self.assertRef('ClassValid', 'class')
        self.assertRef('ClassValid<T>', 'class')
        self.assertRef('ClassValid`1', 'class')

    def test_class_invalid(self):
        '''Invalid class parsing'''
        self.app._mock_build(
            '''
            .. dn:class:: Class NotValid

            .. dn:class:: ClassParens()

            .. dn:class:: ClassValid`1``0

            '''
        )
        warnings = self.app._warning.getvalue()
        self.assertNotRef('Class', 'class')
        self.assertNotRef('Class NotValid', 'class')
        assert 'WARNING: Parsing signature failed: "Class NotValid"' in warnings
        self.assertNotRef('ClassParens', 'class')
        assert 'WARNING: Parsing signature failed: "ClassParens()"' in warnings
        self.assertNotRef('ClassValid`1``0', 'class')
        assert 'WARNING: Parsing signature failed: "ClassValid`1``0"' in warnings

    def test_class_namespace_nested(self):
        '''Class nested in namespace

        Subnested class is respected in the input, though may not be a valid .NET
        construct
        '''
        self.app._mock_build(
            '''
            .. dn:namespace:: Namespace

                .. dn:class:: NestedClass

                    .. dn:class:: SubNestedClass

            '''
        )
        self.assertRef('Namespace.NestedClass', 'class')
        self.assertRef('Namespace.NestedClass.SubNestedClass', 'class')
