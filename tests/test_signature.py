'''Test .NET signature parsing'''

import unittest
import time

from sphinxcontrib.dotnetdomain import DotNetSignature


class ParseTests(unittest.TestCase):

    def test_parse_plain(self):
        '''Parsing vanilla class signatures'''
        sig = DotNetSignature.from_string('Foo.Bar')
        self.assertEqual(sig.prefix, 'Foo')
        self.assertEqual(sig.member, 'Bar')
        self.assertIsNone(sig.arguments)

        sig = DotNetSignature.from_string('Foo.Bar.test(something)')
        self.assertEqual(sig.prefix, 'Foo.Bar')
        self.assertEqual(sig.member, 'test')
        self.assertIn('something', sig.arguments)

        sig = DotNetSignature.from_string('test(something)')
        self.assertIsNone(sig.prefix)
        self.assertEqual(sig.member, 'test')
        self.assertIn('something', sig.arguments)

    def test_non_matching(self):
        '''Non matching signature should return signature class instance'''
        self.assertRaises(ValueError, DotNetSignature.from_string,
                          '#this&will%never*parse')

    def test_full_name(self):
        '''Full name output'''
        sig = DotNetSignature.from_string('Foo.Bar')
        self.assertEqual(sig.full_name(), 'Foo.Bar')
        sig = DotNetSignature.from_string('Foo.Bar.test(something)')
        self.assertEqual(sig.full_name(), 'Foo.Bar.test')
        sig = DotNetSignature.from_string('test(something)')
        self.assertEqual(sig.full_name(), 'test')

    def test_generic_type(self):
        '''Generic type declartion in signature'''
        sig = DotNetSignature.from_string('Foo.Bar`0')
        self.assertEqual(sig.full_name(), 'Foo.Bar`0')
        sig = DotNetSignature.from_string('Foo.Bar`99')
        self.assertEqual(sig.full_name(), 'Foo.Bar`99')
        sig = DotNetSignature.from_string('Foo.Bar``0')
        self.assertEqual(sig.full_name(), 'Foo.Bar``0')

    def test_slow_backtrack(self):
        '''Slow query because of excessive backtracking'''
        time_start = time.time()
        sig = DotNetSignature.from_string('Microsoft.CodeAnalysis.Classification.ClassificationTypeNames.XmlDocCommentAttributeName')
        self.assertEqual(sig.prefix, 'Microsoft.CodeAnalysis.Classification.ClassificationTypeNames')
        self.assertEqual(sig.member, 'XmlDocCommentAttributeName')
        time_end = time.time()
        self.assertTrue((time_end - time_start) < 2)
