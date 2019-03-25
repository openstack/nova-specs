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

.. note:: In the following paragraphs the term NUMA is incorrectly used to
   signify any guest characteristic that is expressed in the
   ``InstanceNUMATopology`` object, for example CPU pinning and hugepages. CPU
   pinning can be achieved without a guest NUMA topology, but the two concepts
   are unfortunately tightly coupled in Nova and instance pinning is not
   possible without an instance NUMA topology.  For this reason, NUMA is used
   as a catchall term.

.. note:: This spec concentrates on the libvirt driver. Any higher level code
   (compute manager, conductor) will be as driver agnostic as possible.

The problem can best be described with three examples.

The first example is live migration with CPU pinning. An instance with a
``hw:cpu_policy=dedicated`` `extra spec
<https://docs.openstack.org/nova/latest/user/flavors.html#extra-specs-cpu-policy>`_
and pinned CPUs is live-migrated.  Its pin mappings are naively copied over to
the destination host. This creates two problems.  First, its pinned pCPUs
aren't properly claimed on the destination.  This means that, should a second
instance with pinned CPUs land on the destination, both instances' vCPUs could
be pinned to the same pCPUs. Second, any existing pin mappings on the
destination are ignored. If another instance already exists on the destination,
both instances's vCPUs could be pinned to the same pCPUs. In both cases, the
``dedicated`` CPU policy is violated, potentially leading to unpredictable
performance degradation.

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

The first two of these examples are known bugs [1]_ [2]_.

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

There are five aspects to supporting NUMA live migration. First, the instance's
NUMA characteristics need to be recalculated to fit on the new host. Second,
the resources that the instance will consume on the new host need to be
claimed. Third, information about the instance's new NUMA characteristics needs
to be generated on the destination (an ``InstanceNUMATopolgy`` object is not
enough, more on that later). Fourth, this information needs to be sent from
the destination to the source, in order for the source to generate the correct
XML for the instance to be able to run on the destination. Finally, the
instance's resource claims need to "converge" to reflect the success or failure
of the live migration. If the live migration succeeded, the usage on the source
needs to be released. If it failed, the claim on the destination needs to be
rolled back.

Resource claims
---------------

Let's address the resource claims aspect first. An effort has begun to support
NUMA resource providers in placement [3]_ and to standardize CPU resource
tracking [4]_. However, placement can only track inventories and allocations of
quantities of resources. It does not track which specific resources are used.
Specificity is needed for NUMA live migration. Consider an instance that uses
4 dedicated CPUs in a future where the standard CPU resource tracking spec [4]_
has been implemented. During live migration, the scheduler claims those 4 CPUs
in placement on the destination. However, we need to prevent other instances
from using those specific CPUs. Therefore, in addition to claiming quantities
of CPUs in placement, we need to claim specific CPUs on the compute host. The
compute resource tracker already exists for exactly this purpose, and it will
continue to be used to claim specific resources on the destination, even in a
NUMA-enabled placement future.

There is a time window between the scheduler picking a destination for the live
migration and the actual live migration RPC conversation between the two
compute hosts. Another instance could land on the destination during that time
window, using up NUMA resources that the scheduler thought were free. This race
leads to the resource claim failing on the destination. This spec proposes to
handle this claim failure using the existing ``MigrationPreCheckError``
exception mechanism, causing the scheduler to pick a new host.

Fitting to the new host
-----------------------

An advantage of using the resource tracker is that it forces us to use a
``MoveClaim``, thus giving us the instance new NUMA topology for free
(``Claim._test_numa_topology`` in ``nova/compute/claims.py``).

Generating the new NUMA information on the destination
------------------------------------------------------

However, having the new instance NUMA topology in the claim isn't enough for
the source to generate the new XML. The simplest way to generate the new XML
fom the new instance NUMA topology would be to call the libvirt driver's
``_get_guest_numa_config`` method (which handily accepts an
``instance_numa_topology`` as an argument). However, this needs to be done on
the destination, as it depends on the host NUMA topology.
``_get_guest_numa_config`` returns a tuple of ``LibvirtConfigObject``. The
information contained therein needs to somehow be sent to the source over the
wire.

The naive way would be to send the objects directly, or perhaps to call
``to_xml`` and send the resulting XML blob of text. This would be unversioned,
and there would be no schema. This could cause problems in the case of, for
example, a newer libvirt driver, which has dropped support for a particular
element or attribute, talking to an older libvirt driver, which still supports
it.

Because of this, and sticking to the existing OpenStack best practice of
sending oslo versionedobjects over the wire, this spec proposes encode the
necessary NUMA-related information as Nova versioned objects. These new objects
should be as virt driver independent as reasonnably possible, but as the use
case is still libvirt talking to libvirt, abstraction for the sake of
abstraction is not appropriate either.

Sending the new NUMA Nova objects
---------------------------------

Once the superconductor has chosen and/or validated the destination host, the
relevant parts of the current live migration flow can be summarized by the
following oversimplified pseudo sequence diagram.::

    +-----------+                           +---------+                        +-------------+ +---------+
    | Conductor |                           | Source  |                        | Destination | | Driver  |
    +-----------+                           +---------+                        +-------------+ +---------+
          |                                      |                                    |             |
          | check_can_live_migrate_destination() |                                    |             |
          |-------------------------------------------------------------------------->|             |
          |                                      |                                    |             |
          |                                      |    check_can_live_migrate_source() |             |
          |                                      |<-----------------------------------|             |
          |                                      |                                    |             |
          |                                      | migrate_data                       |             |
          |                                      |----------------------------------->|             |
          |                                      |                                    |             |
          |                                      |                       migrate_data |             |
          |<--------------------------------------------------------------------------|             |
          |                                      |                                    |             |
          | live_migration(migrate_data)         |                                    |             |
          |------------------------------------->|                                    |             |
          |                                      |                                    |             |
          |                                      | pre_live_migration(migrate_data)   |             |
          |                                      |----------------------------------->|             |
          |                                      |                                    |             |
          |                                      |                       migrate_data |             |
          |                                      |<-----------------------------------|             |
          |                                      |                                    |             |
          |                                      | live_migration(migrate_data)       |             |
          |                                      |------------------------------------------------->|
          |                                      |                                    |             |

In the proposed new flow, the destination compute manager asks the libvirt
driver to calculate the new ``LibvirtGuestConfig`` objects using the new
instance NUMA topology obtained from the move claim. The compute manager
converts those ``LibvirtGuestConfig`` objecs to the new NUMA Nova objects, and
adds them as fields to the ``LibvirtLiveMigrateData`` ``migrate_data`` object.
The latter eventually reaches the source libvirt driver, which uses it to
generate the new XML. The proposed flow is summarised in the following
diagram.::

    +-----------+                                             +---------+                       +-------------+                                          +---------+
    | Conductor |                                             | Source  |                       | Destination |                                          | Driver  |
    +-----------+                                             +---------+                       +-------------+                                          +---------+
          |                                                        |                                   |                                                      |
          | check_can_live_migrate_destination()                   |                                   |                                                      |
          |------------------------------------------------------------------------------------------->|                                                      |
          |                                                        |                                   |                                                      |
          |                                                        |   check_can_live_migrate_source() |                                                      |
          |                                                        |<----------------------------------|                                                      |
          |                                                        |                                   |                                                      |
          |                                                        | migrate_data                      |                                                      |
          |                                                        |---------------------------------->|                                                      |
          |                                                        |                                   | +-----------------------------------+                |
          |                                                        |                                   |-| Obtain new_instance_numa_topology |                |
          |                                                        |                                   | | from claim                        |                |
          |                                                        |                                   | +-----------------------------------+                |
          |                                                        |                                   |                                                      |
          |                                                        |                                   | _get_guest_numa_config(new_instance_numa_topology)   |
          |                                                        |                                   | ---------------------------------------------------->|
          |                                                        |                                   |                                                      |
          |                                                        |                                   |                           LibvirtConfigGuest objects |
          |                                                        |                                   |<-----------------------------------------------------|
          |                                                        |                                   |                                                      |
          |                                                        |                                   | +----------------------------------+                 |
          |                                                        |                                   |-| Build new NUMA Nova objects from |                 |
          |                                                        |                                   | | LibvirtConfigGuest objects       |                 |
          |                                                        |                                   | | and add to migrate_data          |                 |
          |                                                        |                                   | +----------------------------------+                 |
          |                                                        |                                   |                                                      |
          |                                                       migrate_data + new NUMA Nova objects |                                                      |
          |<-------------------------------------------------------------------------------------------|                                                      |
          |                                                        |                                   |                                                      |
          | live_migration(migrate_data + new NUMA Nova objects)   |                                   |                                                      |
          |------------------------------------------------------->|                                   |                                                      |
          |                                                        |                                   |                                                      |
          |                                                        |              pre_live_migration() |                                                      |
          |                                                        |---------------------------------->|                                                      |
          |                                                        |<----------------------------------|                                                      |
          |                                                        |                                   |                                                      |
          |                                                        | live_migration(migrate_data + new NUMA Nova objects)                                     |
          |                                                        |----------------------------------------------------------------------------------------->|
          |                                                        |                                   |                                                      |
          |                                                        |                                   |                +-----------------------------------+ |
          |                                                        |                                   |                | generate NUMA XML for destination |-|
          |                                                        |                                   |                +-----------------------------------+ |
          |                                                        |                                   |                                                      |


Claim convergence
-----------------

The claim object is a context manager, so it can in theory clean itself up if
any code within its context raises an unhandled exception. However, live
migration involves RPC casts between the compute hosts, making it impractical
to use the claim as a context manager. For that reason, if the live migration
fails, ``drop_move_claim`` needs to be called manually during the rollback to
drop the claim from the destination.  Whether to do this on the source in
``rollback_live_migration`` or in ``rollback_live_migration_at_destination`` is
left as an implementation detail.

Similarly, if the live migration succeeds, ``drop_move_claim`` needs to be
called to drop the claim from the source, similar to how ``_confirm_resize``
does it in the compute manager. Whether to do this in ``post_live_migration``
on the source or in ``post_live_migration_at_destination`` is left as an
implementation detail.

Alternatives
------------

Using move claims and the new instance NUMA topology calculated within
essentially dictates the rest of the implementation.

When the superconductor calls the scheduler's ``select_destination`` method,
that call eventually ends up calling ``numa_fit_instance_to_host``
(``select_destinations`` -> ``_schedule`` -> ``_consume_selected_host`` ->
``consume_from_request`` -> ``_locked_consume_from_request`` ->
``numa_fit_instance_to_host``). It would be conceivable to reuse that result.
However, the claim would still calculate its own new instance NUMA topology.

Data model impact
-----------------

New version objects are created to transmit cell, CPU, emulator thread, and
hugepage nodeset mappings from the destination to the source. These objects are
added to ``LibvirtLiveMigrateData``.

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

Upgrade impact
--------------

In the case of a mixed N/N+1 cloud, the possibilities for the exchange of
information between the destination and the source are summarized in the
following table. In it, **no** indicates that the new code is not present,
**old path** indicates that the new code is present but choses to execute the
old code for backwards compatibility, and **yes** indicates that the new
functionality is used.

.. list-table:: Mixed N/N+1 cloud
   :widths: 10 45 45
   :stub-columns: 1
   :header-rows: 1

   * -
     - Old dest
     - New dest
   * - Old source
     - +----------------------------------+----------+
       | New NUMA objects from dest       | no       |
       +----------------------------------+----------+
       | New XML from source              | no       |
       +----------------------------------+----------+
       | Initial claim on dest            | no       |
       +----------------------------------+----------+
       | Claim drop for source on success | no       |
       +----------------------------------+----------+
       | Claim drop for dest on failure   | no       |
       +----------------------------------+----------+
     - +----------------------------------+----------+
       | New NUMA objects from dest       | old path |
       +----------------------------------+----------+
       | New XML from source              | no       |
       +----------------------------------+----------+
       | Initial claim on dest            | old path |
       +----------------------------------+----------+
       | Claim drop for source on success | no       |
       +----------------------------------+----------+
       | Claim drop for dest on failure   | old path |
       +----------------------------------+----------+
   * - New source
     - +----------------------------------+----------+
       | New NUMA objects from dest       | no       |
       +----------------------------------+----------+
       | New XML from source              | old path |
       +----------------------------------+----------+
       | Initial claim on dest            | no       |
       +----------------------------------+----------+
       | Claim drop for source on success | old path |
       +----------------------------------+----------+
       | Claim drop for dest on failure   | no       |
       +----------------------------------+----------+
     - +----------------------------------+----------+
       | New NUMA objects from dest       | yes      |
       +----------------------------------+----------+
       | New XML from source              | yes      |
       +----------------------------------+----------+
       | Initial claim on dest            | yes      |
       +----------------------------------+----------+
       | Claim drop for source on success | yes      |
       +----------------------------------+----------+
       | Claim drop for dest on failure   | yes      |
       +----------------------------------+----------+

Implementation
==============

Assignee(s)
-----------

Primary assignee:
  notartom

Work Items
----------

* Fail live migration of instances with NUMA topology [5]_ until this spec is
  fully implemented.
* Add NUMA Nova objects
* Add claim context to live migration
* Calculate new NUMA topology on the destination and send it to the source
* Source updates instance XML according to new NUMA topology calculated by the
  destination

Dependencies
============

None.

Testing
=======

The libvirt/qemu driver used in the gate does not currently support NUMA
features (though work is in progress [6]_). Therefore, testing NUMA aware
live migration in the upstream gate would require nested virt. In addition, the
only assertable outcome of a NUMA live migration test (if it ever becomes
possible) would be that the live migration succeeded. Examining the instance
XML to assert things about its NUMA affinity or CPU pin mapping is explicitly
out of tempest's scope. For these reasons, NUMA aware live migration is best
tested in third party CI [7]_ or other downstream test scenarios [8]_.

Documentation Impact
====================

Current live migration documentation does not mention the NUMA limitations
anywhere. Therefore, a release note explaining the new NUMA capabilities of
live migration should be enough.

References
==========

.. [1] https://bugs.launchpad.net/nova/+bug/1496135
.. [2] https://bugs.launchpad.net/nova/+bug/1607996
.. [3] https://review.openstack.org/#/c/552924/
.. [4] https://review.openstack.org/#/c/555081/
.. [5] https://review.openstack.org/#/c/611088/
.. [6] https://review.openstack.org/#/c/533077/
.. [7] https://github.com/openstack/intel-nfv-ci-tests
.. [8] https://review.rdoproject.org/r/gitweb?p=openstack/whitebox-tempest-plugin.git

[9] https://review.openstack.org/#/c/244489/

History
=======

.. list-table:: Revisions
   :header-rows: 1

   * - Release Name
     - Description
   * - Rocky
     - Introduced
   * - Stein
     - Re-proposed with modifications pertaining to claims and the exchange of
       information between destination and source.
