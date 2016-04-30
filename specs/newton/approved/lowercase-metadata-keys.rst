..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

===========================================
Restrict valid characters for metadata keys
===========================================

https://blueprints.launchpad.net/nova/+spec/lowercase-metadata-keys

Change API validation to require metadata keys are only lower case
ascii with a limited number of symbols to ensure consistent operation
regardless of database backend.

Problem description
===================

Metadata keys throughout Nova (as used by aggregates, servers, flavors
extra specs). They get stored with various levels of restrictions.

* aggregate metadata - ^[a-zA-Z0-9-_:. ]{1,255}$' (with the allowance
  it can be null) [#f1]_
* server metadata - ^[a-zA-Z0-9-_:. ]{1,255}$' [#f2]_
* flavors extra specs - ^[a-zA-Z0-9-_:. ]{1,255}$' [#f3]_ (but also
  can be cast as a number, which is probably a bug in failing to
  understand jsonschema)

All of these lead to issues because the default storage with MySQL is
case *insensitive*. This leads to bugs of the following type:

https://bugs.launchpad.net/nova/+bug/1538011 (what is seen in Aggregates)

1. If we have unique constraints on a column
2. Add key to a resource of name 'foo'
3. Add key to a resource of name 'Foo' - explodes as a constraint
   violation

or in the delete case:

https://bugs.launchpad.net/nova/+bug/1535224 (what is seen in Server Metadata)

1. If we don't have unique constraints on a column
2. Add keys to a resource named 'foo', 'Foo', 'FOO'.
3. Delete key 'foo'
4. All of 'foo', 'Foo', 'FOO' are deleted

Up until this point there have been some complicated fixes that are
largely whack a mole working around this by doing a second round of
select / delete / update in python to make up for the case
insensitivity issues.

in the Flavors Extra Specs case we get yet a third behavior:

1. Add key 'foo'
2. Add key 'Foo'
3. "Returning 409 to user: Flavor 3 extra spec cannot be updated or
   created after 10 retries." returned to the user

Use Cases
---------

As a user of metadata in the Nova API I would like a guarunteeded get
/ set that works the same regardless of backend database.

Proposed change
===============

Create an API microversion after which point we make the metadata
definition be '^[a-z0-9-_:. ]{1,255}$', dropping support for uppercase
ascii characters.

Update documentation to say that's all that is supported.

In requests before the microversion we will not change behavior,
however we will also close all bugs related to this as Won't Fix.

A `nova-manage` command for auditing and squashing existing metadata
keys into the new storage format will be provided. This will be
optional for the operator to run, as they may choose to live with the
bugs on older API versions.

The following resources use metadata and fall victim to this:

* Aggregates
* Flavors Extra Specs
* Instances (servers) (all actions unless otherwise specified)
* Instances metadata direct set / get

The following parts of the API will not be changed:

* servers (actions) - createImage (the metadata is glance metadata,
  and not stored in Nova)
* Images proxy - this is stored via glance, Nova will not change
  validation rules here.
* Volumes proxy - this is stored via cinder, Nova will not change
  validation rules here.


Alternatives
------------

.. courtesy of jpenick

* Firey ball of suck

  Just keep glomming on more python hot fixes to try to approximate
  the behavior we want. This is unlikely to really converge to the
  point where we don't have bugs.

* Force consistent behavior in database

  We could force MySQL to be case sensitive here which would remove a
  class of stack traces. However that becomes a potentially expensive
  migration, and means we have to care about all potential backends
  behaving correctly

* Implement 409 for all resources like Flavor Extra Specs

  This requires quite a bit of extra round tripping to the database,
  and potentially runs into interesting race conditions when updates
  are happening simultaneously.

Data model impact
-----------------

No data model changes will be made until we uplift microversion to the
point where the old code is not supported.

REST API impact
---------------

No change to resources or attributes, however we'll now be
returning 400 via the validation framework.

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

There will now be metadata keys that won't be accessable via the API
after the microversion. If other items such as scheduler filters or
higher level orchestration trigger off these values there may need to
be changes to them.

A `nova-manage` command should be provided to audit and fold old keys
into this new key structure.

Developer impact
----------------

None

Implementation
==============

Assignee(s)
-----------

Primary assignee:
  auggy

Other contributors:
  sdague

Work Items
----------

* Implement jsonschema using this new validation rule for a new
  microversion for the resources listed above.
* Write `nova-manage` key folding tool. (Ensure that we remember to
  update metadata quota in the process)


Dependencies
============

None

Testing
=======

Testing will be done with in tree functional testing as this is all
just API and API <-> DB code paths.

Testing for `nova-manage` tool done in tree to ensure we can properly
fold data and update quota.

Documentation Impact
====================

API Reference site will be updated with new microversion. We will
update the default documentation to say that the API only supports
this subset of characters. This will hopefully get people using old
versions to self reduce to this new character set.

References
==========

* Mailing list discussion on this bug -
  http://lists.openstack.org/pipermail/openstack-dev/2016-February/087404.html
* Etherpad from Newton Summit -
  https://etherpad.openstack.org/p/newton-nova-summit-unconference

.. rubric:: Footnotes

.. [#f1] https://github.com/openstack/nova/blob/8185dcb57e55f7579b60040649fcd0588177d714/nova/api/openstack/compute/schemas/aggregates.py#L123
.. [#f2] https://github.com/openstack/nova/blob/8185dcb57e55f7579b60040649fcd0588177d714/nova/api/openstack/compute/schemas/server_metadata.py#L47
.. [#f3] https://github.com/openstack/nova/blob/8185dcb57e55f7579b60040649fcd0588177d714/nova/api/openstack/compute/schemas/flavors_extraspecs.py#L22

History
=======

.. list-table:: Revisions
   :header-rows: 1

   * - Release Name
     - Description
   * - Newton
     - Introduced
