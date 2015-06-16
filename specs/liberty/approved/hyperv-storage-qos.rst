..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

==========================================
Hyper-V Storage QoS
==========================================

https://blueprints.launchpad.net/nova/+spec/hyperv-storage-qos

Hyper-V provides options to specify maximum IOPS per virtual disk image.

By leveraging this feature, this blueprint proposes to add support for setting
QoS specs targeting instance local disks as well as volumes exported through
SMB.

Problem description
===================

At the moment, the Nova Hyper-V driver does not support setting storage IOPS
limits. For this reason, some instances might exhaust storage resources,
impacting other tenants.

Use Cases
----------

* Associate front-end QoS specs for volumes exported through SMB, which will
  be handled on the hypervisor side

* Set IOPS caps for instance local disks by using flavor extra specs

Project Priority
-----------------

None

Proposed change
===============

Cinder volumes can have QoS specs assigned. Front-end QoS specs should be
applied by Nova when the volume is attached. Those are applied per volume.

In addition, this blueprint proposes per instance QoS specs that will be
specified using flavor extra specs. The Hyper-V driver will apply those IOPS
caps to all the local instance disks equally.

For example, if a specific IOPS cap is specified in the flavor extra specs,
this cap will be applied to the instance root, ephemeral and configdrive disk
equally.

Front-end volume specs will be supported only in case of volumes exported
through SMB.

Use case examples:

* Admin sets front-end QoS specs on a specific volume type
    cinder qos-create my-qos consumer=front-end \
                             total_bytes_sec=20971520 \

    cinder qos-associate my-qos <volume_type_id>

    # SMB must be used as a volume backend, iSCSI support may be
    # added in the future
    cinder create <size> --volume-type <volume_type_id>

    # Those QoS specs are applied when the volume is
    # attached to a Hyper-V instance
    nova volume-attach <hyperv_instance_id> <volume_id>

* Admin sets instance storage QoS specs on the flavor
    nova flavor-key <my_flavor> set \
                    storage_local_qos:total_bytes_sec=20971520

Available QoS specs:
    * total_bytes_sec - includes read/writes

    * total_iops_sec

Alternatives
------------

Flavor QoS specs could be applied not only for instance local disks but
attached volumes as well. In this case, if volume QoS specs are present, we may
apply the lowest IOPS cap.

Also, the cap could be divided among the disks, but this may not be desired.

Data model impact
-----------------

None

REST API impact
---------------

None

Security impact
---------------

Setting storage QoS specs will prevent instances from exhausting storage
resources, which may impact other tenants.

Notifications impact
--------------------

None

Other end user impact
---------------------

None

Performance Impact
------------------

Preventing instances from exhausting storage resources can have a significant
performance impact.

Other deployer impact
---------------------

None

Developer impact
----------------

None

Implementation
==============

Assignee(s)
-----------

Primary assignee:
  plucian

Work Items
----------

* Add front-end QoS specs support in the Hyper-V SMB volume driver

* Add flavor storage QoS specs support

Dependencies
============

None

Testing
=======

This feature will be tested by the Hyper-V CI. We'll add tempest tests
verifying that the IOPS cap is actually enforced.

Documentation Impact
====================

The QoS features should be described in the Hyper-V driver documentation.

References
==========

Hyper-V Storage QoS reference:
https://technet.microsoft.com/en-us/library/dn282281.aspx

History
=======

None
