import unittest

from sphinxcontrib.dotnetdomain import DotNetXRefMixin


class FieldTests(unittest.TestCase):

    """Test for xref fields"""

    def test_split(self):
        cls = DotNetXRefMixin()
        self.assertEqual(
            cls.split_refs('TFoo'),
            [('TFoo', None)]
        )
        self.assertEqual(
            cls.split_refs('Foo<Foo`1>'),
            [('Foo', 'Foo`1')]
        )
        self.assertEqual(
            cls.split_refs('Foo<Foo`1>{Bar<Bar`1>}'),
            [('Foo', 'Foo`1'), ('Bar', 'Bar`1')]
        )
        self.assertEqual(
            cls.split_refs('Foo`1<Foo>{Bar`1<Bar>}'),
            [('Foo`1', 'Foo'), ('Bar`1', 'Bar')]
        )
        self.assertEqual(
            cls.split_refs('Foo`1<Foo>{Bar`1<Bar>{TFoo}}'),
            [('Foo`1', 'Foo'), ('Bar`1', 'Bar'), ('TFoo', None)]
        )
