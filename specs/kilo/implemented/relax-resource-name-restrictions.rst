..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

================================
Relax resource name restrictions
================================

https://blueprints.launchpad.net/nova/+spec/relax-resource-name-restrictions

Currently, the only allowed characters in most resource names are
Unicode alphanumerics, space, and ``[.-_]``. This should be expanded
to all printable unicode characters and horizontal spaces.

Problem description
===================

Resource names are unnecessarily restricted. It's pretty much always a
bad idea to add unnecessary restrictions without a good
reason. Furthermore, the current restriction already allows Unicode,
so any Unicode-related concerns should not be tied to this blueprint.

Use Cases
---------

While there may not be an immediate need to use, for example, the
ever-useful `PILE OF POO <http://codepoints.net/U+1F4A9>`_ in a flavor
name, it's hard to come up with a reason people *shouldn't* be allowed
to use it.

Project Priority
----------------

None.

Proposed change
===============

Instead of a strict whitelist of alphanumerics, space, and ``[.-_]``,
we propose to allow all printable three-byte Unicode characters and
horizontal spaces. With reference to `Unicode character categories
<http://www.fileformat.info/info/unicode/category/index.htm>`_, the
allowed characters will be:

* All characters that are not in the ``C`` (Other, including control
  and format characters) and ``Z`` (Separator) categories; and
* Characters in the ``Zs`` (Separator, Space) category.

Fields that have legitimate reasons to be restricted can still impose
further restrictions. For instance, hostnames can be restricted per
RFC 1178, which is a strict subset of the restrictions described above.

Alternatives
------------

Full four-byte support is problematic due to limitations in MySQL. The
``utf8`` character set only supports three-byte Unicode, while
``utf8mb4`` supports full four-byte Unicode. But MySQL limits key
length to 765 bytes, which fits a 255-character three-byte string, but
only a 190-character four-byte string. So, in order to provide full
four-byte Unicode support in MySQL, we'd have to reduce the length of
any key fields, which is distinctly undesirable.

Making the allowable Unicode character width configurable (e.g., for
installations using PostgreSQL) is difficult since
``nova.api.validation.parameter_types``, the primary module that
implements the naming restrictions, defines all of its types as
module-level variables; making these configurable would be
unnecessarily difficult and fraught. It could also confuse users
moving between environments.

Moreover, no interest has been expressed in using full four-byte
Unicode support; if someone would like to implement that later,
nothing in this feature will preclude that option.

Data model impact
-----------------

None.

REST API impact
---------------

The validation for many REST endpoints will change; for instance,
creating a flavor called "m1.small+" will fail on Juno, but will
succeed once this spec is implemented. That said, the new allowed
characters are a strict superset of the old allowed characters, so
this should only be an issue moving from Kilo to Juno; all resources
created on Juno will work on Kilo.

Security impact
---------------

None.

Notifications impact
--------------------

None.

Other end user impact
---------------------

None.

Performance Impact
------------------

Minimal. Compiled regexes, even large ones, are embarrassingly
efficient. The actual performance penalty incurred by this change
varies by the length of the name used; longer names incur less of a
penalty than shorter names. Using a random distribution of both valid
and invalid names between five and two hundred characters long, I
found that the new approach is approximately 16% slower than the old
approach.

While 16% may seem like a significant performance impact, it's 16% of
an operation that is currently measured in microseconds on modern
hardware. To put the performance impact in pragmatic terms, someone
would have to create in the neighborhood of fifty million new entities
(say, fifty million new flavors) to even reach 10 seconds of
performance penalty due to this change (assuming Nova is running on my
laptop, which is not recommended in production).

Other deployer impact
---------------------

None.

Developer impact
----------------

None.

Implementation
==============

Assignee(s)
-----------

Primary assignee:
  stpierre

Work Items
----------

#. Create a new name validation regex that allows all printable
   three-byte Unicode characters and horizontal spaces.
#. Make all JSON Schema documents use
   ``nova.api.validation.parameter_types.hostname`` for validating all
   server name fields.
#. Make all JSON Schema documents use the new regex for validating all
   other resource names.

Dependencies
============

In order to make this change discoverable by the API user, it depends
on API microversions:
https://blueprints.launchpad.net/nova/+spec/api-microversions

Testing
=======

No new tempest tests are required; existing tempest tests that test
resource name validation will need to be modified to include names
that are now invalid under the new, relaxed, restrictions.

Unit tests will, of course, be added as well.

Documentation Impact
====================

Docs that mention the old resource name restrictions will need to be
updated to the new ones.

References
==========

* Mailing list discussion: http://lists.openstack.org/pipermail/openstack-dev/2014-September/045917.html
* Tempest test updates: https://review.openstack.org/#/c/120451/
* Nova change: https://review.openstack.org/#/c/119741/
