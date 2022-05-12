..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

=================================
`socket` PCI NUMA affinity Policy
=================================

https://blueprints.launchpad.net/nova/+spec/pci-socket-affinity

Nova's current support for NUMA affinity for PCI devices is limited in the
kinds of affinity that it can express. Either a PCI device has affinity for a
NUMA node, or no affinity at all. This makes one of two assumptions about the
underlying host NUMA topology. Either there is only a single NUMA node per
socket, or - for cluster on die topologies with multiple nodes per socket -
there are enough CPUs in each NUMA node to fit reasonably large VMs that
require strict PCI NUMA affinity. The latter assumption is no longer true, and
Nova needs a more nuanced way to express PCI NUMA affinity.


Problem description
===================

Consider a guest with 16 CPUs and a PCI device, and a `require` PCI
NUMA affinity policy. Such a policy requires the guest to "fit" entirely into
the host NUMA node to which the PCI device is affined. Until recently, this was
a reasonnable expectation: more than 16 CPUs per NUMA node was the norm, even
in hosts with multiple NUMA nodes per socket.

With more recent hardware like AMD's Zen2 architecture, this is no longer the
case. Depending on the BIOS configuration, there could be as little as 8 CPUs
per NUMA node. This effectively makes a 16-CPU guest with a `require` PCI
device un-schedulable, as no host NUMA node can fit the entire guest.

.. seealso:: Zen2 BIOSes have a L3AsNUMA configuration option, which creates a
   NUMA node for every level 3 cache. Up to 4 cores can share an L3 cache, with
   2 SMT threads per core. This is how the number 8 was arrived at. See the AMD
   Developer Documentation [1]_ for more details.

Use Cases
---------

As an NFV cloud operator, I want to make full use of my hardware (AMD Zen2, or
Intel with cluster on die enabled) with minimal performance penalties.


Proposed change
===============

This spec proposes a new value for the ``hw:pci_numa_affinity_policy`` (and the
``hw_pci_numa_affinity_policy`` image property). The value is ``socket``, and
it indicates that the instance's PCI device has to be affined to the same
socket as the host CPUs that it is pinned to. If no such devices are available
on any compute hosts, the instance fails to schedule. In that sense, ``socket``
is the same as ``require``, except the PCI device must belong to the same
socket, rather than the same host NUMA node. In the case of multiple NUMA
nodes, the PCI device must belong to the same socket as *one* of the NUMA
nodes.

To better understand the new policy, consider some examples.

In the following oversimplified diagram, an instance with ``hw_numa_nodes=1``
and ``hw_pci_numa_affinity_policy=socket`` can be pinned to NUMA node N0 or N1,
but not N2 or N3

::

  +----------+         +----------+
  | N0    N1 |         | N2    N3 |
  |          +---PCI   |          |
  | Socket 0 |         | Socket 1 |
  +----------+         +----------+

Remaining with the same diagram, if the instance has ``hw_numa_nodes=2``
instead, it can be pinned to the following, as they all have at least one guest
NUMA node pinned to the PCI device's socket.

* N0 and N1
* N0 and N2
* N0 and N3
* N1 and N2
* N1 and N3

The instance cannot be pinned to N2 and N3, as they're both on a different
socket from the PCI device.

The implementation requires knowing the socket affinity of host CPUs and PCI
devices. For CPUs, the libvirt driver obtains that information from libvirt's
host capabilities and saves it in a new field in the ``NUMACell`` object. For
PCI devices, the existing ``PCIDevice.numa_node`` field can be used to look up
the corresponding ``NUMACell`` object and obtain its socket affinity.

The socket affinity information is then used in
hardware.py's ``numa_fit_instance_to_host()``, specifically when it calls down
to the PCI manager's ``support_requests()``.

Alternatives
------------

There are no alternatives with a similar level of simplicity. A more complex
model could include numeric NUMA distances and/or PCI root complex electrical
connection vs memory mapping affinity.

At the implementation level, an alternative to looking up the PCI device socket
affinity every time is to save it in a new field in the ``PCIDevice`` object.
This is ruled out because it adds a database migration, and is less flexible
and future-proof.

Another alternative for the same purpose is to use the ``extra_info`` field in
``PCIDevice``. It is a JSON blob that can accept arbitrary new entries. One of
the original purposes of Nova objects was to avoid unversioned dicts flying
over the wire. Relying on JSON blobs inside objects goes against this. In
addition, socket affinity is applicable to all PCI devices, and so does not
belong in a device-specific ``extra_info`` dict.

Data model impact
-----------------

* A ``socket`` integer field is added to the ``NUMACell`` object. No database
  changes are necessary here, as the object is stored as a JSON blob. The field
  is populated at runtime by the libvirt driver.

REST API impact
---------------

No API changes per se, and definitely no new microversion. A new ``socket``
value is added to the list of possible values for the
``hw:pci_numa_affinity_policy`` flavor extra spec and the
``hw_pci_numa_affinity_policy`` image property. The flavor extra spec
validation logic is extended to support the new value.

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

There is minimal impact on Nova performance. Documentation on the performance
impact of using the new ``socket`` NUMA affinity policy on various
architectures may be necessary.

Other deployer impact
---------------------

None.

Developer impact
----------------

Only the libvirt driver supports PCI NUMA affinity policies. This spec builds
on that support.

Upgrade impact
--------------

The current (pre-Wallaby) implementation of ``_filter_pools_for_numa_cells()``
recognizes ``required``, ``preferred`` and ``legacy`` as values for
``hw_pci_numa_affinity_policy``, with the latter being the catch-all default.
Therefore, instances with ``hw_pci_numa_affinity_policy=socket`` cannot be
permitted to land on pre-Wallaby compute hosts: the ``socket`` value would not
be recognized, and they would be incorrectly treated as having the
``legacy`` value.

To ensure that only Wallaby compute hosts receive instances with
``hw_pci_numa_affinity_policy=socket``, a new trait is reported by the Wallaby
libvirt driver to indicate that it supports the new policy. A corresponding
request pre-filter is added.


Implementation
==============

Assignee(s)
-----------

Primary assignee:
  notartom

Feature Liaison
---------------

Feature liaison:
  stephenfin

Work Items
----------

* Add a ``socket`` integer field to the ``NUMACell`` object.
* Libvirt driver starts populating the new ``NUMACell.socket`` field.
* Modify ``PciDeviceStats._filter_pools()``, as called by
  ``PciDeviceStats.support_requests()``, to support the new ``socket``
  NUMA affinity policy.
* Add COMPUTE_SOCKET_NUMA_AFFINITY trait (name can be adjusted during
  implementation) and corresponding pre-filter.
* Extend the flavor extra spec validation to allow the new ``socket`` value.


Dependencies
============

None.


Testing
=======

While there are aspirations for AMD Zen2 hardware in a third party CI, that is
too far in the future to have any impact on this spec. Functional tests will
have to do.


Documentation Impact
====================

The behavior of the new ``socket`` NUMA affinity policy will be documented.
Documentation on the performance impact of using the new ``socket`` NUMA
affinity policy on various architectures may be necessary.


References
==========

.. [1] `Socket SP3 Platform NUMA TopologyforAMD Family 17h
   Models30h–3Fh
   <http://developer.amd.com/wp-content/resources/56338_1.00_pub.pdf>`_


History
=======

.. list-table:: Revisions
   :header-rows: 1

   * - Release Name
     - Description
   * - Wallaby
     - Introduced
