..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

==========================================
Enhanced KVM Storage QoS
==========================================

https://blueprints.launchpad.net/nova/+spec/enhanced-kvm-storage-qos

QEMU 1.7 [1]_ and Libvirt 1.2.11 [2]_ [3]_ provides options to specify
maximum burst IOPS and maximum burst bandwidth per disk.
Additionally disk IO size can be specified as part of this version of QEMU.

This blueprint proposes to add support for these additonal settings to
QoS specs for connected volumes.

Problem description
===================

At the moment, the Nova libvirt driver does not support setting storage IOPS
limits. For this reason, some instances might exhaust storage resources,
impacting other tenants.

Use Cases
----------

* Associate burst IOPs and bandwidth front-end QoS specs for volumes
  exported through Cinder, which will be handled on the hypervisor side.
  This is in addition to the existing IOPs and bandwidth caps.

* Set block IO size for IOPs to volumes exported through Cinder.

* Set IOPs and bandwidth burst limits and block IO sizes for instance
  attached disks by using Cinder extra specs

Proposed change
===============

Cinder attached volumes can have additional QoS specs assigned.
Front-end QoS specs should be applied by Nova when the volume is attached.
These are applied per volume.

This blueprint proposes additional per volume QoS specs that will be
specified using Cinder volume extra specs. The libvirt driver will apply
those IOPS and bandwidth caps to the instance disks on a per volume basis.

Additionally, this blueprint proposes adding the block IO size control using
cinder volume extra specs to cinder attached volumes on a per volume basis.

Front-end volume specs will be supported only in case of volumes exported
through Cinder. No QoS specs are provided for local drives provided directly by
Nova.

Use case examples:

* Admin sets front-end QoS specs on a specific volume type
    cinder qos-create my-qos consumer=front-end \
                             total_bytes_sec_max=300000000 \

    cinder qos-associate my-qos <volume_type_id>

    cinder create <size> --volume-type <volume_type_id>

    # Those QoS specs are applied when the volume is
    # attached to a KVM instance
    nova volume-attach <instance_id> <volume_id>

Available additional QoS specs, where each will add an extra
line into the libvirt XML definition, specifically in the <iotune>
section for each device, are:

* read_bytes_sec_max
    add <read_bytes_sec_max>value</read_bytes_sec_max>

* write_bytes_sec_max
    add <write_bytes_sec_max>value</write_bytes_sec_max>

* total_bytes_sec_max - includes read/writes
    add <total_bytes_sec_max>value</total_bytes_sec_max>

* read_iops_sec_max
    add <read_iops_sec_max>value</read_iops_sec_max>

* write_iops_sec_max
    add <write_iops_sec_max>value</write_iops_sec_max>

* total_iops_sec_max - includes read/writes
    add <total_iops_sec_max>value</total_iops_sec_max>

* size_iops_sec
    add <size_iops_sec>value</size_iops_sec>



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

As Nova supports N-1 version computes, if these new qoS specs are applied to a
compute node running Queens, these new specs will be ignored. No error message
will be provided from the Queens node.

Existing Cinder QoS specs are documented in the Cinder Administration
documentation set. [8]_

Performance Impact
------------------

Allowing burst IOPs and bandwidth for certain volumes will allow some
applications to better perform when required.

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
  simon-dodsley

Work Items
----------

* Add burst and IO size QoS specs support in the libvirt volume driver by
  extending the `nova/virt/libvirt/volumes/` block volume drivers to pass
  the new properties of a volume to `LibvirtConfigGuestDisk` via the
  `qos_specs' in the `connection_info` dict.
* Extend the `LibvirtConfigGuestDisk` class to add the disk burst limits
  of a disk device [2]_


Dependencies
============

* QEMU 1.7 [1]_
* Libvirt 1.2.11 [2]_ [3]_

QEMU included in Ubuntu 16.04 [4]_ [5]_ and libvirt at a higher version
in Ubuntu 16.04 [4]_ [5]_. Also already included in Fedora 24 [6]_ [7]_

Testing
=======

* Unit tests
* Existing tests will ensure that the quest XML is formatted correctly
  assuming the required versions of libvirt and QEMU are present.

Documentation Impact
====================

The additional QoS features are described in the libvirt driver
documentation [1]_.

Will update the Cinder Administrators Guide to add these new front-end
QoS storage parameters.

References
==========

.. [1] https://libvirt.org/formatdomain.html
.. [2] https://libvirt.org/news-2014.html
.. [3] https://www.redhat.com/archives/libvir-list/2014-August/msg01354.html
.. [4] https://launchpad.net/ubuntu/+source/libvirt
.. [5] https://launchpad.net/ubuntu/+source/qemu
.. [6] https://apps.fedoraproject.org/packages/qemu
.. [7] https://apps.fedoraproject.org/packages/libvirt
.. [8] https://docs.openstack.org/cinder/latest/admin/blockstorage-capacity-based-qos.html

History
=======

.. list-table:: Revisions
   :header-rows: 1

   * - Release Name
     - Description
   * - Rocky
     - Introduced
