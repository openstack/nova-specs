..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

==========================================
Make Resource Tracker Use Objects
==========================================

https://blueprints.launchpad.net/nova/+spec/make-resource-tracker-use-objects

This blueprint was approved for Kilo but some patches missed the feature
freeze. This proposal is to complete the remaining patches in Liberty.

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
- PciDevicePool

The ComputeNode object was modified during the Kilo cycle to include
required fields. A small amount of cleanup is needed around the
PciDevicePool object to correct assignment of tags and the API samples
and tests associated with the os-pci API. PciDevicePool is used
in the ComputeNode object so this is required before finally replacing
compute node data structures in the resource tracker with the ComputeNode
object.

The other objects were added to the resource tracker during Kilo.

Alternatives
------------

None.

Data model impact
-----------------

The objects isolate the code from the database schema. They are written to
operate with existing data model versions. At present the scheduler does not
the ComputeNode object, so code there will need to tolerate changes in
database schema or the format of data stored in fields.

REST API impact
---------------

None. The current tests and API samples for pci stats are incorrect and
will be fixed. This does not change the relvant API, so although the
samples change, the API doesn't.

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
Juno. There is no database migration associated with the remaining
changes in this blueprint and the format of data stored in the fields of
the database will not change. This means that a combination of Kilo and
Liberty versions of the compute nodes will be able to coexist and interact
with the scheduler.

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

These are the remaining work items left to complete the blueprint.

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

The os-pci API response samples will be correct. There will be no new feature
and the APIs will not change, but API samples appear in the documentation so
this will cause a minor documentation impact.

References
==========

https://blueprints.launchpad.net/nova/+spec/scheduler-lib
