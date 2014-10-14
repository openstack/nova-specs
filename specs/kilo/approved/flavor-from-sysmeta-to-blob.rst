..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

===============================================
Move flavor data from system-metadata to a blob
===============================================

Include the URL of your launchpad blueprint:

https://blueprints.launchpad.net/nova/+spec/flavor-from-sysmeta-to-blob

Flavor data is currently stored inefficiently in system_metadata and
should be moved to being stored as a blob in an appropriate place
per-instance. This will facilitate storing additional flavor details
that we badly need, such as extra_specs.

Problem description
===================

Currently we store some properties of the flavor used to spawn an
instance in that instance's system_metadata area. We do this by
namespacing the keys of the flavor like this:

=======================  ======
Key                      Value
=======================  ======
instance_type_flavorid   'foo'
instance_type_memory_mb  '1024'
=======================  ======

This means that everything is stringified and that each key and value
is limited to 255 characters. It also makes it very difficult to store
complex flavor properties, such as extra_specs which has become
increasingly important recently for things like NUMA and PCI
passthrough. Without the ability to store these values along with the
rest of the flavor information, rescheduling or migrating an instance
requires using a combination of the original flavor data (stored with
the instance) along with the current values attached to the flavor.

Finally, during a resize operation, we store two additional copies of
all of this data for the old and new flavors respectively, all in
system_metadata. Since system_metadata is a single row key-value
layout, this means we get a lot of rows per instance during a
resize. In the past, this led to a decoupling of the instance query
from the system_metadata query, since a multiple-instance query joined
with system_metadata would inflate an already large result by a factor
of approximately 30.

Use Cases
----------

* As an operator, I want to be able to migrate my instances and have
  the rescheduling process honor all the original information I
  provided, such as CPU and NUMA layouts as well as PCI passthrough
  details.
* As an operator, I want to have database queries be efficient, both
  in wire bandwidth as well as in latency. Joining large tables and
  making multiple queries hurt this goal.

Project Priority
-----------------

This refactor has been a project priority for several cycles now,
fitting under both the "stability" and "reducing technical debt" umbrellas.

Proposed change
===============

Since shortly after we started storing flavor data in system_metadata,
we have been discussing moving it to a JSON blob in a suitable place
in the database. Late in Juno, we added a table called
"instance_extra" specifically for the purpose of holding additional
JSON blobs for each instance that are needed at different times. This
spec proposes to add another column to that table for "flavor" where
we will store a JSONified copy of the flavor on initial boot. Further,
we will provide for storage of an 'old' and 'new' flavor to facilitate
resize operations. The top-level structure will look like this::

 {'cur': { ... serialized Flavor object ... }
  'new': None,
  'old': None,
 }

When a flavor is stored in one of the three slots above, the form used
will be the serialized NovaObject result. This means that the content
in the database will be versioned and deserializing it from the
database will work just like receiving one over RPC.

The database migration for this change will simply add the new column,
but not perform a data migration. Instead, the migration from
system_metadata to instance_extra will be managed by the objects
layer. The objects code will handle honoring the system_metadata
flavor data, if present, otherwise using the new format in
instance_extra. During a save operation, the system_metadata area will
be cleared of any flavor data at which time the instance will be fully
migrated.

Alternatives
------------

* We could keep doing what we're doing, adding additional hacks to the
  flavor stashing code to keep the bits of extra_specs that we need
* We could move to persisting more of the request_spec structure,
  which would necessarily include the flavor data, as suggested here:
  https://review.openstack.org/#/c/125484/1. My feeling is that when
  we get to things internally modeled more as tasks, we'll have a
  better base for that and that the incremental improvement offered by
  the approach chosen in this spec is a worthwhile intermediate step
  at least.

Data model impact
-----------------

This will add a new TEXT column to the instance_extra table, and will
result in data being migrated out of system_metadata to that column as
instances are used.

Additionally, a tool to perform offline migrations of instances that
are not changing will need to be written to allow operators to ensure
that dormant instances get their data migrated as well as active ones.

The Instance object will gain three new properties: 'flavor',
'old_flavor', and 'new_flavor'. These will be honored in the
"expected_attributes" parameters of various queries, and will contain
a nova.objects.Flavor object when and where appropriate.

REST API impact
---------------

There should be no user-visible impact to this change.

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

After all the flavor data is moved out of system_metadata, we can
consider going back to joining system_metadata when we query for
instances. This will remove a DB hit and potentially improve latency.

Additionally, the objects layer will support conditional loading of
the flavor data, allowing code that needs system_metadata, but not all
of the flavor data to request that more granular response.

Other deployer impact
---------------------

Deployers will need to take action to ensure that dormant instances
get their data migrated before we remove the compatibility code that
supports flavors in system_metadata. This should be something that can
be run in the background against a running deployment, so the operator
impact is mostly procedural.

Developer impact
----------------

The objects layer should mostly hide the complex migration activities
from the average developer. However, it will be important for people
to realize that accessing the flavor information for an instance
through the Instance.flavor object is necessary going forward.

Implementation
==============

Assignee(s)
-----------

Primary assignee:
  danms

Work Items
----------

* Clean up existing instance_extra interfaces for consistency, moving
  pci_requests to be a proper field on Instance, etc.
* Add a flavor column to instance_extra
* Add the three flavor fields to Instance
* Modify the Instance object and instance_* DB API functions to handle
  compatibility with and migration away from flavors being stored in
  system_metadata
* Write a tool to migrate inactive instances in the background, to live
  in the nova/tools directory

Dependencies
============

This is mostly isolated work. Other work may depend on this, however.

Testing
=======

Unit tests to cover the online data migration code will be provided
and should be relatively straightforward. Further, the existing
grenade testing in the gate should cover the data migration case for
existing instances, as well as guaranteeing that this migration on
newer conductor nodes does not disrupt compute nodes running Juno code.

Documentation Impact
====================

Some documentation of the fact that this is being done will need to
appear in the release notes. Further, a small bit of documentation to
cover the procedures for migrating the data of dormant instances will
need to be integrated into any documents that describe moving from
Juno to Kilo.

References
==========

* Original plan to move all of system_metadata to a JSON blob,
  including flavors:
  https://blueprints.launchpad.net/nova/+spec/instance-sysmeta-to-json
