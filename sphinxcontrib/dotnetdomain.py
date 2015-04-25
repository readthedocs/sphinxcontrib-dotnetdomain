'''Sphinx .NET Domain

API documentation support for .NET langauges
'''

import re

from sphinx import addnodes
from sphinx.domains import Domain, ObjType, Index
from sphinx.locale import l_, _
from sphinx.directives import ObjectDescription
from sphinx.roles import XRefRole
from sphinx.domains.python import _pseudo_parse_arglist
from sphinx.util.nodes import make_refnode
from sphinx.util.docfields import Field, TypedField

from docutils.parsers.rst import directives


# Global regex parsing
_re_parts = {}
_re_parts['type'] = r'(?:[\`]{1,2}[0-9]+|\<T[0-9]?\>)?'
_re_parts['name'] = r'[\w\_\-]+?%(type)s' % _re_parts
_re_intermediate = (
    r'''
        ^(?:(?P<prefix>.+)\.)?
        (?P<member>%(name)s)
        (?:\((?P<arguments>[^)]+)\))?$
    ''' % _re_parts)
_re_signature = re.compile(_re_intermediate, re.VERBOSE)


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

    @classmethod
    def from_string(cls, signature):
        '''Create signature objects from string definition

        :param signature: construct definition
        :type signature: string
        '''
        match = _re_signature.match(signature)
        if match:
            arg_string = match.group('arguments')
            arguments = None
            if arg_string:
                arguments = re.split(r'\,\s+', arg_string)
            return cls(
                prefix=match.group('prefix'),
                member=match.group('member'),
                arguments=arguments
            )
        raise ValueError('Could not parse signature: {0}'.format(signature))

    def full_name(self):
        '''Return full name of member'''
        if self.prefix is not None:
            return '.'.join([self.prefix, self.member])
        return self.member

    def prefix(self, prefix):
        '''Return prefix of object, compared to input prefix

        :param prefix: object prefix to compare against
        '''
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
            sig = DotNetSignature.from_string(sig_input.strip())
        except ValueError:
            self.env.warn(self.env.docname,
                          'Parsing signature failed: "{}"'.format(sig_input),
                          self.lineno)
            raise

        prefix = self.env.temp_data.get('dn:prefix', None)

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
        # TODO wtf does this do?
        objectname = self.options.get(
            'object', self.env.temp_data.get('dn:object'))
        fullname = name_obj[0]
        if fullname not in self.state.document.ids:
            signode['names'].append(fullname)
            signode['ids'].append(fullname.replace('$', '_S_'))
            signode['first'] = not self.names
            self.state.document.note_explicit_target(signode)
            objects = self.env.domaindata['dn']['objects']
            if fullname in objects:
                self.state_machine.reporter.warning(
                    'duplicate object description of %s, ' % fullname +
                    'other instance in ' +
                    self.env.doc2path(objects[fullname][0]),
                    line=self.lineno)
            objects[fullname] = self.env.docname, self.objtype

        indextext = self.get_index_text(objectname, name_obj)
        if indextext:
            self.indexnode['entries'].append(('single', indextext,
                                              fullname.replace('$', '_S_'),
                                              ''))

    def get_index_text(self, objectname, name_obj):
        # TODO this should inspect classes, not this objtype nonsense
        name, obj = name_obj
        if self.objtype == 'function':
            if not obj:
                return _('%s() (built-in function)') % name
            return _('%s() (%s method)') % (name, obj)
        elif self.objtype == 'namespace':
            return _('%s (package)') % name
        elif self.objtype == 'data':
            return _('%s (global variable or constant)') % name
        elif self.objtype == 'attribute':
            return _('%s (%s attribute)') % (name, obj)
        return ''

    @classmethod
    def get_type(cls):
        return ObjType(l_(cls.long_name), cls.short_name)


class DotNetObjectNested(DotNetObject):
    '''Nestable object'''

    prefix_set = False
    option_spec = {
        'noindex': directives.flag,
        'hidden': directives.flag,
    }

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
        '''Build up prefix with nested elements'''
        super(DotNetObjectNested, self).before_content()
        if self.names:
            (parent, prefix) = self.names.pop()
            self.env.temp_data['dn:prefix'] = prefix
            self.prefix_set = True

    def after_content(self):
        super(DotNetObjectNested, self).after_content()
        if self.prefix_set:
            self.env.temp_data['dn:prefix'] = None


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
    class_object = True
    short_name = 'op'
    long_name = 'operator'


# Cross referencing
class DotNetXRefRole(XRefRole):

    def process_link(self, env, refnode, has_explicit_title, title, target):
        refnode['dn:object'] = env.temp_data.get('dn:object')
        refnode['dn:prefix'] = env.temp_data.get('dn:prefix')
        if not has_explicit_title:
            title = title.lstrip('.')
            # TODO tilde?
            target = target.lstrip('~')
            if title[0:1] == '~':
                title = title[1:]
                dot = title.rfind('.')
                if dot != -1:
                    title = title[dot + 1:]
        if target[0:1] == '.':
            target = target[1:]
            refnode['refspecific'] = True
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
    localname = l_('.Net Module Index')
    shortname = l_('.Net modules')

    def generate(self, docnames=None):
        content = {}
        # list of all modules, sorted by module name
        modules = sorted(self.domain.data['objects'].iteritems(),
                         key=lambda x: x[0].lower())
        for modname, (docname, _type) in modules:
            if docnames and docname not in docnames:
                continue

            if _type != 'namespace':
                continue

            letter = modname.split('.')[-1][0]

            entries = content.setdefault(letter.lower(), [])

            subtype = 0
            qualifier = ''
            synopysis = ''
            extra = ''
            anchor = modname

            entries.append([
                modname,  # name
                subtype,  # subtype
                'autoapi/' + '/'.join(modname.split('.')) + '/index',  # docname
                anchor,  # Anchor
                extra,  # Extra
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
        'objects': {},  # fullname -> docname, objtype
    }

    indices = [
        DotNetIndex,
    ]

    def clear_doc(self, docname):
        for fullname, (fn, _) in self.data['objects'].items():
            if fn == docname:
                del self.data['objects'][fullname]

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
            if prefix and fullname in objects:
                newname = fullname
            else:
                newname = name
        else:
            if name in objects:
                newname = name
            elif prefix and fullname in objects:
                newname = fullname

        return newname, objects.get(newname)

    def resolve_xref(self, env, fromdocname, builder, obj_type, target, node,
                     contnode):
        prefix = node.get('dn:prefix')
        searchorder = node.hasattr('refspecific') and 1 or 0

        name, obj = self.find_obj(env, prefix, target, obj_type, searchorder)

        if not obj:
            return None
        # TODO required to swap out dollar sigil?
        return make_refnode(builder, fromdocname, obj[0],
                            name.replace('$', '_S_'), contnode, name)

    def get_objects(self):
        # TODO wtf does this do?
        for refname, (docname, type) in self.data['objects'].iteritems():
            yield refname, refname, type, docname, \
                refname.replace('$', '_S_'), 1


def setup(app):
    app.add_domain(DotNetDomain)
