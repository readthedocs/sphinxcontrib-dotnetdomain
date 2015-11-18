import unittest

from util import SphinxTestCase


class XRefTests(SphinxTestCase):
    '''Cross reference parsing tests'''

    def test_basic_xref(self):
        '''Basic cross references, not nested'''
        self.app._mock_build(
            '''
            .. dn:namespace:: ValidNamespace
            .. dn:class:: ValidClass
            .. dn:struct:: ValidStructure
            .. dn:interface:: ValidInterface
            .. dn:delegate:: ValidDelegate
            .. dn:enum:: ValidEnumeration

            :dn:ns:`ValidNamespace`
            :dn:namespace:`ValidNamespace`
            :dn:cls:`ValidClass`
            :dn:class:`ValidClass`
            :dn:struct:`ValidStructure`
            :dn:structure:`ValidStructure`
            :dn:iface:`ValidInterface`
            :dn:interface:`ValidInterface`
            :dn:del:`ValidDelegate`
            :dn:delegate:`ValidDelegate`
            :dn:enum:`ValidEnumeration`
            :dn:enumeration:`ValidEnumeration`
            ''')
        self.assertXRef('ValidNamespace', obj_type='namespace',
                        obj_ref_type='namespace')
        self.assertXRef('ValidNamespace', obj_type='namespace',
                        obj_ref_type='ns')
        self.assertXRef('ValidClass', obj_type='class', obj_ref_type='class')
        self.assertXRef('ValidClass', obj_type='class', obj_ref_type='cls')
        self.assertXRef('ValidStructure', obj_type='struct',
                        obj_ref_type='struct')
        self.assertXRef('ValidStructure', obj_type='struct',
                        obj_ref_type='structure')
        self.assertXRef('ValidInterface', obj_type='interface',
                        obj_ref_type='iface')
        self.assertXRef('ValidInterface', obj_type='interface',
                        obj_ref_type='interface')
        self.assertXRef('ValidDelegate', obj_type='delegate',
                        obj_ref_type='del')
        self.assertXRef('ValidDelegate', obj_type='delegate',
                        obj_ref_type='delegate')
        self.assertXRef('ValidEnumeration', obj_type='enum',
                        obj_ref_type='enum')
        self.assertXRef('ValidEnumeration', obj_type='enum',
                        obj_ref_type='enumeration')

    def test_nested_xref(self):
        '''Cross references nested one level deep in a namespace'''
        self.app._mock_build(
            '''
            .. dn:namespace:: ValidNamespace

                * :dn:cls:`NestedClass`
                * :dn:struct:`NestedStructure`
                * :dn:iface:`NestedInterface`
                * :dn:del:`NestedDelegate`
                * :dn:enum:`NestedEnumeration`

                .. dn:class:: NestedClass
                .. dn:struct:: NestedStructure
                .. dn:interface:: NestedInterface
                .. dn:delegate:: NestedDelegate
                .. dn:enum:: NestedEnumeration
            ''')
        self.assertRef('ValidNamespace', 'namespace')

        self.assertXRef('NestedClass', prefix='ValidNamespace',
                        obj_type='class')
        self.assertXRef('NestedStructure', prefix='ValidNamespace',
                        obj_type='struct')
        self.assertXRef('NestedInterface', prefix='ValidNamespace',
                        obj_type='interface')
        self.assertXRef('NestedDelegate', prefix='ValidNamespace',
                        obj_type='delegate')
        self.assertXRef('NestedEnumeration', prefix='ValidNamespace',
                        obj_type='enum')

    def test_nested_toplevel_xref(self):
        '''Cross references nested one level deep in a namespace'''
        self.app._mock_build(
            '''
            .. dn:namespace:: ValidNamespace

                .. dn:class:: NestedClass
                .. dn:struct:: NestedStructure
                .. dn:interface:: NestedInterface
                .. dn:delegate:: NestedDelegate
                .. dn:enum:: NestedEnumeration

            * :dn:cls:`ValidNamespace.NestedClass`
            * :dn:struct:`ValidNamespace.NestedStructure`
            * :dn:iface:`ValidNamespace.NestedInterface`
            * :dn:del:`ValidNamespace.NestedDelegate`
            * :dn:enum:`ValidNamespace.NestedEnumeration`
            ''')
        self.assertRef('ValidNamespace', 'namespace')

        self.assertXRef('ValidNamespace.NestedClass', obj_type='class')
        self.assertXRef('ValidNamespace.NestedStructure', obj_type='struct')
        self.assertXRef('ValidNamespace.NestedInterface', obj_type='interface')
        self.assertXRef('ValidNamespace.NestedDelegate', obj_type='delegate')
        self.assertXRef('ValidNamespace.NestedEnumeration', obj_type='enum')

    def test_xref_long_names(self):
        '''Long name xref directives'''
        self.app._mock_build(
            '''
            .. dn:namespace:: NamespaceFoo
            .. dn:struct:: StructFoo
            .. dn:interface:: InterfaceFoo
            .. dn:delegate:: DelegateFoo
            .. dn:enum:: EnumFoo
            .. dn:class:: ClassFoo
            .. dn:method:: MethodFoo()
            .. dn:property:: PropertyFoo()
            .. dn:operator:: OperatorFoo()

            * :dn:namespace:`NamespaceFoo`
            * :dn:ns:`NamespaceFoo`
            * :dn:class:`ClassFoo`
            * :dn:interface:`InterfaceFoo`
            * :dn:delegate:`DelegateFoo`
            * :dn:method:`MethodFoo`
            * :dn:property:`PropertyFoo`
            * :dn:operator:`OperatorFoo`
            ''')

        for (type_short, type_long) in [('ns', 'namespace'),
                                        ('cls', 'class'),
                                        ('meth', 'method'),
                                        ('prop', 'property'),
                                        ('op', 'operator'),
                                        ('del', 'delegate'),
                                        ('iface', 'interface')]:
            # Lookup for long type exists
            self.assertXRef(
                '{0}Foo'.format(type_long.title()),
                #prefix='ClassFoo',
                obj_type=type_long,
                obj_ref_type=type_long
            )
            # Lookup for short type doesn't exist yet
            self.assertNoXRef(
                '{0}Foo'.format(type_long.title()),
                #prefix='ClassFoo',
                obj_type=type_short,
                obj_ref_type=type_long
            )
            # Short name xref = long name xref
            ret = self.app.env.domains['dn'].find_obj(
                self.app.env,
                None,
                '{0}Foo'.format(type_long.title()),
                type_short)
            self.assertEqual(
                ret,
                ((type_short, '{0}Foo'.format(type_long.title())),
                 ('index', type_long))
            )

    def test_xref_duplication_on_long_names(self):
        '''Long name xref directives aren't duplicates'''
        self.app._mock_build(
            '''
            .. dn:namespace:: NamespaceFoo
            .. dn:struct:: StructFoo
            .. dn:interface:: InterfaceFoo
            .. dn:delegate:: DelegateFoo
            .. dn:enum:: EnumFoo
            .. dn:class:: ClassFoo
            .. dn:method:: MethodFoo()
            .. dn:property:: PropertyFoo()
            .. dn:operator:: OperatorFoo()

            * :any:`NamespaceFoo`
            * :any:`ClassFoo`
            * :any:`InterfaceFoo`
            * :any:`DelegateFoo`
            * :any:`MethodFoo`
            * :any:`PropertyFoo`
            * :any:`OperatorFoo`
            ''')
        warnings = self.app._warning.getvalue()
        self.assertEqual(warnings, '')

    def test_class_member_xref(self):
        '''Class member cross references'''
        self.app._mock_build(
            '''
            .. dn:class:: ValidClass

                * :dn:meth:`NestedMethod`
                * :dn:prop:`NestedProperty`
                * :dn:field:`NestedField`
                * :dn:event:`NestedEvent`
                * :dn:op:`NestedOperator`

                .. dn:method:: NestedMethod
                .. dn:property:: NestedProperty
                .. dn:field:: NestedField
                .. dn:event:: NestedEvent
                .. dn:operator:: NestedOperator
            ''')
        self.assertXRef('NestedMethod', prefix='ValidClass',
                        obj_type='method')
        self.assertXRef('NestedProperty', prefix='ValidClass',
                        obj_type='property')
        self.assertXRef('NestedField', prefix='ValidClass',
                        obj_type='field')
        self.assertXRef('NestedEvent', prefix='ValidClass',
                        obj_type='event')
        self.assertXRef('NestedOperator', prefix='ValidClass',
                        obj_type='operator')

    def test_class_member_toplevel_xref(self):
        '''Class member cross references'''
        self.app._mock_build(
            '''
            .. dn:class:: ValidClass

                .. dn:method:: NestedMethod
                .. dn:property:: NestedProperty
                .. dn:field:: NestedField
                .. dn:event:: NestedEvent
                .. dn:operator:: NestedOperator

            * :dn:meth:`ValidClass.NestedMethod`
            * :dn:prop:`ValidClass.NestedProperty`
            * :dn:field:`ValidClass.NestedField`
            * :dn:event:`ValidClass.NestedEvent`
            * :dn:op:`ValidClass.NestedOperator`
            ''')
        self.assertXRef('ValidClass.NestedMethod', obj_type='method')
        self.assertXRef('ValidClass.NestedProperty', obj_type='property')
        self.assertXRef('ValidClass.NestedField', obj_type='field')
        self.assertXRef('ValidClass.NestedEvent', obj_type='event')
        self.assertXRef('ValidClass.NestedOperator', obj_type='operator')

    def test_xref_collision_methods(self):
        '''Cross reference collision on class methods

        Ensure that at least one reference is addressable
        '''
        self.app._mock_build(
            '''
            .. dn:class:: ValidClass

                :dn:meth:`NestedMethod`

                .. dn:method:: NestedMethod(arg1)
                .. dn:method:: NestedMethod(arg2)
            ''')
        self.assertXRef('NestedMethod', prefix='ValidClass',
                        obj_type='method')

    def test_xref_collision_type_difference(self):
        '''Cross reference but with type differences

        On differing types, colliding names should both be addressable.
        '''
        self.app._mock_build(
            '''
            .. dn:class:: ValidClass

                * :dn:meth:`Nested`
                * :dn:field:`Nested`
                * :dn:prop:`Nested`

                .. dn:method:: Nested()
                .. dn:field:: Nested()
                .. dn:property:: Nested()
            ''')
        self.assertXRef('Nested', prefix='ValidClass', obj_type='method')
        self.assertXRef('Nested', prefix='ValidClass', obj_type='field')
        self.assertXRef('Nested', prefix='ValidClass', obj_type='property')

    def test_xref_collision_multiple_namespaces(self):
        '''Cross reference with same name between multiple namespaces'''
        self.app._mock_build(
            '''
            .. dn:class:: ValidClassOne

                * :dn:meth:`Nested`
                * :dn:meth:`ValidClassTwo.Nested`

                .. dn:method:: Nested()

            .. dn:class:: ValidClassTwo

                * :dn:meth:`Nested`
                * :dn:meth:`ValidClassOne.Nested`

                .. dn:method:: Nested()
            ''')
        self.assertXRef('Nested', prefix='ValidClassOne',
                        obj_type='method')
        self.assertXRef('Nested', prefix='ValidClassTwo',
                        obj_type='method')
        self.assertNoXRef('ValidClassTwo.Nested', prefix='ValidClassOne',
                          obj_type='method')
        self.assertNoXRef('ValidClassOne.Nested', prefix='ValidClassTwo',
                          obj_type='method')

    def test_xref_subnested(self):
        '''Cross reference nested multiple levels'''
        self.app._mock_build(
            '''
            * :dn:meth:`Level1.Level2.Level3`

            .. dn:namespace:: Level1

                * :dn:meth:`Level2.Level3`

                .. dn:class:: Level2

                    * :dn:meth:`Level3`

                    .. dn:method:: Level3()
            ''')
        self.assertXRef('Level1.Level2.Level3', obj_type='method')
        self.assertXRef('Level2.Level3', prefix='Level1', obj_type='method')
        self.assertXRef('Level3', prefix='Level1.Level2', obj_type='method')

    def test_xref_subnested_inverted(self):
        '''Cross reference nested multiple levels referencing backwards'''
        self.app._mock_build(
            '''
            * :dn:ns:`Level1`

            .. dn:namespace:: Level1

                * :dn:ns:`Level1`

                .. dn:class:: Level2

                    * :dn:ns:`Level1`

                    .. dn:method:: Level3()

                        * :dn:ns:`Level1`
            ''')
        self.assertXRef('Level1', obj_type='namespace', ret_name='Level1')
        self.assertXRef('Level1', prefix='Level1', obj_type='namespace',
                        ret_name='Level1')
        self.assertXRef('Level1', prefix='Level1.Level2', obj_type='namespace',
                        ret_name='Level1')

    def test_xref_nested_sibling(self):
        '''Cross reference nested multiple levels referencing backwards'''
        self.app._mock_build(
            '''
            .. dn:namespace:: Level1

                * :dn:ns:`Level1Sibling`

                .. dn:class:: Level2

                    * :dn:cls:`Level2Sibling`
                    * :dn:cls:`Level1.Level2Sibling`

                    .. dn:method:: Level3()

                        * :dn:meth:`Level3Sibling`
                        * :dn:meth:`Level1.Level2.Level3Sibling`

                    .. dn:method:: Level3Sibling

                .. dn:class:: Level2Sibling

            .. dn:namespace:: Level1Sibling
            ''')
        self.assertXRef('Level1Sibling', prefix='Level1', obj_type='namespace',
                        ret_name='Level1Sibling')
        self.assertXRef('Level1.Level2Sibling', prefix='Level1.Level2',
                        obj_type='class', ret_name='Level1.Level2Sibling')
        self.assertNoXRef('Level2Sibling', prefix='Level1.Level2',
                          obj_type='class', ret_name='Level2Sibling')
        # This works because methods don't propagate new prefixes to ref_context
        self.assertXRef('Level3Sibling', prefix='Level1.Level2',
                        obj_type='method', ret_name='Level1.Level2.Level3Sibling')
        self.assertXRef('Level1.Level2.Level3Sibling', prefix='Level1.Level2',
                        obj_type='method', ret_name='Level1.Level2.Level3Sibling')

    def test_xref_generics(self):
        '''Cross reference with same name between multiple namespaces'''
        self.app._mock_build(
            '''
            .. dn:class:: GenericClass<T>
            .. dn:class:: GenericClass<T,T>
            .. dn:class:: GoofyClass<T>
            .. dn:class:: GoofyClass<T,T>
            .. dn:class:: GoofyClass<T,T,T>

            * :dn:cls:`GenericClass\<T\>`
            * :dn:cls:`GenericClass\<T,T\>`

            This is special Sphinx reference syntax, meaning reference to type
            ``T``, with text ``GoofyClass``. We'll assume this is a mistake and
            fix the reference, because escaping the generic is annoying:

            * :dn:cls:`GoofyClass<T>`
            * :dn:cls:`GoofyClass<T,T>`
            * :dn:cls:`GoofyClass<T,T,T>`
            ''')
        self.assertXRef('GenericClass<T>', obj_type='class')
        self.assertXRef('GenericClass<T,T>', obj_type='class')
        self.assertXRef('GoofyClass<T>', obj_type='class')
        self.assertXRef('GoofyClass<T,T>', obj_type='class')
        self.assertXRef('GoofyClass<T,T,T>', obj_type='class')
