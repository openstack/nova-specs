..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

========================================
Robustify Compute Node Hostname Handling
========================================

Include the URL of your launchpad blueprint:

https://blueprints.launchpad.net/nova/+spec/example

Nova has long had a dependency on an unchanging hostname on the
compute nodes. This spec aims to address this limitation, at least
from the perspective of being able to detect an accidental change and
avoiding catastrophe in the database that can currently result from a
hostname change, whether intentional or not.

Problem description
===================

Currently nova uses the hostname of the compute (specifically
``CONF.host``) for a variety of things:

#. As the routing key for communicating with a compute node over RPC
#. As the link between the instance, service and compute node objects
   in the database
#. For neutron to bind ports to the proper hostname (and in some
   cases, it must match the equivalent setting in the neutron agent
   config)
#. For cinder to export a volume to the proper host
#. As the resource provider name in placement (this actually comes
   from libvirt's notion of the hostname, not ``CONF.host``)

If the hostname of the compute node changes, all of these links
break. Upon starting the compute node with the changed name, we will
be unable to find a ``nova-compute`` ``Service`` record in the
database that matches, and will create a new one. After that, we will
fail to find the matching ``ComputeNode`` record and create a new one
of those, with a new UUID. Instances that refer to both the old
compute and service records will not be associated with the running
host, and thus become unmanageable through the API. Further, new
instances that end up created on the compute node after the rename
will be able to claim resources that have been promised to the
orphaned instances (such as PCI devices and VCPUs) as the tracking of
those is associated with the old compute node record.

If the orphaned instances are relatively static, the first indication
that something has gone wrong may be long after the actual rename,
where reality has forked and there are instances running on one
compute node that refer to two different compute node records and thus
are accounted for in two separate locations.

Further, neutron, cinder, and placement resources will have the old
information for existing instances and new information for current
instances, which requires reconciliation. This situation may also
prevent restarting old instances if the old hostname is no longer
reachable.

Use Cases
---------

* As an operator, I want to make sure my database does not get
  corrupted due to a temporary or permanent DNS change or outage
* As an operator, I may need to change the name of a compute node as
  my network evolves over many years.
* As a deployment tool writer, I want to make sure that changes in
  tooling and libraries never cause data loss or database corruption.

Proposed change
===============

There are multiple things we can do here to robustify Nova's handling
of this data. Each one increases safety, but we do not have to do all
of them.

Ensure a stable compute node UUID
---------------------------------

For non-ironic virt drivers, whenever we generate a compute node uuid,
we should write that to a file on the local disk. Whenever we start,
we should look for that UUID file, use that, and under no
circumstances should we generate another one. To facilitate
pre-generating this by deployment tools, we should use this if we are
starting for the first time and create a ComputeNode record in the
database.

We would put the actual lookup of the compute node UUID in the
`get_available_nodes()` method of the virt driver (or create a new
UUID-specific one). Ironic would override this with its current
implementation that returns UUIDs based on the state of Ironic and the
hash ring. Thus only non-Ironic computes would read and write the
persistent UUID file.

Single-host virt drivers like libvirt would be able to tolerate a
system hostname change, updating ``ComputeNode.hypervisor_hostname``
without breaking things.

Link ComputeNode records with Service records by id
---------------------------------------------------

Currently the ComputeNode and Service records are associated in the
database purely by the hostname string. This means that they can
become disassociated, and is also not ideal from a performance
standpoint. Some other data structures are linked against ComputeNode
by id, and thus are not re-associated when the name matches.

This relationship used to exist, but was `removed`_ in the Kilo
timeframe. I believe this was due to the desire to make the process
less focused on the service object and more on the compute node
(potentially because of Ironic) although the breaking of that tight
relationship has serious downsides as well. I think we can keep the
tight binding for single-host computes where it makes sense.

At startup, ``nova-compute`` should resolve its ComputeNode object via
the persistent UUID, find the associated Service, and fail to start if
the hostname does not match CONF.host. Since this is used with
external services, we should not just "fix it" as those other links
will be broken as well. This will at least allow us to avoid opening
the window for silent data corruption.

Link Instances to a ComputeNode by id
-------------------------------------

Currently instance records are linked to their Service and ComputeNode
objects purely by hostname. We should link them to a ComputeNode by
its id. Since we need the Service in order to get the RPC routing key
or for hostname resolution when talking to external services, we
should find that based on the Instance->ComputeNode->Service id
relationship.

We already link PCI allocations for instances to the compute node by
id, even though the instance itself is linked via hostname. This
discrepancy makes it easy to get one out of sync with the other.

Potential Changes in the future
-------------------------------

If the above changes are made, we open ourselves to the future
possibility for supporting:

#. Renaming service objects through the API if a compute host really
   needs to have its hostname changed. This will require changes to
   the other services at the same time, but nova would at least have a
   single source of truth for the hostname, making it feasible.
#. If we do all of this, Nova could potentially be confident enough of
   an intentional rename that it could update port bindings, cinder
   volume attachments, and placement resources to make it seamless.es
#. Moving to the use of the service UUID as the RPC routing key, if
   desired.
#. Dropping quite a bit of duplicate string fields from our database.


Alternatives
------------

We can always do nothing. Compute hostnames have been unchangeable
forever, and the status quo is "don't do that or it will break" which
is certainly something we could continue to rely on.

We could implement part of this (i.e. the persistent ComputeNode UUID)
without the rest of the database changes. This would allow us to
detect the situation and abort, but without (the work required to get)
the benefits of a more robust database schema that could potentially
also support voluntary renames.


Data model impact
-----------------

Most of the impact here is to the data model for Instance,
ComputeNode, Service. Other models that reference compute hostnames
may also make sense to change (although it's also reasonable to punt
that entirely or to a different phase). Examples:

* Migration
* InstanceFault
* InstanceActionEvent
* TaskLog
* ConsoleAuthToken

Further, host aggregates use the service name for
membership. Migrating those to database IDs is not possible since
multiple cells will cause overlap. We could migrate those to UUIDs or
simply ignore this case and assume that any *actual* rename operation
in the future would involve API operations to fix aggregates (which is
doable, unlike changing the host of things like Instance).

REST API impact
---------------

No specific REST API impact for this, other than the potential for
enabling a mutable Service hostname in the future.


Security impact
---------------

No impact.


Notifications impact
--------------------

No impact.

Other end user impact
---------------------

Not visible to end users.

Performance Impact
------------------

Theoretically some benefit comes from integer-based linkages between
these objects that are currently linked by strings. Eventually we
could reduce a bunch of string duplication from our DB schema and
footprint.

There will definitely be a one-time performance impact due to the
online data migration(s) required to move to the more robust schema.

Other deployer impact
---------------------

This is really all an (eventual) benefit to the deployer.

Developer impact
----------------

There will be some churn in the database models during the
transition. Looking up the hostname of an instance will require
Instance->ComputeNode->Service, but this can probably be hidden with
helpers in the Instance object such that not much has to change in the
actual workflow.

Upgrade impact
--------------

There will be some substantial online data migrations required to get
things into the new schema, and the benefits will only be achievable
in a subsequent release once everything is converted.

Implementation
==============

Assignee(s)
-----------

Primary assignee:
  danms


Work Items
----------

* Persist the compute node UUID to disk when we generate it. Read the
  compute node UUID from that location if it exists before we look to
  see if we need to generate, create, or find an existing node record.
* Change the compute startup procedures to abort if we detect a
  mismatch
* Make the schema changes to link database models by id. The
  ComputeNode and Service objects/tables still have the id fields that
  we can re-enable without even needing a schema change on those.
* Make the data models honor the ID-based linkages, if present
* Write an online data migration to construct those links on existing
  databases

Later, there will be work items to:
* Drop the legacy columns
* Potentially implement an actual service rename procedure

Dependencies
============

There should be no external dependencies for the base of this work,
but there is a dependency on the release cycle, which affects how
quickly we can implement this and drop the old way of doing it.

Testing
=======

Unit and functional testing for the actual compute node startup
behavior should be fine. Existing integration testing should ensure
that we haven't broken any of the runtime behavior. Grenade jobs
will test the data migration and we can implement some nova status
items to help validate things in those upgrade jobs.

Documentation Impact
====================

There will need to be some documentation about the persistent compute
node UUID file for deployers and tool authors. Ideally, the only
visible result of this would be some additional failure modes if the
compute service detects an unexpected rename, so some documentation of
what that looks like and what to do about it would be helpful.

References
==========

TODO(danms): There are probably bugs we can reference about compute
node renames being not possible, or problematic if/when they happen.

.. _removed: https://specs.openstack.org/openstack/nova-specs/specs/kilo/implemented/detach-service-from-computenode.html

History
=======

.. list-table:: Revisions
   :header-rows: 1

   * - Release Name
     - Description
   * - Antelope
     - Introduced
