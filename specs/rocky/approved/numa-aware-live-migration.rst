..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

=========================
NUMA-aware live migration
=========================

https://blueprints.launchpad.net/nova/+spec/numa-aware-live-migration

When an instance with NUMA characteristics is live-migrated, those
characteristics are not recalculated on the destination compute host. In the
CPU pinning case, using the source host's pin mappings on the destination can
lead to multiple instances being pinned to the same pCPUs. In the case of
hugepage-backed instances, which are NUMA-localized, an instance needs to have
its NUMA mapping recalculated on the destination compute host during a live
migration.

Problem description
===================

In the following paragraphs the term NUMA is incorrectly used to signify any
guest characteristic that is expressed in the `InstanceNUMATopology` object,
for example CPU pinning and hugepages. CPU pinning can be achieved without a
guest NUMA topology, but because no better term than NUMA is available it will
continue to be used.

The problem can best be described with three examples.

The first example is live migration with CPU pinning. An instance with a
``dedicated`` CPU policy and pinned CPUs is live-migrated.  Its pin mappings
are naively copied over to the destination host. This creates two problems.
First, its pinned pCPUs aren't properly claimed on the destination. This means
that, should a second instance with pinned CPUs land on the destination, both
instances' vCPUs could be pinned to the same pCPUs. Second, any existing pin
mappings on the destination are ignored. If another instance already exists on
the destination, both instances's vCPUs could be pinned to the same pCPUs. In
both cases, the ``dedicated`` CPU policy is violated, potentially leading to
unpredictable performance degradation.

The second example is instances with hugepages. There are two hosts, each with
two NUMA nodes and 8 1GB hugepages per node. Two identical instances are booted
on the two hosts. Their virtual NUMA topology is one virtual NUMA node and 8
1GB memory pages. They land on their respective host's NUMA node 0, consuming
all 8 of its pages. One instance is live-migrated to the other host. The
libvirt driver enforces strict NUMA affinity and does not regenerate the
instance XML. Both instances end up on the hosts NUMA node 0, and the
live-migrated instance fails to run.

The third example is an instance with a virtual NUMA topology (but without
hugepages). If an instance affined to its host's NUMA node 2 is live migrated
to a host with only two NUMA nodes, and thus without a NUMA node 2, it will
fail to run.

The first two of these examples are known bugs `[1]`_ `[2]`_.

Use Cases
---------

As a cloud administrator, I want to live migrate instances with CPU pinning
without the pin mappings overlapping on the destination compute host.

As a cloud administrator, I want live migration of hugepage-backed instances to
work and for the instances to successfully run on the destination compute host.

As a cloud administrator, I want live migration of instances with an explicit
NUMA topology to work and for the instances to successfully run on the
destination compute host.

Proposed change
===============

Currently, the scheduler does not claim any NUMA resources. While work has
started to model NUMA topologies as resources providers in placement `[3]`_,
this spec intentionally ignores that work and does not depend on it. Instead,
the current method of claiming NUMA resources will continue to be used.
Specifically, NUMA resources will continue to be claimed by the compute host's
resource tracker.

At the cell conductor (live migration isn't supported between cells, so the
superconductor is not involved) and compute level, the relevant parts of the
current live migration flow can be summarized by the following oversimplified
pseudo sequence diagram.::

    +-----------+                        +---------+                             +-------------+ +---------+
    | Conductor |                        | Source  |                             | Destination | | Driver  |
    +-----------+                        +---------+                             +-------------+ +---------+
          |                                   |                                         |             |
          | check_can_live_migrate_destination|                                         |             |
          |---------------------------------------------------------------------------->|             |
          |                                   |                                         |             |
          |                                   |           check_can_live_migrate_source |             |
          |                                   |<----------------------------------------|             |
          |                                   |                                         |             |
          |                                   | migrate_data                            |             |
          |                                   |---------------------------------------->|             |
          |                                   |                                         |             |
          |                                   |                            migrate_data |             |
          |<----------------------------------------------------------------------------|             |
          |                                   |                                         |             |
          | live_migration(migrate_data)      |                                         |             |
          |---------------------------------->|                                         |             |
          |                                   |                                         |             |
          |                                   | pre_live_migration(migrate_data)        |             |
          |                                   |---------------------------------------->|             |
          |                                   |                                         |             |
          |                                   |                            migrate_data |             |
          |                                   |<----------------------------------------|             |
          |                                   |                                         |             |
          |                                   | live_migration(migrate_data)            |             |
          |                                   |------------------------------------------------------>|
          |                                   |                                         |             |

`migrate_data` is a LiveMigrateData object. This spec proposes to add an object
field containing an `InstanceNUMATopology` object. The source will include the
instance's existing NUMA topology in the `migrate_data` that its
`check_can_live_migrate_source` returns to the destination. The destination's
virt driver will fit this `InstanceNUMATopology` to the destination's
`NUMATopology` and claim the resources using the resource tracker. It will then
send the updated `InstanceNUMATopology` back to the conductor as part of the
existing `migrate_data` that `check_can_live_migrate_destination` returns. The
updated `InstanceNUMATopology` will continue to be propagated as part of
`migrate_data`, eventually reaching the source. The source's libvirt driver
will use this updated `InstanceNUMATopology` when generating the instance XML
to be sent to the destination for the live migration. The proposed flow is
summarised in the following diagram.::

    +-----------+                                                   +---------+                                +-------------+                                      +---------+
    | Conductor |                                                   | Source  |                                | Destination |                                      | Driver  |
    +-----------+                                                   +---------+                                +-------------+                                      +---------+
          |                                                              |                                            |                                                  |
          | check_can_live_migrate_destination                           |                                            |                                                  |
          |---------------------------------------------------------------------------------------------------------->|                                                  |
          |                                                              |                                            |                                                  |
          |                                                              |              check_can_live_migrate_source |                                                  |
          |                                                              |<-------------------------------------------|                                                  |
          |                                                              |                                            |                                                  |
          |                                                              | migrate_data + InstanceNUMATopology        |                                                  |
          |                                                              |------------------------------------------->|                                                  |
          |                                                              |                                            | --------------------------------------------\    |
          |                                                              |                                            |-| Fit InstanceNUMATopology to NUMATopology, |    |
          |                                                              |                                            | | fail live migration if unable             |    |
          |                                                              |                                            | |-------------------------------------------|    |
          |                                                              |    migrate_data + new InstanceNUMATopology |                                                  |
          |<----------------------------------------------------------------------------------------------------------|                                                  |
          |                                                              |                                            |                                                  |
          | live_migration(migrate_data + new InstanceNUMATopology)      |                                            |                                                  |
          |------------------------------------------------------------->|                                            |                                                  |
          |                                  --------------------------\ |                                            |                                                  |
          |                                  | pre_live_migration call |-|                                            |                                                  |
          |                                  |-------------------------| |                                            |                                                  |
          |                                                              |                                            |                                                  |
          |                                                              | live_migration(migrate_data + new InstanceNUMATopology)                                       |
          |                                                              |---------------------------------------------------------------------------------------------->|
          |                                                              |                                            |            ------------------------------------\ |
          |                                                              |                                            |            | generate NUMA XML for destination |-|
          |                                                              |                                            |            |-----------------------------------| |
          |                                                              |                                            |                                                  |

Exchanging instance NUMA topologies is done early (in
`check_can_live_migrate_source` rather than `pre_live_migration`) in order to
fail as fast as possible if the destination cannot fit the instance. What
happens when the compute hosts are not both running the updated handshake code
is discussed in ref:`upgrade-impact`.

Currently, only placement allocations are updated during a live migration. The
proposed resource tracker claims mechanism will become obsolete once NUMA
resource providers are implemented `[3]`_. Therefore, as a stopgap error
handling method, the live migration can be failed if the resource claim does
not succeed on the destination compute host. Once NUMA is handled by placement,
the compute host will not have to do any resource claims.

It would also be possible for another instance to steal NUMA resources from a
live migrated instance before the latter's destination compute host has a
chance to claim them. Until NUMA resource providers are implemented `[3]`_ and
allow for an essentially atomic schedule+claim operation, scheduling and
claiming will keep being done at different times on different nodes. Thus, the
potential for races will continue to exist.

Alternatives
------------

It would be possible to reuse the result of `numa_fit_instance_to_host` as
called from the scheduler before the live migration reaches the conductor.
`select_destinations` in the scheduler returns a list of `Selection` objects to
the conductor's live migrate task. The `Selection` object could be modified to
include `InstanceNUMATopology`. The NUMA topology filter could add an
`InstanceNUMATopology` for every host that passes. That topology would
eventually reach the conductor, which would put it in `migrate_data`. The
destination compute host would then claim the resources as previously
described.

Data model impact
-----------------

`InstanceNUMATopology` is added to `LiveMigrateData`.

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

None.

Developer impact
----------------

None.

.. _upgrade-impact:

Upgrade impact
--------------

None.

Hypothetically, how NUMA aware live migration could be supported between
version-mismatched compute hosts would depend on which of the two compute hosts
is older.

If the destination is older than the source, the source does not get an
`InstanceNUMATopology` in `migrate_data` and can therefore choose to
run an old-style live migration.

If the source is older than the destination, the new field in `LiveMigrateData`
is ignored and the source's old live migration runs without issues.  However,
the destination has already claimed NUMA resources that the source does
generate instance XML for. The destination could conceivably check the source's
compute service version and fail the migration before claiming resources if the
source doesn't support NUMA live migration.

However, given the current broken state of NUMA live migration, a simpler
solution is to refuse to perform a NUMA live migration unless both source and
destination compute hosts have been upgraded to a version that supports it. To
achieve this, the conductor can check the source and destination compute's
service version and fail the migration if either one is too old.

Implementation
==============

Assignee(s)
-----------

Primary assignee:
  notartom

Work Items
----------

* Add `InstanceNUMATopology` to `LiveMigrateData`.
* Modify the libvirt driver to generate live migration instance XML based on
  the `InstanceNUMATopolgy` in the `migrate_data` it receives from the
  destination.

Dependencies
============

None.

Testing
=======

The libvirt/qemu driver used in the gate does not currently support NUMA
features (though work is in progress `[4]`_). Therefore, testing NUMA aware
live migration in the upstream gate would require nested virt. In addition, the
only assertable outcome of a NUMA live migration test (if it ever becomes
possible) would be that the live migration succeeded. Examining the instance
XML to assert things about its NUMA affinity or CPU pin mapping is explicitly
out of tempest's scope. For these reasons, NUMA aware live migration is best
tested in third party CI `[5]`_ or other downstream test scenarios `[6]`_.

Documentation Impact
====================

Current live migration documentation does not mention the NUMA limitations
anywhere. Therefore, a release note explaining the new NUMA capabilities of
live migration should be enough.

References
==========

.. _[1]: https://bugs.launchpad.net/nova/+bug/1496135
.. _[2]: https://bugs.launchpad.net/nova/+bug/1607996
.. _[3]: https://review.openstack.org/#/c/552924/
.. _[4]: https://review.openstack.org/#/c/533077/
.. _[5]: https://github.com/openstack/intel-nfv-ci-tests
.. _[6]: https://review.rdoproject.org/r/gitweb?p=openstack/whitebox-tempest-plugin.git

History
=======

.. list-table:: Revisions
   :header-rows: 1

   * - Release Name
     - Description
   * - Rocky
     - Introduced
