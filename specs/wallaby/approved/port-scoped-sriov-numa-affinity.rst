..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

=========================================
Port Scoped SR-IOV NUMA Affinity Policies
=========================================

https://blueprints.launchpad.net/nova/+spec/port-scoped-sriov-numa-affinity

In the Ussuri release [1]_ support was added to allow PCI NUMA affinity
policies to be specified via flavor or image. This work builds on a previous
feature introduced in the Ussuri release and extends the granularity to allow
per neutron port NUMA affinity policies.

Problem description
===================

In some environments the server form factor is restricted, preventing PCI
devices from being physically installed across all NUMA nodes on a server,
e.g. high density blade/multi server systems or non standard form factor
equipment. In the Ussuri release operators gained the flexibility to specify
a VM-wide NUMA affinity policy via the flavor or image however in many cases
different NICs have different constraint.

Use Cases
---------

As an operator deploying openstack on high density or restricted form factor
hardware, I wish to specify a per-port NUMA affinity policy for SR-IOV devices
that differs form the VM-wide pci NUMA affinity policy.

As a tenant or VNF vendor, I want to be able to customize the affinity of
network interfaces, based on their usage. i.e. strict affinity for dataplane
interfaces and no affinity for management interfaces.

As an operator I wish to utilize NUMA-aware vSwitches but still be able to
disable it for individual VM interfaces.

Proposed change
===============

Per interface NUMA affinity polices have been introduced via a neutron
API extension [2]_. The neutron API extension introduces a new port attribute
which holds the requested affinity policy. Port NUMA affinity policies will
have a higher precedence than flavor,image or config based policy
specifications. As a result the precedence relationship will be
port > image/flavor > PCI alias.

This will enable operators to specify a default affinity policy per PCI alias,
this in turn can be overriden per VM via the flavor and image and finally the
NIC affinity can be refined via the per port policy.

The flavor- and image-based approach covers 80% of the use cases
enabled by per-interface NUMA affinity polices without requiring neutron API
changes. Now that the neutron API has been enhanced to support port NUMA
affinity policies this spec can address the final 20% of usecases.

.. note::

  This spec will address NUMA affinity for NUMA instance only. If a VM would
  not otherwise have a NUMA topology, a per port NUMA affinity policy will
  not make the instance a NUMA instance. This feature will support both SR-IOV
  NUMA affinity and NUMA aware vswitches but will not apply to cyborg managed
  interfaces.

To assist with scheduling a new compute capability trait
COMPUTE_NET_NUMA_AFFINITY will be added. The libvirt driver will be modified
to report this trait if it is configured with either SR-IOV network interfaces
via the PCI passthough whitelist or NUMA aware vswitches.

A prefilter will be added to append a required traits request to the unnamed
traits group when a port NUMA affinity policy is present. This is required
to the required the strict affinity policy ``require`` for NUMA deployments
that use NUMA aware vswitches.

The neutron api extension [2]_ will be update to support the newly added
socket pci affinity policy [3].

Alternatives
------------

None

Data model impact
-----------------

The ``nova.network.model.VIF`` object will be extended with a NUMA affinity
policy. While this is stored in the database, it is stored as a json blob
in the network info cache so it will not alter the schema or rpc objects.

REST API impact
---------------

There will be no direct changes to any existing API in Nova. However,
a new API extension [2]_ has been added to neutron to store the port
NUMA affinity policy.

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

As the scheduler already supports PCI affinity adding a new way to
pass the PCI policy should have no effect on scheduling performance.

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

The socket NUMA affinity policy depends on [3]_.
The only other dependency is on extending the request spec
object to store the requested networks. This is part
of the routed networks spec [4]_ implemented by [5]_.

Testing
=======

As this feature relates to SR-IOV it cannot be tested in the upstream gate
via tempest. Unit tests will be provided to assert that the policy
is correctly conveyed to the existing PCI assignment code and the existing
functional test can be extended as required. As this feature simply provides
another way to specify the PCI affinity policy the code change is minimal and
can leverage much of the existing test coverage. The most important thing to
assert is the precedence relationship of polices between config, flavor, image
and port.


Documentation Impact
====================

A release note and updates to the networking docs will be provided.

References
==========

.. [1] https://specs.openstack.org/openstack/nova-specs/specs/ussuri/implemented/vm-scoped-sriov-numa-affinity.html
.. [2] https://specs.openstack.org/openstack/neutron-specs/specs/victoria/port-numa-affinity-policy.html
.. [3] https://specs.openstack.org/openstack/nova-specs/specs/wallaby/approved/pci-socket-policy.html
.. [4] https://specs.openstack.org/openstack/nova-specs/specs/wallaby/approved/routed-networks-scheduling.html
.. [5] https://review.opendev.org/c/openstack/nova/+/749977

History
=======

.. list-table:: Revisions
   :header-rows: 1

   * - Release Name
     - Description
   * - Wallaby
     - Introduced
