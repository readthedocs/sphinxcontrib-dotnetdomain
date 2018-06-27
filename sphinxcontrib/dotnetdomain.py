"""Sphinx .NET Domain

API documentation support for .NET langauges
"""

import re
from itertools import chain

from six import iteritems

from sphinx import addnodes, version_info as sphinx_version_info
from sphinx.domains import Domain, ObjType, Index
from sphinx.locale import l_
from sphinx.directives import ObjectDescription
from sphinx.roles import AnyXRefRole
from sphinx.domains.python import _pseudo_parse_arglist
from sphinx.util.nodes import make_refnode
from sphinx.util.docfields import Field, TypedField

from docutils.parsers.rst import directives
from docutils import nodes


SPHINX_VERSION_14 = (sphinx_version_info >= (1, 4))

# Global regex parsing
_re_parts = {}
_re_parts['type_dimension'] = r'''
    (?:\`\d+)?      # non-greedy search for dimension syntax: `1
    (?:\`\`\d+)?    # non-greedy search for dimension syntax: ``1
'''
_re_parts['type_generic'] = r'''
    (?:[\<\{]                           # open bracket for generic
        (?:[\w]+|[\<\{].+?[\>\}])       # first parameter type, word or generic
        (?:,\s?                         # group of next parameters
            (?:[\w]+|[\<\{].+?[\>\}])   # parameter type, word or generic
        )*?                             # non-greedy search for unlimited groups
    [\>\}])                             # close bracket for generic
    (?![\<\{][^\>\}]+[\>\}])
'''
# Parameter types should be either a dimension or generic syntax
_re_parts['type'] = r'(?:%(type_dimension)s|%(type_generic)s)' % _re_parts
# Indexer type syntax is slightly different than generic, parse separately for a
# normal type declaration in an indexer declaration
_re_parts['type_indexer'] = r'(\[[\w\_\-\.]+?%(type)s\])?' % _re_parts
# Look for either the type declaration or and indexer declaration
_re_parts['name'] = r'[\w\_\-]+?(?:%(type)s|%(type_indexer)s)' % _re_parts


class DotNetSignature(object):

    """Signature parsing for .NET directives

    Attributes
        prefix
            Object prefix or namespace

        member
            Member name

        arguments
            List of arguments
    """

    def __init__(self, prefix=None, member=None, arguments=None):
        self.prefix = prefix
        self.member = member
        self.arguments = arguments

    def full_name(self):
        """Return full name of member"""
        if self.prefix is not None:
            return '.'.join([self.prefix, self.member])
        return self.member

    def __str__(self):
        return '.'.join([str(self.prefix), str(self.member)])


class DotNetObject(ObjectDescription):

    """Description of a .NET construct object.

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
    """

    has_arguments = False
    display_prefix = None
    class_object = False
    short_name = None
    long_name = None
    signature_pattern = None

    option_spec = dict(
        item for obj in [ObjectDescription.option_spec,
                         {'public': directives.flag,
                          'protected': directives.flag,
                          'static': directives.flag}]
        for item in obj.items())

    @classmethod
    def parse_signature(cls, signature):
        """Parse signature declartion string

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
        """
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

    def handle_signature(self, sig, signode):
        """Parses out pieces from construct signatures

        Parses out prefix and argument list from construct definition. This is
        assuming that the .NET languages this will support will be in a common
        format, such as::

            Namespace.Class.method(argument, argument, ...)

        The namespace and class will be determined by the nesting of rST
        directives.

        Returns
            Altered :py:data:`signode` with attributes corrected for rST
            nesting/etc
        """
        try:
            sig = self.parse_signature(sig.strip())
        except ValueError:
            self.env.warn(self.env.docname,
                          'Parsing signature failed: "{}"'.format(sig),
                          self.lineno)
            raise

        prefix = self.env.ref_context.get('dn:prefix', None)

        if prefix is not None:
            sig.prefix = prefix

        signode['object'] = sig.member
        signode['prefix'] = sig.prefix
        signode['fullname'] = sig.full_name()

        # Prefix modifiers
        if self.display_prefix:
            signode += addnodes.desc_annotation(self.display_prefix,
                                                self.display_prefix)
        for prefix in ['public', 'protected', 'static']:
            if prefix in self.options:
                signode += addnodes.desc_annotation(prefix + ' ',
                                                    prefix + ' ')

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

    def add_target_and_index(self, name, sig, signode):
        """Add objects to the domain list of objects

        This uses the directive short name along with the full object name to
        create objects and nodes that are type and name unique.
        """
        full_name = name[0]
        target_name = '{0}-{1}'.format(self.short_name, full_name)
        if target_name not in self.state.document.ids:
            signode['names'].append(target_name)
            signode['ids'].append(target_name)
            signode['first'] = not self.names
            self.state.document.note_explicit_target(signode)

            # Update domain objects
            objects = self.env.domaindata['dn']['objects']
            try:
                found_obj = objects[full_name]
                (found_doc, found_type) = found_obj
                self.state_machine.reporter.warning(
                    ('duplicate object definition of {obj_type} {obj_name}'
                     'other instance in {path}'
                     .format(obj_type=found_type, obj_name=full_name,
                             path=self.env.doc2path(found_doc))),
                    line=self.lineno)
            except KeyError:
                pass
            finally:
                objects[full_name] = (self.env.docname, self.objtype)

        index_text = self.get_index_text(None, name)
        if index_text:
            entry = ('single', index_text, full_name, '')
            if SPHINX_VERSION_14:
                entry = ('single', index_text, full_name, '', None)
            self.indexnode['entries'].append(entry)

    def get_index_text(self, prefix, name_obj):
        """Produce index text by directive attributes"""
        (name, _) = name_obj
        msg = '{name} ({obj_type})'
        parts = {
            'name': name,
            'prefix': prefix,
            'obj_type': self.long_name,
        }
        try:
            (obj_ns, obj_name) = name.rsplit('.', 1)
            parts['name'] = obj_name
            parts['namespace'] = obj_ns
            msg = '{name} ({namespace} {obj_type})'
        except ValueError:
            pass

        return msg.format(**parts)

    @classmethod
    def get_type(cls):
        return ObjType(l_(cls.long_name), cls.short_name, cls.long_name, 'obj')


class DotNetObjectNested(DotNetObject):

    """Nestable object"""

    option_spec = dict(
        item for obj in [DotNetObject.option_spec,
                         {'hidden': directives.flag}]
        for item in obj.items())

    signature_pattern = r'''
        ^(?:(?P<prefix>.+)\.)?
        (?P<member>%(name)s)$
    ''' % _re_parts

    def run(self):
        """If element is considered hidden, drop the desc_signature node

        The default handling of signatures by :py:cls:`ObjectDescription`
        returns a list of nodes with the signature nodes. We are going to remove
        them if this is a hidden declaration.
        """
        nodes = super(DotNetObjectNested, self).run()
        if 'hidden' in self.options:
            for node in nodes:
                if isinstance(node, addnodes.desc):
                    for (m, child) in enumerate(node.children):
                        if isinstance(child, addnodes.desc_signature):
                            node.children.pop(m)
        return nodes

    def before_content(self):
        """Build up prefix history for nested elements

        The following keys are used in :py:attr:`self.env.ref_context`:

            dn:prefixes
                Stores the prefix history. With each nested element, we add the
                prefix to a list of prefixes. When we exit that object's nesting
                level, :py:meth:`after_content` is triggered and the prefix is
                removed from the end of the list.

            dn:prefix
                Current prefix. This should reflect the last element in the
                prefix history
        """
        super(DotNetObjectNested, self).before_content()
        if self.names:
            (_, prefix) = self.names.pop()
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


class DotNetXRefMixin(object):

    """Add .NET handling for `.` and `~` reference operators"""

    nested_pattern = re.compile(r'^(?P<parent>[^{]+?)\{(?P<inner>.+)\}$')
    alias_pattern = re.compile(r'^(?P<target>[^{]+?)\<(?P<alias>.+)\>$')

    def split_refs(self, target):

        def alias_target(ref):
            found = self.alias_pattern.match(ref)
            if found:
                return (found.group('target'), found.group('alias'))
            return (ref, None)

        refs = []
        current = target
        while True:
            found = self.nested_pattern.match(current)
            if not found:
                refs.append(alias_target(current))
                break
            current = found.group('inner')
            refs.append(alias_target(found.group('parent')))
        return refs

    def make_xref(self, rolename, domain, target_name,
                  innernode=nodes.emphasis, contnode=None):
        if not rolename:
            return contnode or innernode(target_name, target_name)

        field_node = None
        refs = self.split_refs(target_name)
        refs.reverse()
        for (target_name_, target_alias) in refs:
            if not target_alias and target_name_.startswith(('.', '~')):
                prefix, target_name_ = target_name_[0], target_name_[1:]
                if prefix == '.':
                    target_alias = target_name_[1:]
                elif prefix == '~':
                    target_alias = target_name_.split('.')[-1]
            if target_alias is None:
                target_alias = target_name_
            ref_node = addnodes.pending_xref(
                '',
                refdomain=domain,
                refexplicit=False,
                reftype=rolename,
                reftarget=target_alias,
                refspecific=True,
            )
            ref_node += nodes.Text(target_name_, target_name_)
            if field_node is None:
                field_node = nodes.inline()
                field_node += ref_node
            else:
                inner_node = field_node
                field_node = nodes.inline()
                field_node += [
                    ref_node,
                    nodes.Text('<', '<'),
                    inner_node,
                    nodes.Text('>', '>'),
                ]

        return innernode('', '', field_node)


class DotNetBasicField(DotNetXRefMixin, Field):
    pass


class DotNetTypedField(DotNetXRefMixin, TypedField):
    pass


class DotNetCallable(DotNetObject):

    """An object that is callable with arguments"""

    has_arguments = True
    doc_field_types = [
        DotNetTypedField('arguments', label=l_('Arguments'),
                         names=('argument', 'arg', 'parameter', 'param'),
                         typerolename='obj', typenames=('paramtype', 'type'),
                         can_collapse=True),
        Field('returnvalue', label=l_('Returns'), has_arg=False,
              names=('returns', 'return')),
        DotNetBasicField('returntype', label=l_('Return type'), has_arg=False,
                         names=('rtype',), bodyrolename='obj'),
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
    display_prefix = 'struct '


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
    display_prefix = 'enum '


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
        (?P<member>(?:\#ctor|%(name)s))
        (?:\((?P<arguments>[^)]*)\))?$
    ''' % _re_parts


class DotNetProperty(DotNetCallable):

    """Property object definition

    Properties can be defined with the following options:

        getter
            Property has a getter

        setter
            Property has a setter

    For example::

        .. dn:property:: Example()
            :getter:
    """

    class_object = True
    short_name = 'prop'
    long_name = 'property'
    has_arguments = False

    option_spec = dict(
        item for obj in [DotNetCallable.option_spec,
                         {'getter': directives.flag,
                          'setter': directives.flag}]
        for item in obj.items())


class DotNetField(DotNetCallable):

    """Field object definition

    Fields can be defined with the following options:

        adder
            Field adder

        remover
            Field remover

    For example::

        .. dn:field:: Example
            :adder:
            :remover:
    """

    class_object = True
    short_name = 'field'
    long_name = 'field'

    option_spec = dict(
        item for obj in [DotNetCallable.option_spec,
                         {'adder': directives.flag,
                          'remover': directives.flag}]
        for item in obj.items())


class DotNetEvent(DotNetCallable):
    class_object = True
    short_name = 'event'
    long_name = 'event'


class DotNetOperator(DotNetCallable):

    class_object = True
    short_name = 'op'
    long_name = 'operator'


# Cross referencing
class DotNetXRefRole(AnyXRefRole):

    """XRef role to handle special .NET cases"""

    def __init__(self, *args, **kwargs):
        super(DotNetXRefRole, self).__init__(*args, **kwargs)

    def process_link(self, env, refnode, has_explicit_title, title, target):
        """This handles some special cases for reference links in .NET

        First, the standard Sphinx reference syntax of ``:ref:`Title<Link>```,
        where a reference to ``Link`` is created with title ``Title``, causes
        problems for the generic .NET syntax of ``:dn:cls:`FooBar<T>```. So, here
        we assume that ``<T>`` was the generic declaration, and fix the
        reference.

        This also uses :py:cls:`AnyXRefRole` to add `ref_context` onto the
        refnode. Add data there that you need it on refnodes.

        This method also resolves special reference operators ``~`` and ``.``
        """
        result = super(DotNetXRefRole, self).process_link(env, refnode,
                                                          has_explicit_title,
                                                          title, target)
        (title, target) = result
        if not has_explicit_title:
            # If the first character is a tilde, don't display the parent name
            title = title.lstrip('.')
            target = target.lstrip('~')
            if title[0:1] == '~':
                title = title[1:]
                dot = title.rfind('.')
                if dot != -1:
                    title = title[dot + 1:]
        else:
            if title != target:
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

    """Index subclass to provide the .NET module index"""

    name = 'modindex'
    localname = l_('.NET Module Index')
    shortname = l_('.NET modules')

    def generate(self, docnames=None):
        content = {}
        objects = sorted(self.domain.data['objects'].items(),
                         key=lambda x: x[1][0].lower())
        for obj_name, (obj_doc_name, obj_type) in objects:
            if docnames and obj_doc_name not in docnames:
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
        content = sorted(content.items())
        return content, False


class DotNetDomain(Domain):

    """.NET language domain."""

    name = 'dn'
    label = '.NET'

    object_types = dict((cls.long_name, cls.get_type())
                        for cls in _domain_types)
    directives = dict(chain(
        ((cls.long_name, cls) for cls in _domain_types),
        ((cls.short_name, cls) for cls in _domain_types),
    ))
    roles = dict(chain(
        ((cls.short_name, DotNetXRefRole())
         for cls in _domain_types),
        ((cls.long_name, DotNetXRefRole())
         for cls in _domain_types),
        ((extra_key, DotNetXRefRole())
         for extra_key in ['obj'])
    ))

    initial_data = {
        'objects': {},  # fullname -> (docname, obj_type)
    }

    indices = [
        DotNetIndex,
    ]

    def __init__(self, *args, **kwargs):
        super(DotNetDomain, self).__init__(*args, **kwargs)
        self._role2type = {}
        name_mapping = dict((cls.long_name, cls.short_name)
                            for cls in _domain_types)
        for name, obj in iteritems(self.object_types):
            for role in obj.roles:
                if name in name_mapping:
                    (self._role2type
                     .setdefault(role, [])
                     .append(name_mapping[name]))
                self._role2type.setdefault(role, []).append(name)
        self.objtypes_for_role = self._role2type.get

    def clear_doc(self, docname):
        objects = list(self.data['objects'].items())
        for obj_name, (obj_doc_name, _) in objects:
            if docname == obj_doc_name:
                del self.data['objects'][obj_name]

    def find_obj(self, env, prefix, name, obj_type, searchorder=0):
        """Find object reference

        :param env: Build environment
        :param prefix: Object prefix
        :param name: Object name
        :param obj_type: Object type
        :param searchorder: Search for exact match
        """
        # Skip parens
        if name[-2:] == '()':
            name = name[:-2]

        if not name:
            return []

        object_types = list(self.object_types)
        if obj_type is not None:
            object_types = self.objtypes_for_role(obj_type)

        objects = self.data['objects']
        newname = None
        fullname = name
        if prefix is not None:
            fullname = '.'.join([prefix, name])

        if searchorder == 1:
            if prefix and fullname in objects and objects[fullname][1] in object_types:
                newname = fullname
            elif name in objects and objects[name][1] in object_types:
                newname = name
            else:
                try:
                    matches = [obj_name for obj_name in objects
                               if obj_name.endswith('.' + name)]
                    newname = matches.pop()
                except IndexError:
                    pass
        else:
            if name in objects:
                newname = name
            elif prefix and fullname in objects:
                newname = fullname

        if newname is None:
            return None
        return newname, objects.get(newname, (None, None))

    def resolve_xref(self, env, doc, builder, obj_type, target, node,
                     contnode):
        prefix = node.get('dn:prefix')
        searchorder = node.hasattr('refspecific') and 1 or 0

        found = self.find_obj(env, prefix, target, obj_type, searchorder)
        try:
            # pylint: disable=unbalanced-tuple-unpacking
            obj_name, obj = found
            (obj_doc_name, obj_type) = obj
            if obj_name is None or obj_doc_name is None:
                return None
            return make_refnode(builder, doc, obj_doc_name, obj_name, contnode,
                                obj_name)
        except (TypeError, ValueError):
            return None

    def resolve_any_xref(self, env, doc, builder, target, node, contnode):
        """Look for any references, without object type

        This always searches in "refspecific" mode
        """
        prefix = node.get('dn:prefix')
        results = []

        match = self.find_obj(env, prefix, target, None, 1)
        if match is not None:
            (name, obj) = match
            results.append(('dn:' + self.role_for_objtype(obj[1]),
                            make_refnode(builder, doc, obj[0], name, contnode,
                                         name)))
        return results

    def get_objects(self):
        for obj_name, (obj_doc, obj_doc_type) in self.data['objects'].items():
            obj_long_type = self.directives[obj_doc_type].long_name
            yield obj_name, obj_name, obj_long_type, obj_doc, obj_name, 1


def setup(app):
    app.add_domain(DotNetDomain)
