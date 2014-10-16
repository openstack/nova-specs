..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

==========================================
Make Resource Tracker Use Objects
==========================================

https://blueprints.launchpad.net/nova/+spec/make-resource-tracker-use-objects

This blueprint was approved for Juno but missed feature freeze.

Nova is converting data structures it uses to communicate via RPC and through
the database to use an object encapsulation called Nova Objects. This supports
of multi-versioning for live-upgrade and database schema independence. This
blueprint covers the conversion of the resource tracker to use Nova Objects.

Problem description
===================

Conversion to Nova Objects will replace dict data structures that are currently
communicated via the conductor API with Nova Object versions. Where necessary
the Nova Objects will be extended to cover parameters that are not already
implemented.

Use Cases
---------

As an operator I want to be able to upgrade Nova without any downtime.

Project Priority
----------------

This blueprint fits under the Live Upgrades priority.

Proposed change
===============

The Nova Object classes that will be used include:

- ComputeNode
- Instance
- Migrations
- Flavor
- Service

The ComputeNode object is currently missing some parameters that exist
in the compute_nodes table and are used in the resource tracker. The
following parameters will be added to the ComputeNode:

- pci_stats

In addition, the following fields exist in the compute_nodes table but
are not currently used by the resource tracker. We propose not to add fields
to the ComputeNode object unless they are used, so these fields will not
be added as part of this blueprint.

- extra_resources

When complete there will be no direct calls to conductor in the resource
tracker.

Alternatives
------------

There is another effort to split the scheduler from Nova. When the split is
complete the resource tracker may no longer interact with the scheduler via
the database.  Initially, the scheduler-lib blueprint (see references) will
make all compute node interaction with the scheduler go through a new
scheduler library in preparation for the split.

This suggests that it might be unnecessary to use the ComputeNode object at
least. However, it is reasonable to continue using the ComputeNode object
even if it is not used to persist data in the database, so we will go ahead
with the existing plan to implement it.

Data model impact
-----------------

The objects isolate the code from the database schema. They are written to
operate with existing data model versions. At present the scheduler does not
the ComputeNode object, so code there will need to tolerate changes in
database schema or the format of data stored in fields.

The fields that need to be added to the ComputeNode object are as follows:

**pci_stats**

Database field type: text

Object field type: fields.ObjectField('PciDeviceList', nullable=True)

The pci_stats field is currently populated with a PciDeviceList serialized
as an object primitive. This is already the correct form for an object field.

REST API impact
---------------

None.

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

None.

Other deployer impact
---------------------

The objects are written to be compatible with the database schema used in
Juno. There is no database migration associated with this blueprint and
the format of data stored in the fields of the database will not change. This
means that a combination of Juno and Kilo versions of the compute nodes
will be able to coexist and interact with the scheduler.

Developer impact
----------------

Developers working on the resource tracker will be required to use the new
objects instead of directly making database calls to conductor.

Implementation
==============

Assignee(s)
-----------

Primary assignee:
  pmurray

Work Items
----------

* Use flavor object in resource tracker

* Use Service object in resource tracker

* Use Instance object in resource tracker

* Use Migrations object in resource tracker

* Use ComputeNode object in resource tracker

Some of these work items are currently ready for review:
https://review.openstack.org/#/q/topic:bp/make-resource-tracker-use-objects,n,z

Dependencies
============

None

Testing
=======

This does not affect existing tempest tests. Unit tests will be
added for each object and existing tests will be modified to deal
with the new data structure.

Documentation Impact
====================

No new features or API changes so no document impact.

References
==========

https://blueprints.launchpad.net/nova/+spec/scheduler-lib
