from util import SphinxTestCase


class ReferenceDefinitionTests(SphinxTestCase):
    '''Parse sphinx project, test reference definitions are generated'''

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

            .. dn:class:: ClassValid<T,T,T>

            .. dn:class:: ClassValid`1

            .. dn:class:: ClassValid`1``0

            .. dn:class:: ClassValid``0

            '''
        )
        self.assertRef('ClassValid', 'class')
        self.assertRef('ClassValid<T>', 'class')
        self.assertRef('ClassValid<T,T,T>', 'class')
        self.assertRef('ClassValid`1', 'class')
        self.assertRef('ClassValid`1``0', 'class')
        self.assertRef('ClassValid``0', 'class')

    def test_class_invalid(self):
        '''Invalid class parsing'''
        self.app._mock_build(
            '''
            .. dn:class:: Class NotValid

            .. dn:class:: ClassInvalid<T><T><T>

            .. dn:class:: ClassParens()

            .. dn:class:: ClassValid`0`1

            .. dn:class:: ClassValid`1``1```1

            '''
        )
        warnings = self.app._warning.getvalue()
        self.assertNotRef('Class', 'class')
        self.assertNotRef('Class NotValid', 'class')
        assert 'WARNING: Parsing signature failed: "Class NotValid"' in warnings
        self.assertNotRef('ClassParens', 'class')
        assert 'WARNING: Parsing signature failed: "ClassInvalid<T><T><T>"' in warnings
        self.assertNotRef('ClassInvalid<T><T><T>', 'class')
        assert 'WARNING: Parsing signature failed: "ClassParens()"' in warnings
        self.assertNotRef('ClassValid`0`1', 'class')
        assert 'WARNING: Parsing signature failed: "ClassValid`0`1"' in warnings
        self.assertNotRef('ClassValid`1``1```1', 'class')
        assert 'WARNING: Parsing signature failed: "ClassValid`1``1```1"' in warnings

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

                    .. dn:class:: SubNestedClassTwo

            '''
        )
        self.assertRef('Namespace.NestedClass', 'class')
        self.assertRef('Namespace.NestedClass.SubNestedClass', 'class')
        self.assertRef('Namespace.NestedClass.SubNestedClassTwo', 'class')

    def test_nested_constructs(self):
        '''Nested constructs besides class'''
        self.app._mock_build(
            '''
            .. dn:struct:: ValidStructure
            .. dn:interface:: ValidInterface
            .. dn:delegate:: ValidDelegate
            .. dn:enum:: ValidEnumeration

            .. dn:namespace:: ValidNamespace

                .. dn:struct:: NestedStructure
                .. dn:interface:: NestedInterface
                .. dn:delegate:: NestedDelegate
                .. dn:enum:: NestedEnumeration

            .. dn:namespace:: UnNestedNamespace

            .. dn:struct:: UnNestedNamespace.UnNestedStructure
            .. dn:interface:: UnNestedNamespace.UnNestedInterface
            .. dn:delegate:: UnNestedNamespace.UnNestedDelegate
            .. dn:enum:: UnNestedNamespace.UnNestedEnumeration
            '''
        )
        self.assertRef('ValidStructure', 'struct')
        self.assertRef('ValidNamespace.NestedStructure', 'struct')
        self.assertRef('UnNestedNamespace.UnNestedStructure', 'struct')
        self.assertRef('ValidInterface', 'interface')
        self.assertRef('ValidNamespace.NestedInterface', 'interface')
        self.assertRef('UnNestedNamespace.UnNestedInterface', 'interface')
        self.assertRef('ValidDelegate', 'delegate')
        self.assertRef('ValidNamespace.NestedDelegate', 'delegate')
        self.assertRef('UnNestedNamespace.UnNestedDelegate', 'delegate')
        self.assertRef('ValidEnumeration', 'enum')
        self.assertRef('ValidNamespace.NestedEnumeration', 'enum')
        self.assertRef('UnNestedNamespace.UnNestedEnumeration', 'enum')

    # Test callable members
    def test_method_args(self):
        '''Method args on class'''
        self.app._mock_build(
            '''
            .. dn:class:: ValidClass

                .. dn:method:: MethodNoArgs()

                .. dn:method:: MethodArg(T1)

                .. dn:method:: MethodArgs(T1, T2)

                .. dn:method:: MethodNested(List<int>, Dictionary<string,List<int>>)

            '''
        )
        self.assertRef('ValidClass.MethodNoArgs', 'method')
        self.assertRef('ValidClass.MethodArg', 'method')
        self.assertRef('ValidClass.MethodArgs', 'method')
        self.assertRef('ValidClass.MethodNested', 'method')

    def test_ctor(self):
        '''Constructor method parsing'''
        self.app._mock_build(
            '''
            .. dn:class:: ValidClass

                .. dn:constructor:: #ctor()

            .. dn:constructor:: UnNested.#ctor()

            '''
        )
        warnings = self.app._warning.getvalue()
        self.assertRef('ValidClass.#ctor', 'constructor')
        self.assertRef('UnNested.#ctor', 'constructor')

    def test_callable_constructs(self):
        '''Callable constructs on nested constructs

        Having bare properties/fields/etc on a namespace might not be valid in
        .NET, but we don't check for correctness here.
        '''
        self.app._mock_build(
            '''
            .. dn:property:: ValidProperty
            .. dn:field:: ValidField
            .. dn:event:: ValidEvent
            .. dn:operator:: ValidOperator

            .. dn:namespace:: ValidNamespace

                .. dn:property:: NestedProperty
                .. dn:field:: NestedField
                .. dn:event:: NestedEvent
                .. dn:operator:: NestedOperator

                .. dn:class:: NestedClass

                    .. dn:property:: NestedClassProperty
                    .. dn:field:: NestedClassField
                    .. dn:event:: NestedClassEvent
                    .. dn:operator:: NestedClassOperator

            '''
        )
        self.assertRef('ValidProperty', 'property')
        self.assertRef('ValidField', 'field')
        self.assertRef('ValidEvent', 'event')
        self.assertRef('ValidOperator', 'operator')
        self.assertRef('ValidNamespace.NestedProperty', 'property')
        self.assertRef('ValidNamespace.NestedField', 'field')
        self.assertRef('ValidNamespace.NestedEvent', 'event')
        self.assertRef('ValidNamespace.NestedOperator', 'operator')
        self.assertRef('ValidNamespace.NestedClass.NestedClassProperty', 'property')
        self.assertRef('ValidNamespace.NestedClass.NestedClassField', 'field')
        self.assertRef('ValidNamespace.NestedClass.NestedClassEvent', 'event')
        self.assertRef('ValidNamespace.NestedClass.NestedClassOperator', 'operator')

    def test_operator(self):
        '''Operator references'''
        self.app._mock_build(
            '''
            .. dn:class:: ValidClass

                .. dn:operator:: AnInvalidOperatorWeParseAnyways
                .. dn:operator:: op_Equal(T1, T2)
                .. dn:operator:: op_LessThanOrEqual(T1, T2)
                .. dn:operator:: op_True(T1, T2)
                .. dn:operator:: op_implicit(T1)
            '''
        )
        self.assertRef('ValidClass.AnInvalidOperatorWeParseAnyways', 'operator')
        self.assertRef('ValidClass.op_Equal', 'operator')
        self.assertRef('ValidClass.op_LessThanOrEqual', 'operator')
        self.assertRef('ValidClass.op_True', 'operator')
        self.assertRef('ValidClass.op_implicit', 'operator')

    def test_construct_options(self):
        '''Construct directive options'''
        self.app._mock_build(
            '''
            .. dn:class:: PublicClass
                :public:

            .. dn:class:: ProtectedClass
                :protected:

            .. dn:class:: StaticClass
                :static:

            .. dn:class:: NopeClass
                :nope:
            '''
        )
        self.assertIn('public PublicClass',
                      self.app.builder.output['index'])
        self.assertIn('protected ProtectedClass',
                      self.app.builder.output['index'])
        self.assertIn('static StaticClass',
                      self.app.builder.output['index'])
        self.assertIn('unknown option: "nope".',
                      self.app._warning.getvalue())

    def test_property_options(self):
        '''Property directive options'''
        self.app._mock_build(
            '''
            .. dn:property:: GetProperty
                :getter:

            .. dn:property:: SetProperty
                :setter:

            .. dn:property:: Property
                :getter:
                :setter:
            '''
        )
        self.assertRef('GetProperty', 'property')
        self.assertRef('SetProperty', 'property')
        self.assertRef('Property', 'property')
        self.assertNotIn('Property()', self.app.builder.output['index'])
        self.assertIn('Property', self.app.builder.output['index'])

    def test_field_options(self):
        '''Field directive options'''
        self.app._mock_build(
            '''
            .. dn:field:: AdderField
                :adder:

            .. dn:field:: RemoverField
                :remover:

            .. dn:field:: Field
                :adder:
                :remover:
            '''
        )
        self.assertRef('AdderField', 'field')
        self.assertRef('RemoverField', 'field')
        self.assertRef('Field', 'field')
