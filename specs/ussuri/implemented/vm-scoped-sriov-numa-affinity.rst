..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

=======================================
VM Scoped SR-IOV NUMA Affinity Policies
=======================================

https://blueprints.launchpad.net/nova/+spec/vm-scoped-sriov-numa-affinity

In the Queens release [1]_ support was added to allow PCI NUMA affinity
policies to be specified via PCI aliases. This work builds on a previous
feature introduced in the Juno release [2]_ that introduced strict NUMA
affinity for PCI devices; however, the Queens feature did not address
the NUMA affinity of neutron SR-IOV interfaces which were also enforced by
the original Juno enhancement. This spec seeks to provide a per-VM mechanism
to set a VM-wide NUMA afinity policy for all PCI passthrough devices,
including but not limited to neutron SR-IOV interfaces
(vnic_type=direct,direct-phyical,macvtap,virtio-forwarder)


Problem description
===================

In some environments the server form factor is restricted, preventing PCI
devices from being physically installed across all NUMA nodes on a server,
e.g. high density blade/multi server systems or non standard form factor
equipment. In such an environment the default legacy policy which is applied
to all neutron SR-IOV interfaces prevents VMs from using SR-IOV on a non local
NUMA node if the VM has a NUMA topology (uses cpu pinning, vPMEM, hugepages or
requests a NUMA topology explicitly).

To use a remote SR-IOV device via neutron ports in such an environment the
operator is forced to either configure the guest to have multiple NUMA nodes
or disable NUMA reporting on the host server. Both options pessimize the
performance of both the guest and host in different ways. While a VM with
multiple virtual NUMA nodes can outperform a VM with the same resources and a
single NUMA node in a memory bound workload, that is only true if the workload
is NUMA-aware. A two-node NUMA topology, if enforced on a workload that is not
NUMA-aware, can result in increased cross-NUMA traffic and result in a lower
throughput. Similarly while disabling NUMA reporting at the hardware level
is beneficial in some HPC workloads due to the increased memory bandwidth, it
comes at the cost of increased memory latency, making it unsuitable for
realtime workloads such as VOIP.

Use Cases
---------

As an operator deploying openstack on high density or restricted form factor
hardware, I wish to specify a per-VM NUMA affinity policy for SR-IOV devices
via standard flavor extra specs.

As a tenant or VNF vendor, I want to be able to customize the affinity of my
VMs via image properties so I can express the NUMA affinity requirements of
my workloads.

Proposed change
===============

This spec proposes extending the PCI NUMA affinity polices introduced
by [1]_ to all PCI and SR-IOV devices including neutron ports by adding a
new flavor extra spec ``hw:pci_numa_affinity_policy`` and
``hw_pci_numa_affinity_policy`` image metadata property.

The new properties will accept one of three values: ``required``, ``preferred``
and ``legacy`` as defined in [1]_. If a PCI device is requested using a flavor
alias, the NUMA affinity policy specified in the flavor or image will
take precedence over any policy set in the host PCI alias. If no
PCI NUMA affinity policy is specified in the flavor or image, alias based
PCI pass-through will fall back to the policy set in the alias. If no policy
is set in the flavor or image and no policy is set in the alias the legacy
policy will continue to be used. For neutron SR-IOV interfaces if no policy
is set in the flavor or image the legacy policy will be used.

.. NOTE::

  The Queens spec [1]_ originally contained both of the proposed flavor
  and image properties but were removed during implementation as the original
  neutron port usecase that motivated the feature was not captured in the spec.
  As a result, while the Queens feature addressed NUMA affinity for
  flavor-based PCI pass-through, no mechanism is available to specify the policy
  for neutron SR-IOV interfaces.


Alternatives
------------

We could change the default policy to ``preferred`` if no policy is specified.
This would optimize for cases where people do not care about NUMA affinity
at the expense of requiring those who do to specify a policy.
As this would be a change in behavior on upgrade it is not proposed that we
take this approach.

We could enable per-interface NUMA affinity polices. This is not mutually
exclusive with this proposal and will be proposed separately as an additional
feature. The flavor- and image-based approach covers 80% of the use cases
enabled by per-interface NUMA affinity polices without requiring neutron api
changes.

Data model impact
-----------------

The image metadata object and related notification objects will be updated
to contain the new PCI NUMA affinity field. As the PCI request spec object
already has a NUMA affinity policy field for alias-based pass-through, no
other data model changes are required.

REST API impact
---------------

There will be no direct changes to any existing API. However,
a new flavor extra spec will be introduced.

Security impact
---------------

None

Notifications impact
--------------------

The image metadata properties payload will be extended with the
new property field. No other impact is expected.

Other end user impact
---------------------

To utilize this feature operators and tenants will need to modify their
images and flavors to add the ``hw:pci_numa_affinity_policy`` and
``hw_pci_numa_affinity_policy``  properties.

Performance Impact
------------------

None

As the scheduler was already asserting legacy PCI affinity, passing
a policy to assert instead should not affect the overall scheduling time.
Depending on the policy selected the performance of the guest may improve
or be reduced inline with the guarantees expressed by that policy.

Other deployer impact
---------------------

As was previously required to enable NUMA affinity to be enforced for
SR-IOV/PCI devices, the PCI pass-through and NUMA topology filters must be
enabled.

Developer impact
----------------

None

Upgrade impact
--------------

None

Implementation
==============

Assignee(s)
-----------

Primary assignee:
  sean-k-mooney

Feature Liaison
---------------

Feature liaison:
  sean-k-mooney

Work Items
----------

None

Dependencies
============

None

Testing
=======

As this feature relates to SR-IOV it cannot be tested in the upstream gate
via tempest. Unit tests will be provided to assert that the policy
is correctly conveyed to the existing PCI assignment code and the existing
functional test can be extended as required.

As this feature simply provides another way to specify the PCI affinity policy
the code change is minimal and can leverage much of the existing test coverage.


Documentation Impact
====================

A release note and updates to the existing user flavor docs will be provided,
and the glance metadefs should be updated to reflect the new image property.

References
==========

.. [1] https://specs.openstack.org/openstack/nova-specs/specs/queens/implemented/share-pci-between-numa-nodes.html
.. [2] https://specs.openstack.org/openstack/nova-specs/specs/juno/approved/input-output-based-numa-scheduling.html

History
=======

.. list-table:: Revisions
   :header-rows: 1

   * - Release Name
     - Description
   * - Ussuri
     - Introduced
