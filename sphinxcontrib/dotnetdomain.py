'''Sphinx .NET Domain

API documentation support for .NET langauges
'''

import re

from sphinx import addnodes
from sphinx.domains import Domain, ObjType, Index
from sphinx.locale import l_
from sphinx.directives import ObjectDescription
from sphinx.roles import AnyXRefRole
from sphinx.domains.python import _pseudo_parse_arglist
from sphinx.util.nodes import make_refnode
from sphinx.util.docfields import Field, TypedField

from docutils.parsers.rst import directives


# Global regex parsing
_re_parts = {}
_re_parts['type_dimension'] = r'(?:\`\d+)?(?:\`\`\d+)?'
_re_parts['type_generic'] = r'(?:\<T[0-9]?\>)+'
_re_parts['type'] = r'(?:%(type_dimension)s|%(type_generic)s)' % _re_parts
_re_parts['name'] = r'[\w\_\-]+?%(type)s' % _re_parts


class DotNetSignature(object):

    '''Signature parsing for .NET directives

    Attributes
        prefix
            Object prefix or namespace

        member
            Member name

        arguments
            List of arguments
    '''

    def __init__(self, prefix=None, member=None, arguments=None):
        self.prefix = prefix
        self.member = member
        self.arguments = arguments

    def full_name(self):
        '''Return full name of member'''
        if self.prefix is not None:
            return '.'.join([self.prefix, self.member])
        return self.member

    def prefix(self, prefix):
        '''Return prefix of object, compared to input prefix

        :param prefix: object prefix to compare against
        '''
        # TODO finish this
        pass

    def __str__(self):
        return '.'.join([str(self.prefix), str(self.member)])


class DotNetObject(ObjectDescription):
    '''Description of a .NET construct object.

    Class variables
    ---------------

        has_arguments
            If set to ``True`` this object is callable and a
            `desc_parameterlist` is added

        display_prefix
            What is displayed right before the documentation entry

        class_object
            TODO

        short_name
            Short cross reference name for object

        long_name
            Long cross reference and indexed data name for object
    '''

    has_arguments = False
    display_prefix = None
    class_object = False
    short_name = None
    long_name = None
    signature_pattern = None

    @classmethod
    def parse_signature(cls, signature):
        '''Parse signature declartion string

        Uses :py:attr:`signature_pattern` to parse out pieces of constraint
        signatures. Pattern should provide the following named groups:

            prefix
                Object prefix, such as a namespace

            member
                Object member name

            arguments
                Declaration arguments, if this is a callable constraint

        :param signature: construct signature
        :type signature: string
        '''
        assert cls.signature_pattern is not None
        pattern = re.compile(cls.signature_pattern, re.VERBOSE)
        match = pattern.match(signature)
        if match:
            groups = match.groupdict()
            arguments = None
            if 'arguments' in groups and groups['arguments'] is not None:
                arguments = re.split(r'\,\s+', groups['arguments'])
            return DotNetSignature(
                prefix=groups.get('prefix', None),
                member=groups.get('member', None),
                arguments=arguments
            )
        raise ValueError('Could not parse signature: {0}'.format(signature))

    def handle_signature(self, sig_input, signode):
        '''Parses out pieces from construct signatures

        Parses out prefix and argument list from construct definition. This is
        assuming that the .NET languages this will support will be in a common
        format, such as::

            Namespace.Class.method(argument, argument, ...)

        The namespace and class will be determined by the nesting of rST
        directives.

        Returns
            Altered :py:data:`signode` with attributes corrected for rST
            nesting/etc
        '''
        try:
            sig = self.parse_signature(sig_input.strip())
        except ValueError:
            self.env.warn(self.env.docname,
                          'Parsing signature failed: "{}"'.format(sig_input),
                          self.lineno)
            raise

        prefix = self.env.ref_context.get('dn:prefix', None)

        if prefix is not None:
            sig.prefix = prefix

        signode['object'] = sig.member
        signode['prefix'] = sig.prefix
        signode['fullname'] = sig.full_name()

        if self.display_prefix:
            signode += addnodes.desc_annotation(self.display_prefix,
                                                self.display_prefix)

        # Show prefix only on shorter declarations
        if sig.prefix is not None and not self.has_arguments:
            signode += addnodes.desc_addname(sig.prefix + '.', sig.prefix + '.')

        signode += addnodes.desc_name(sig.member, sig.member)
        if self.has_arguments:
            if not sig.arguments:
                signode += addnodes.desc_parameterlist()
            else:
                # TODO replace this
                _pseudo_parse_arglist(signode, ', '.join(sig.arguments))

        if isinstance(self, DotNetObjectNested):
            return sig.full_name(), sig.full_name()
        return sig.full_name(), sig.prefix

    def add_target_and_index(self, name_obj, sig, signode):
        '''Add objects to the domain list of objects

        This uses the directive short name along with the full object name to
        create objects and nodes that are type and name unique.
        '''
        obj_name = self.options.get('object',
                                    self.env.ref_context.get('dn:object'))
        full_name = name_obj[0]
        target_name = '{0}-{1}'.format(self.short_name, full_name)
        if target_name not in self.state.document.ids:
            signode['names'].append(target_name)
            signode['ids'].append(target_name)
            signode['first'] = not self.names
            self.state.document.note_explicit_target(signode)

            # Update domain objects
            objects = self.env.domaindata['dn']['objects']
            try:
                found_obj = objects[self.short_name, full_name]
                (found_doc, _) = found_obj
                self.state_machine.reporter.warning(
                    ('duplicate object definition of {obj_type} {obj_name}'
                     'other instance in {path}'
                     .format(obj_type=self.short_name, obj_name=full_name,
                             path=self.env.doc2path(found_doc))),
                    line=self.lineno)
            except KeyError:
                pass
            finally:
                objects[self.short_name, full_name] = (self.env.docname,
                                                       self.objtype)

        index_text = self.get_index_text(obj_name, name_obj)
        if index_text:
            self.indexnode['entries'].append(('single', index_text, full_name,
                                              ''))

    def get_index_text(self, obj_name, name_obj):
        '''Produce index text by directive attributes'''
        (name, _) = name_obj
        return '{obj_name} ({name} {obj_type})'.format(
            obj_name=obj_name, name=name, obj_type=self.long_name)

    @classmethod
    def get_type(cls):
        return ObjType(l_(cls.long_name), cls.short_name)


class DotNetObjectNested(DotNetObject):
    '''Nestable object'''

    option_spec = {
        'noindex': directives.flag,
        'hidden': directives.flag,
    }

    signature_pattern = r'''
        ^(?:(?P<prefix>.+)\.)?
        (?P<member>%(name)s)$
    ''' % _re_parts

    def run(self):
        '''If element is considered hidden, drop the desc_signature node

        The default handling of signatures by :py:cls:`ObjectDescription`
        returns a list of nodes with the signature nodes. We are going to remove
        them if this is a hidden declaration.
        '''
        nodes = super(DotNetObjectNested, self).run()
        if 'hidden' in self.options:
            for node in nodes:
                if isinstance(node, addnodes.desc):
                    for (m, child) in enumerate(node.children):
                        if isinstance(child, addnodes.desc_signature):
                            _ = node.children.pop(m)
        return nodes

    def before_content(self):
        '''Build up prefix history for nested elements

        The following keys are used in :py:attr:`self.env.ref_context`:

            dn:prefixes
                Stores the prefix history. With each nested element, we add the
                prefix to a list of prefixes. When we exit that object's nesting
                level, :py:meth:`after_content` is triggered and the prefix is
                removed from the end of the list.

            dn:prefix
                Current prefix. This should reflect the last element in the
                prefix history
        '''
        super(DotNetObjectNested, self).before_content()
        if self.names:
            (parent, prefix) = self.names.pop()
            try:
                self.env.ref_context['dn:prefixes'].append(prefix)
            except (AttributeError, KeyError):
                self.env.ref_context['dn:prefixes'] = [prefix]
            finally:
                self.env.ref_context['dn:prefix'] = prefix

    def after_content(self):
        super(DotNetObjectNested, self).after_content()
        try:
            self.env.ref_context['dn:prefixes'].pop()
            prefix = self.env.ref_context['dn:prefixes'][-1]
            self.env.ref_context['dn:prefix'] = prefix
        except (KeyError, IndexError):
            self.env.ref_context['dn:prefixes'] = []
            self.env.ref_context['dn:prefix'] = None


class DotNetCallable(DotNetObject):

    '''An object that is callable with arguments'''
    has_arguments = True
    doc_field_types = [
        TypedField('arguments', label=l_('Arguments'),
                   names=('argument', 'arg', 'parameter', 'param'),
                   typerolename='func', typenames=('paramtype', 'type')),
        Field('returnvalue', label=l_('Returns'), has_arg=False,
              names=('returns', 'return')),
        Field('returntype', label=l_('Return type'), has_arg=False,
              names=('rtype',)),
    ]

    signature_pattern = r'''
        ^(?:(?P<prefix>.+)\.)?
        (?P<member>%(name)s)
        (?:\((?P<arguments>[^)]*)\))?$
    ''' % _re_parts

# Types
class DotNetNamespace(DotNetObjectNested):
    short_name = 'ns'
    long_name = 'namespace'
    display_prefix = 'namespace '


class DotNetClass(DotNetObjectNested):
    short_name = 'cls'
    long_name = 'class'
    display_prefix = 'class '


class DotNetStructure(DotNetObjectNested):
    short_name = 'struct'
    long_name = 'structure'
    display_prefix = 'structure '


class DotNetInterface(DotNetObjectNested):
    short_name = 'iface'
    long_name = 'interface'
    display_prefix = 'interface '


class DotNetDelegate(DotNetObjectNested):
    short_name = 'del'
    long_name = 'delegate'
    display_prefix = 'delegate '


class DotNetEnumeration(DotNetObjectNested):
    short_name = 'enum'
    long_name = 'enumeration'
    display_prefix = 'enumeration '


# Members
class DotNetMethod(DotNetCallable):
    class_object = True
    short_name = 'meth'
    long_name = 'method'


class DotNetConstructor(DotNetCallable):
    class_object = True
    short_name = 'ctor'
    long_name = 'constructor'
    signature_pattern = r'''
        ^(?:(?P<prefix>.+)\.)?
        (?P<member>\#ctor)
        (?:\((?P<arguments>[^)]*)\))?$
    ''' % _re_parts


class DotNetProperty(DotNetCallable):
    class_object = True
    short_name = 'prop'
    long_name = 'property'


class DotNetField(DotNetCallable):
    class_object = True
    short_name = 'field'
    long_name = 'field'


class DotNetEvent(DotNetCallable):
    class_object = True
    short_name = 'event'
    long_name = 'event'


class DotNetOperator(DotNetCallable):
    '''Operator object with special parsing

    Parses out signatures that match several cases:

        Prefix.operator ==(args)
        Prefix.operator true(args)
        Prefix.operator false(args)
            This is parsed out with respect to overloadable operators, found at:
            <https://msdn.microsoft.com/en-us/library/8edha89s.aspx>. We won't
            list the operators we are searching for here, rather just expect
            1-3 non-word characters.

        Prefix.implicit operator Prefix.Type(args)
            Implicit operators specify return type in the declaration, which we
            don't do anything here but use for the reference. Separate return
            type is expected as well.
    '''

    class_object = True
    short_name = 'op'
    long_name = 'operator'
    signature_pattern = r'''
        ^(?:(?P<prefix>\S+?)\.)?
        (?P<member>(?:
            (?:implicit\soperator\s(?:\S+\.)?)?%(name)s |
            operator\s(?:true|false|\W{1,3})
        ))
        (?:\((?P<arguments>[^)]*)\))?$
    ''' % _re_parts


# Cross referencing
class DotNetXRefRole(AnyXRefRole):
    '''XRef role to handle special .NET cases'''

    # So, this is silly, because FooBar<T><T> links to `T><T`, and so on.
    generic_pattern = re.compile(r'^T(?:\>\<T)*$')

    def process_link(self, env, refnode, has_explicit_title, title, target):
        '''This handles some special cases for reference links in .NET

        First, the standard Sphinx reference syntax of ``:ref:`Title<Link>```,
        where a reference to ``Link`` is created with title ``Title``, causes
        problems for the generic .NET syntax of ``:dn:cls:`FooBar<T>```. So, here
        we assume that ``<T>`` was the generic declaration, and fix the
        reference.

        This also uses :py:cls:`AnyXRefRole` to add `ref_context` onto the
        refnode. Add data there that you need it on refnodes.
        '''
        super(DotNetXRefRole, self).process_link(env, refnode,
                                                 has_explicit_title, title,
                                                 target)
        # Fix generic references that are accidentally titled references
        if self.generic_pattern.match(target):
            target = title = '{title}<{target}>'.format(title=title,
                                                        target=target)
        return title, target


_domain_types = [
    DotNetNamespace,
    DotNetClass,
    DotNetStructure,
    DotNetInterface,
    DotNetDelegate,
    DotNetEnumeration,

    DotNetMethod,
    DotNetProperty,
    DotNetConstructor,
    DotNetField,
    DotNetEvent,
    DotNetOperator,
]


class DotNetIndex(Index):
    """
    Index subclass to provide the .NET module index.
    """

    name = 'modindex'
    localname = l_('.NET Module Index')
    shortname = l_('.NET modules')

    def generate(self, doc_names=None):
        content = {}
        objects = sorted(self.domain.data['objects'].iteritems(),
                         key=lambda x: x[1].lower())
        for (obj_type, obj_name), (obj_doc_name, _) in objects:
            if doc_names and obj_doc_name not in doc_names:
                continue
            if obj_type != 'namespace':
                continue

            letter = obj_name.split('.')[-1][0]
            entries = content.setdefault(letter.lower(), [])

            subtype = 0
            qualifier = ''
            synopysis = ''
            extra = ''
            anchor = obj_name

            entries.append([
                obj_name,  # name
                subtype,  # subtype
                'autoapi/' + '/'.join(obj_name.split('.')) + '/index',  # docname
                anchor,
                extra,
                qualifier,
                synopysis,
            ])

        # sort by first letter
        content = sorted(content.iteritems())
        return content, False


class DotNetDomain(Domain):

    '''.NET language domain.'''

    name = 'dn'
    label = '.NET'

    object_types = dict((cls.long_name, cls.get_type())
                        for cls in _domain_types)
    directives = dict((cls.long_name, cls)
                      for cls in _domain_types)
    roles = dict((cls.short_name, DotNetXRefRole())
                 for cls in _domain_types)

    initial_data = {
        'objects': {},  # (ref_type, fullname) -> (docname, obj_type)
    }

    indices = [
        DotNetIndex,
    ]

    def clear_doc(self, doc_name):
        for (obj_type, obj_name), (obj_doc_name, _) in self.data['objects'].items():
            if doc_name  == obj_doc_name:
                del self.data['objects'][obj_type, obj_name]

    def find_obj(self, env, prefix, name, obj_type, searchorder=0):
        '''Find object reference

        :param env: Build environment
        :param prefix: Object prefix
        :param name: Object name
        :param obj_type: Object type
        :param searchorder: Search for exact match
        '''
        # Skip parens
        if name[-2:] == '()':
            name = name[:-2]

        if not name:
            return []

        objects = self.data['objects']
        newname = None
        if prefix is not None:
            fullname = '.'.join([prefix, name])

        if searchorder == 1:
            if prefix and (obj_type, fullname) in objects:
                newname = fullname
            else:
                newname = name
        else:
            if (obj_type, name) in objects:
                newname = name
            elif prefix and (obj_type, fullname) in objects:
                newname = fullname

        return (obj_type, newname), objects.get((obj_type, newname),
                                                (None, None))

    def resolve_xref(self, env, doc, builder, obj_type, target, node,
                     contnode):
        prefix = node.get('dn:prefix')
        searchorder = node.hasattr('refspecific') and 1 or 0

        (obj_type, obj_name), obj = self.find_obj(env, prefix, target, obj_type,
                                                  searchorder)
        try:
            (obj_doc_name,) = obj
        except (TypeError, ValueError):
            return None
        return make_refnode(builder, doc, obj_doc_name, obj_name, contnode,
                            obj_name)

    def get_objects(self):
        for (obj_type, obj_name), (obj_doc,) in self.data['objects'].iteritems():
            obj_short_type = self.directives[obj_type].short_name
            yield obj_name, obj_name, obj_short_type, obj_doc, obj_name, 1


def setup(app):
    app.add_domain(DotNetDomain)
