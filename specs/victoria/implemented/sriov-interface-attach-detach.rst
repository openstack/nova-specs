..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

=========================================
Support SRIOV interface attach and detach
=========================================

https://blueprints.launchpad.net/nova/+spec/sriov-interface-attach-detach

Nova supports booting servers with SRIOV interfaces. However, attaching and
detaching an SRIOV interface to an existing server is not supported as the PCI
device management is missing from the attach and detach code path.


Problem description
===================

SRIOV interfaces cannot be attached or detached from an existing nova server.

Use Cases
---------

As an end user I need to connect my server to another neutron network via an
SRIOV interface to get high throughput connectivity to that network direction.

As an end user I want to detach an existing SRIOV interface as I don't use that
network access anymore and I want to free up the scarce SRIOV resource.

Proposed change
===============

In the compute manager, during interface attach, the compute needs to generate
``InstancePCIRequest`` for the requested port if the vnic_type of the port
indicates an SRIOV interface. Then run a PCI claim on the generated PCI request
to check if there is a free PCI device, claim it, and get a ``PciDevice``
object. If this is successful then connect the PCI request to the
``RequestedNetwork`` object and call Neutron as today with that
``RequestedNetwork``. Then call the virt driver as of today.

If the PCI claim fails then the interface attach instance action will fail but
the instance state will not be set to ERROR.

During detach, we have to recover the PCI request from the VIF being destroyed
then from that, we can get the PCI device that we need to unclaim in the PCI
tracker.

Note that detaching an SRIOV interface succeeds today from API user
perspective. However, the detached PCI device is not freed from resource
tracking and therefore leaked until the nova server is deleted or live
migrated. This issue will be gone when the current spec is implemented. Also
as a separate bugfix SRIOV detach will be blocked on stable branches to prevent
the resource leak.

There is a separate issue with SRIOV PF detach due to the way the libvirt
domain XML is generated. While the fix for that is needed for the current spec,
it also needed for the existing SRIOV live migration feature because that also
detaches the SRIOV interfaces during the migration. So the SRIOV PF detach
issue will be fixed as an independent bugfix of the SRIOV live migration
feature and the implementation of this spec will depend on that bugfix.

Alternatives
------------

None

Data model impact
-----------------

None

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

There will be an extra neutron call during interface attach as well as
additional DB operations. The ``interface_attach`` RPC method is synchronous
today, so this will be an end user visible change.

Other deployer impact
---------------------

None

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
  balazs-gibizer


Feature Liaison
---------------

Feature liaison:
  gibi


Work Items
----------

* change the attach and detach code path
* add unit and functional tests
* add documentation


Dependencies
============

None


Testing
=======

Tempest test cannot be added since the upstream CI does not have SRIOV devices.
Functional tests with libvirt driver will be added instead.


Documentation Impact
====================

* remove the limitation from the API documentation

References
==========

None

History
=======

.. list-table:: Revisions
   :header-rows: 1

   * - Release Name
     - Description
   * - Victoria
     - Introduced
