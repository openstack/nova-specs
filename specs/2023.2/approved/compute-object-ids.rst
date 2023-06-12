..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

==========================
Link Compute Objects by ID
==========================

https://blueprints.launchpad.net/nova/+spec/compute-object-ids

Nova has long had a dependency on an unchanging hostname on the
compute nodes. This spec aims to address this limitation, at least
from the perspective of being able to detect an accidental change and
avoiding catastrophe in the database that can currently result from a
hostname change, whether intentional or not.

As a continuation of the effort to `robustify compute hostnames`_, this spec
describes the next phase which involves strengthening the linkage between the
primary database objects managed by the compute nodes.

Problem description
===================

The ``ComputeNode``, ``Service``, and ``Instance`` objects form the primary
data model for our compute nodes. Instances run on compute nodes, which are
managed by services. We rely on this hierarchy to know where instances are
(physically) as well as which RPC endpoint to send messages to for management.
Currently, the linkage between all three objects is a relatively loose and
string-based, association using the hostname of the compute node and/or the
``CONF.host`` values. This not only makes an actual/intentional rename very
difficult, but also risks breaking critical links as a result of an
*accidental* one.

Use Cases
---------

As an operator I want an accidental or transient hostname rename to not cause
corruption of my Nova data structures.

As a developer, I want a stronger association between the primary objects in
the data model for robustness and performance reasons.

Proposed change
===============

We already have a ``service_id`` field on our ``ComputeNode`` object. We should
resume populating that when we create a new ``ComputeNode`` and we should fix
existing records during ``ComputeManager.init_host()``, similar to how we added
checks for hostname discrepancies in the earlier phase of this effort.

We will need to add a ``compute_id`` field to the ``Instance`` object, which
will require a schema migration. This field will need to remain nullable, and
will be ``NULL`` for instances before scheduling, as well as instances in
``SHELVED_OFFLOADED`` state. The ``compute_id`` field can be populated at the
same time we currently set ``Instance.node``, and similar to ``ComputeNode``
records above, we can migrate existing records during
``ComputeManager._init_instance()``. In order to ensure that we keep the `node`
and `compute_id` fields in sync, the ``Instance.create()`` and
``Instance.update()`` methods will perform a check to ensure that the former is
never changed without the latter also being changed. This check will (by the
nature of those two ``@remotable`` methods) be run on the conductor nodes, and
will only enforce the requirement if the version of the objects is new enough.

Many of the times we update ``Instance.node``, we do so from a ``Migration``
object, using either ``source_node`` for reverted migrations or ``dest_node``
for successful ones. Thus, our handling of migrations will need some work as
well, which is described in the subsection below.

It is important to note that this spec defines one part of a two-part effort.
The setup described here will require a subsequent step to change how we
look up these objects to use the new relationships once all the data has been
migrated.

Migration handling
------------------

Currently we update ``Instance.node`` from a ``Migration`` object in a number
of places. In most of these, it is being performed *on* the node where the
instance will remain. For those cases, we will get the ``ComputeNode`` object
from the resource tracker (still by name, from the ``Migration`` object) and
use it to set the new field. Aside from saving a loosely-coupled DB lookup
each time we need it, this has the additional benefit of double-checking that
the node specified (loosely, by name) in the ``Migration`` object is the (or a)
correct one for the current host.

The only place where we currently update ``Instance.node`` from a location that
is *not* the host where the Instance is staying is during the early part of
resize, where ``_resize_instance()`` runs on the sending host with information
provided by the destination. In this case, we will modify the ``Migration``
object to have one additional ``dest_compute_id`` field, which will be filled
by the destination host with its known-correct value, to be used by the sending
host when it modifies ``Instance.node`` (and ``Instance.compute_id``) to be the
values for the new host.

Upgrade Concerns
----------------

Since the ``Instance`` and ``Migration`` objects will be growing new fields,
older nodes will not be populating these fields when migrating between old and
new nodes. In the case of ``Instance``, the ``compute_id`` field will not be
actually used until a later release when we know it has been populated. The
``dest_compute_id`` field in ``Migration`` will be used if present, and if not,
a fallback to finding the node's ID will rely on a call to
``ComputeNode.get_by_host_and_nodename()``, which is "easy" since the
``Migration`` has all the fields necessary to make that call.

Alternatives
------------

This is not *required* for proper operation, so we could choose to do nothing.

We could also choose to keep the string-based association, strengthened by
Foreign Key relationships.

For the ``Migration`` changes, we could also make the destination compute ID
be a new RPC parameter that is passed from the destination compute back to the
source to avoid needing to change the ``Migration`` object. However that
brings with it more upgrade concerns.

We could also use the ``ComputeNode.uuid`` on the ``Migration`` object instead
of the ID. There is no real reason to do that because cross-cell migration
already creates two migration objects, one per cell. It would also perform
worse and would not be a 1:1 mapping of the field we need to set on the
instance, which would mean another DB lookup as well.

Data model impact
-----------------

All changes will be confined to the Cell database:

* Instance will grow a ``compute_id`` field
* Migration will grow a ``dest_compute_id`` field
* Consistency checks for both of these will need to be added to the object
  lifecycle operations.
* ComputeNode's existing ``service_id`` field will be populated
* Both will be populated during new record creation, and for existing records
  at runtime during ``nova-compute`` startup.

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

While not the primary intent, a follow-on effort to this will enable querying
these objects by integer ID relation instead of by string, which should be
both faster as well as lower impact on the database server.

Other deployer impact
---------------------

No additional deployer impact other than a tiny amount of online data
migration traffic on the next startup after upgrade, as well as improved
performance and robustness going forward once the effort is completed.

Developer impact
----------------

Some additional re-learning about the relationships between the objects being
based on IDs instead of hostnames.

Upgrade impact
--------------

No real upgrade impact here, other than what is already expected. A simple and
database migration will be added, with no specific requirements about ordering
or simultaneous code change. Compute nodes will migrate existing records during
the first post-upgrade restart.

Implementation
==============

Assignee(s)
-----------

Primary assignee:
  danms

Work Items
----------

* Start populating ``ComputeNode.service_id`` on creation
* Migrate existing ``ComputeNode`` objects on startup (``init_host()``)
* Add a migration to add the ``Instance.compute_id`` and
  ``Migration.dest_compute_id`` fields
* Start populating ``Migration.dest_compute_id`` for migrations
* Start populating ``Instance.compute_id`` on completion of scheduling and
  migrations.
* Migrate existing ``Instance`` objects on startup (``_init_instance()``)

Dependencies
============

None

Testing
=======

Unit and Functional tests will be added to verify that new and existing objects
are properly linked and migrated.

Documentation Impact
====================

No documentation changes required.

References
==========

- This is part of a larger multi-cycle effort to
  `robustify compute hostnames`_.
- This follows the `first robustification stage`_, completed in ``2023.1``

.. _`robustify compute hostnames`: https://specs.openstack.org/openstack/nova-specs/specs/backlog/approved/robustify-compute-hostnames.html
.. _`first robustification stage`: https://specs.openstack.org/openstack/nova-specs/specs/2023.1/approved/stable-compute-uuid.html

History
=======

.. list-table:: Revisions
   :header-rows: 1

   * - Release Name
     - Description
   * - 2023.2 Bobcat
     - Introduced
