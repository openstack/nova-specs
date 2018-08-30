..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

==========================================
Trusted Virtual Functions
==========================================

https://blueprints.launchpad.net/nova/+spec/sriov-trusted-vfs

In order to enable VF (SR-IOV virtual function) to request "trusted
mode", a new trusted VF concept was introduced in linux kernel 4.4
[5]_.

It allows Virtual Functions to become "trusted" by the Physical
Function and perform some privileged operations, such as enabling VF
promiscuous mode and changing VF MAC address within the guest. The
inability to modify MAC addresses in the guest prevents the users from
being able to easily set up two VFs in a fail-over bond in a
guest. This spec aims to suggest a way for users to boot instances
with trusted VFs.

Problem description
===================

By default, Virtual Functions have no privileges to perform certain
operations, such as enabling multicast promiscuous mode and modifying
the VF's MAC address in the guest. These security measures are
designed to prevent possible attacks, however, in some cases these
operations performed by a VF would be legitimate. OpenStack currently
doesn't provide an easy way for a user to boot an instance that uses
trusted VFs. As well as there is no easy way for cloud operators to
specify which PFs allow their VFs to become trusted.

Use Cases
---------

There are several use cases in which users would prefer to take
advantage of the trusted VFs. Bonding VFs in a guest would be one of
these. Bonding modes that require all slaves to use the same MAC
address, would require address modification on one of the VFs during a
fail-over. As MAC address altering is a privileged operation,
participating VFs should be trusted in order to successfully configure
bonding in the guest. [1]_

Proposed change
===============

The aim of this proposal is to provide a way for users to boot
instances with assigned SR-IOV VFs which will be configured as
trusted.

Cloud operators would have a manageable way to specify which PFs will
allow trusted VFs to be configured. The operators will be able to
select which PFs can have trusted VFs by adding an additional
parameter to the filter in nova.conf.

.. code::

   [pci]
   passthrough_whitelist = {"devname": "eth0",
                            "physical_network": "phy0",
                            "trusted": "true"}

In Neutron the ports will have to be created with a specific bindings
to request that we want enable trusted feature for the VF allocated.

.. code::

    neutron port-create <net-id> \
                        --name sriov_port \
                        --vnic-type direct \
                        --binding:profile type=dict trusted=true

NOTE: It's important to use the same boolean representation for the
value of the trusted tag due to a limitation in the representation of
the requests specs and tags for pools.

An instance requesting to boot with SRIOV VFs attached will have PCI
requests assigned. For ports attached to instances that are requesting
"trusted", the PCI requests will be enhanced by a tag "trusted".

During the scheduling phase the PciPassthroughtFilter is matching tags
from the PCI Requests with tags passed to the
`pci_passtrought_whitelist` that are used to determine whether or not
the instance is to be booted on a given host.

The virt drivers will then have to read the binding profile to check
whether the VFs assigned for an instance should have their trusted
mode activated. When destroying the instance, it's the responsibility
of virt drivers to update the VFs which have been assigned to
instances in their default state (trusted mode off).

Alternatives
------------

The operator could have to manually update each VF on compute-node to
use trusted mode

A long term view would be to use the network capabilities and add new
standardized os-traits for trusted mode as well as using the placement
for the scheduling phase, they are some work in-progress [6]_ [7]_.

Data model impact
-----------------

A new attribute 'vf_trusted' will be add to object
`NetworkInterfaceMetadata`. This attribute will be set only if the
interface is `vnic type SRIOV VF`_ and will indicate whether the VF is using
trusted mode.

  ``vf_trusted: fields.BooleanField(default=False)``

.. _vnic type SRIOV VF: https://github.com/openstack/nova/blob/315a4d63c/nova/network/model.py#L100

REST API impact
---------------

In case where the vif vnic type is SRIOV VF the metadata service will
return for the network interfaces a new json that will include a
'vf_trusted' attribute.

.. code-block:: json

  {
     "devices": [{
       "type": "nic",
       "bus": "pci",
       "address": "0000:00:02.0",
       "mac": "01:22:22:42:22:21",
       "tags": ["nfvfunc1"],
       "vlans": [300, 1000],
       "vf_trusted": true
       }]
  }

The `OpenStack metadata API version`_ will be incremented.

This metadata is being provided via a config drive and a metadata
service. Guest OS will be able to consume this information about the
devices. However, how the guest OS will do it is outside the scope of
this spec.

.. _OpenStack metadata API version: https://github.com/openstack/nova/blob/315a4d63c/nova/api/metadata/base.py#L74

Security impact
---------------

Some security issues are associated with the trusted VFs feature. As
noted, trusted VFs can be set into VF promiscuous mode which will
enable it to receive unmatched and multicast traffic sent to the
physical function [2]_ [3]_ It will be up to the deployer to decide
whether the security issue is manageable.

Notifications impact
--------------------

N/A

Other end user impact
---------------------

Users which request their NICs as 'trusted' during boot time will have
the ability to change the MAC addresses of the VFs within the
guest VM.

Performance Impact
------------------

N/A

Other deployer impact
---------------------

N/A

Developer impact
----------------

N/A

Upgrade impact
--------------

N/A

Implementation
==============

Assignee(s)
-----------

Primary assignee:
  Sahid Orentino Ferdjaoui <sahid-ferdjaoui>

Other contributors:
  Vladik Romanovsky <vladik-romanovsky>

Work Items
----------

- Adding command to configure trusted mode for VFs
- Updating PCI Request Spec to handle trusted tags
- Configuring trust mode for VFs on libvirt driver.
- Update metadata service to include 'vf_trusted' attribute

Dependencies
============

Even if not directly related the spec "User-controlled SR-IOV ports
allocation" [4]_ would provide required granularity in an use-case
like "fail-over bonding" to connect NICs on different physical switch.

Testing
=======

New unit tests will be written to cover the changes.

Documentation Impact
====================

A release note to inform users and operators how to configure that
feature as-well as a new documentation in the compute admin guide [8]_
that to explain how to create ports and link them using flavor
extra-spec and host-aggregates. Also the limitation and security
issues should be documented - It's not possible today to live-migrate
instances with SRIOV - Enable trusted mode for VFs have security
impacts.

References
==========

.. [1] https://communities.intel.com/thread/54061
.. [2] https://community.mellanox.com/docs/DOC-2473
.. [3] http://events.linuxfoundation.org/sites/events/files/slides/20160715_LinuxCon_sriov_final.pdf
.. [4] https://review.openstack.org/#/c/182242/
.. [5] https://marc.info/?l=linux-netdev&m=144074520803184&w=2
.. [6] https://review.openstack.org/#/c/550873/
.. [7] https://review.openstack.org/#/c/504895/7/specs/queens/approved/enable-sriov-nic-features.rst
.. [8] https://docs.openstack.org/nova/latest/admin/

History
=======

.. list-table:: Revisions
   :header-rows: 1

   * - Release Name
     - Description
   * - Pike
     - Introduced
   * - Queens
     - Re-introduced
   * - Rocky
     - Re-introduced
