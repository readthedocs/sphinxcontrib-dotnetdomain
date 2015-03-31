'''Test .NET signature parsing'''

import unittest

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

    def test_full_name(self):
        '''Full name output'''
        sig = DotNetSignature.from_string('Foo.Bar')
        self.assertEqual(sig.full_name(), 'Foo.Bar')
        sig = DotNetSignature.from_string('Foo.Bar.test(something)')
        self.assertEqual(sig.full_name(), 'Foo.Bar.test')
        sig = DotNetSignature.from_string('test(something)')
        self.assertEqual(sig.full_name(), 'test')
