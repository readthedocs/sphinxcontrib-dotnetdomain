'''Test .NET signature parsing'''

import unittest
import time

from sphinxcontrib.dotnetdomain import (DotNetCallable, DotNetObjectNested,
                                        DotNetConstructor, DotNetOperator)


class ParseTests(unittest.TestCase):

    def test_parse_nested_plain(self):
        '''Parsing plain nested object signatures'''
        sig = DotNetObjectNested.parse_signature('Foo.Bar')
        self.assertEqual(sig.prefix, 'Foo')
        self.assertEqual(sig.member, 'Bar')
        self.assertIsNone(sig.arguments)

    def test_parse_callable_plain(self):
        '''Parsing plain callable object signatures'''
        sig = DotNetCallable.parse_signature('Foo.Bar.test(something)')
        self.assertEqual(sig.prefix, 'Foo.Bar')
        self.assertEqual(sig.member, 'test')
        self.assertIn('something', sig.arguments)

        sig = DotNetCallable.parse_signature('test(something)')
        self.assertIsNone(sig.prefix)
        self.assertEqual(sig.member, 'test')
        self.assertIn('something', sig.arguments)

    def test_non_matching(self):
        '''Non matching signature should return signature class instance'''
        self.assertRaises(ValueError, DotNetCallable.parse_signature,
                          '#this&will%never*parse')

    def test_full_name(self):
        '''Full name output'''
        sig = DotNetCallable.parse_signature('Foo.Bar')
        self.assertEqual(sig.full_name(), 'Foo.Bar')
        sig = DotNetCallable.parse_signature('Foo.Bar.test(something)')
        self.assertEqual(sig.full_name(), 'Foo.Bar.test')
        sig = DotNetCallable.parse_signature('test(something)')
        self.assertEqual(sig.full_name(), 'test')

    def test_generic_type(self):
        '''Generic type declartion in signature'''
        sig = DotNetCallable.parse_signature('Foo.Bar`0')
        self.assertEqual(sig.full_name(), 'Foo.Bar`0')
        sig = DotNetCallable.parse_signature('Foo.Bar`99')
        self.assertEqual(sig.full_name(), 'Foo.Bar`99')
        sig = DotNetCallable.parse_signature('Foo.Bar``0')
        self.assertEqual(sig.full_name(), 'Foo.Bar``0')
        sig = DotNetCallable.parse_signature('Foo.Bar`1``0')
        self.assertEqual(sig.full_name(), 'Foo.Bar`1``0')
        sig = DotNetCallable.parse_signature('Foo.Bar<T>')
        self.assertEqual(sig.full_name(), 'Foo.Bar<T>')
        sig = DotNetCallable.parse_signature('Foo.Bar<T,T>')
        self.assertEqual(sig.full_name(), 'Foo.Bar<T,T>')
        sig = DotNetCallable.parse_signature('Foo.Bar<T, T>')
        self.assertEqual(sig.full_name(), 'Foo.Bar<T, T>')
        sig = DotNetCallable.parse_signature('Foo.Bar<T,T,T>')
        self.assertEqual(sig.full_name(), 'Foo.Bar<T,T,T>')
        sig = DotNetCallable.parse_signature('Foo.Bar<TFoo,TBar>')
        self.assertEqual(sig.full_name(), 'Foo.Bar<TFoo,TBar>')
        sig = DotNetCallable.parse_signature('Foo.Bar<T,<string>>')
        self.assertEqual(sig.full_name(), 'Foo.Bar<T,<string>>')
        sig = DotNetCallable.parse_signature('Foo.Bar<T,<T,<string>>>')
        self.assertEqual(sig.full_name(), 'Foo.Bar<T,<T,<string>>>')

    def test_callable_methods(self):
        '''Callable method parsing'''
        sig = DotNetCallable.parse_signature('Foo.Bar()')
        self.assertEqual(sig.full_name(), 'Foo.Bar')
        sig = DotNetCallable.parse_signature('Foo.Bar(arg1)')
        self.assertEqual(sig.full_name(), 'Foo.Bar')
        sig = DotNetCallable.parse_signature('Foo.Bar(arg1, arg2)')
        self.assertEqual(sig.full_name(), 'Foo.Bar')
        sig = DotNetCallable.parse_signature('Foo.Bar`1(arg1, arg2)')
        self.assertEqual(sig.full_name(), 'Foo.Bar`1')
        sig = DotNetCallable.parse_signature('foobar(arg1, arg2)')
        self.assertEqual(sig.full_name(), 'foobar')

    def test_ctor(self):
        '''Class constructor methods'''
        sig = DotNetConstructor.parse_signature('Foo.Bar.#ctor')
        self.assertEqual(sig.full_name(), 'Foo.Bar.#ctor')
        sig = DotNetConstructor.parse_signature('Foo.Bar.#ctor(arg1)')
        self.assertEqual(sig.full_name(), 'Foo.Bar.#ctor')

    def test_ctor_invalid(self):
        '''Invalid class constructor methods'''
        self.assertRaises(ValueError, DotNetConstructor.parse_signature,
                          'Foo.Bar#ctor')

    def test_invalid_generic_type(self):
        '''Invalid generic types that shouldn't pass'''
        self.assertRaises(ValueError, DotNetObjectNested.parse_signature,
                          'Foo.Bar`0`1')
        self.assertRaises(ValueError, DotNetObjectNested.parse_signature,
                          'Foo.Bar<T>`0`1')
        self.assertRaises(ValueError, DotNetObjectNested.parse_signature,
                          'Foo.Bar`0`1<T>')

    @unittest.expectedFailure
    def test_generic_braces(self):
        '''Unknown generic syntax parsing with braces'''
        sig = DotNetCallable.parse_signature('Foo.Bar{`1}')
        self.assertEqual(sig.full_name(), 'Foo.Bar{`1}')

    def test_operator(self):
        '''Operator signature parsing'''
        # Implicit operator
        sig = DotNetOperator.parse_signature('Foo.implicit operator Bar(arg)')
        self.assertEqual(sig.prefix, 'Foo')
        self.assertEqual(sig.member, 'implicit operator Bar')
        raw = ('Microsoft.CodeAnalysis.Options.Option<T>.implicit operator '
               'Microsoft.CodeAnalysis.Options.OptionKey'
               '(Microsoft.CodeAnalysis.Options.Option<T>)')
        sig = DotNetOperator.parse_signature(raw)
        self.assertEqual(sig.prefix,
                         'Microsoft.CodeAnalysis.Options.Option<T>')
        self.assertEqual(sig.member,
                         ('implicit operator '
                          'Microsoft.CodeAnalysis.Options.OptionKey'))
        self.assertEqual(sig.full_name(),
                         ('Microsoft.CodeAnalysis.Options.Option<T>'
                          '.implicit operator '
                          'Microsoft.CodeAnalysis.Options.OptionKey'))
        # Other operators
        sig = DotNetOperator.parse_signature('Foo.operator <=(arg)')
        self.assertEqual(sig.member, 'operator <=')
        sig = DotNetOperator.parse_signature('Foo.operator true(arg)')
        self.assertEqual(sig.member, 'operator true')
        sig = DotNetOperator.parse_signature('Foo.operator false(arg)')
        self.assertEqual(sig.member, 'operator false')
        self.assertRaises(ValueError, DotNetOperator.parse_signature,
                          'Foo.operator foo(args)')
        self.assertRaises(ValueError, DotNetOperator.parse_signature,
                          'Foo.operator foo==(args)')
        self.assertRaises(ValueError, DotNetOperator.parse_signature,
                          'Foo.operator ==foo(args)')
        self.assertRaises(ValueError, DotNetOperator.parse_signature,
                          'Foo.operator <==>(args)')

        raw = ('Microsoft.CodeAnalysis.ProjectId.operator '
               '==(Microsoft.CodeAnalysis.ProjectId, '
               'Microsoft.CodeAnalysis.ProjectId)')
        sig = DotNetOperator.parse_signature(raw)
        self.assertEqual(sig.full_name(),
                         'Microsoft.CodeAnalysis.ProjectId.operator ==')

    def test_slow_backtrack(self):
        '''Slow query because of excessive backtracking'''
        time_start = time.time()
        sig = DotNetObjectNested.parse_signature('Microsoft.CodeAnalysis.Classification.ClassificationTypeNames.XmlDocCommentAttributeName')
        self.assertEqual(sig.prefix, 'Microsoft.CodeAnalysis.Classification.ClassificationTypeNames')
        self.assertEqual(sig.member, 'XmlDocCommentAttributeName')
        time_end = time.time()
        self.assertTrue((time_end - time_start) < 2)
