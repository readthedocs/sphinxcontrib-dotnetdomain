==================
.NET Domain Syntax
==================

Below are the supported syntax rules to the .NET domain:

General Rules
=============

Options
-------

All constructs support the following directive option modifiers:

* public
* protected
* static

For example::

    .. dn:class:: Foobar
        :protected:
        :static:

These options will prefix the output declaration with a modifier, such as::

    class protected static Foobar

These output modifiers are not part of the object name, and so are not part of
any cross references.

Properties
==========

Properties can be defined with the modifier flags:

* getter
* setter

For example::

    .. dn:property:: Foobar()
        :setter:
        :getter:

Fields
======

Fields can be defined with the modifier flags:

* adder
* remover

For example::

    .. dn:field:: Foobar()
        :adder:
        :remover:

Generic Types
=============

Generic type supported syntax::

    .. dn:class:: Foobar<T>
    .. dn:class:: Foobar<T,T>
    .. dn:class:: Foobar<TFoo,TBar>
    .. dn:class:: Foobar<T,<string>>
    .. dn:class:: Foobar<T,<T,<string>>>
