..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

=======================================
Allow StringField to enforce max length
=======================================

https://blueprints.launchpad.net/nova/+spec/string-field-max-length

This blueprint aims to add a max length constraint to the
`nova.objects.fields.StringField` class.

Problem description
===================

Currently, the nova object framework revolves around the use of field type
classes that describe the schema of an object. Each object model is simply
a collection of fields, each of which have a particular type, such as
IntegerField or StringField.

In much the same way that a SQL database schema describes the constraints
that a given column in a table must adhere to -- e.g. the length of characters
possible in a CHAR field, or a valid DATETIME string -- the nova objects
should be self-validating.

Proposed change
===============

This specification proposes to change the `coerce` method of the
`String` class to validate on the number of characters in the
field's string value.

The `StringField` concrete field class shall have a new `max_length` kwarg
added to its constructor that will control the validation. The default
value will be None, and no `StringField` objects defined in the schemas of
any of the nova object models shall be changed in this spec.

Alternatives
------------

None (keep things the way they are now)

Data model impact
-----------------

None (the existing models themselves won't be changed in this specification
at all)

REST API impact
---------------

None

Security impact
---------------

None

Notifications impact
--------------------

None

Other end user impact
---------------------

None

Performance Impact
------------------

None

Other deployer impact
---------------------

None

Developer impact
----------------

None

Implementation
==============

Roughly, the code the `String` field type class would change from this:

.. code:: python

    class String(FieldType):
        @staticmethod
        def coerce(obj, attr, value):
            # FIXME(danms): We should really try to avoid the need to do this
            if isinstance(value, (six.string_types, int, long, float,
                                  datetime.datetime)):
                return unicode(value)
            else:
                raise ValueError(_('A string is required here, not %s') %
                                 value.__class__.__name__)

to this:

.. code:: python

    class String(FieldType):

        def __init__(self, max_length=None):
            """
            :param max_length: Optional constraint on the number of Unicode
                               characters the string value can be.
            """
            self._max_length = max_length

        @staticmethod
        def coerce(self, obj, attr, value):
            # FIXME(danms): We should really try to avoid the need to do this
            if isinstance(value, (six.string_types, int, long, float,
                                  datetime.datetime)):
                result = unicode(value)
            else:
                raise ValueError(_('A string is required here, not %s') %
                                 value.__class__.__name__)
            if self._max_length is not None:
                if len(value) > self._max_length):
                    msg = _("String %(result)s is longer than maximum allowed "
                            "length of %(max_length)d.")
                    msg = msg % dict(result=result,
                                     max_length=self._max_length)
                    raise ValueError(msg)
            return result

The StringField class would then need to be modified to allow passing the
max_length parameter along to its type class.

Work Items
----------

N/A

Assignee(s)
-----------

Primary assignee:
  jaypipes

Dependencies
============

None

Testing
=======

Would need new unit tests. No need for any integration test changes.

Documentation Impact
====================

None

References
==========

The server-instance-tagging work will likely be the first work to use
this functionality, as the tag string has a max length associated with
it and we need to be very careful about changing existing model fields' string
length validation code, so a new field like the tag field is an ideal place to
begin with this implementation.

http://git.openstack.org/cgit/openstack/nova-specs/tree/specs/juno/tag-instances.rst
