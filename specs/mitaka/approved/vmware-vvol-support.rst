..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

==========================================
Support for Virtual Volumes
==========================================

https://blueprints.launchpad.net/nova/+spec/vmware-vvol-support

Virtual Volumes is an integration and management framework delivering a new
operational model for external storage (SAN/NAS). It is comprised of a control
plane using SPBM, and a data plane using VASA APIs for external storage and
vSphere APIs for IO Filtering for in-hypervisor software data services.

A storage container is a logical abstraction on to which Virtual Volumes are
mapped and stored. Storage containers are setup at the array level and
associated with array capabilities. vSphere will map storage containers to
VVol Datastores and provide applicable datastore level functionality.

Currently the VMware driver in Nova supports VMFS, NFS and vSAN datastores.
This is a proposal for adding support for VVol Datastores.

Problem description
===================

The VMware driver cannot provision instances on VVol Datastores.

Use Cases
---------

As an End User I want to provision instances on VVol Datastores when using
the VMware driver in Nova.

Proposed change
===============

Adding support for VVol Datastores would be pretty straightforward -- we just
need to whitelist datastores with type "VVOL" when choosing a datastore for
the instance. There is also an additional restriction that the virtual disk
size of the image that is provisioned should be an even multiple of 1MB.

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

None

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
  rgerganov

Work Items
----------

It will be implemented in a single patch that whitelists the VVol type and
does the required checks for the virtual disk size.

Dependencies
============

Virtual Volumes are introduced in vSphere 6.0. However, we don't need any
checks for the VC version in the code but simply whitelist the VVol type.

Testing
=======

There will be a separate CI job that will run tempest with VVol datastores

Documentation Impact
====================

None

References
==========

[1] https://www.vmware.com/files/pdf/products/virtualvolumes/VMware_Virtual_Volumes_FAQ.pdf

[2] https://www.vmware.com/files/pdf/products/virtualvolumes/VMware-Whats-New-vSphere-Virtual-Volumes.pdf

[3] https://pubs.vmware.com/vsphere-60/topic/com.vmware.vsphere.storage.doc/GUID-516662BE-1F19-4C03-A633-B79AE4C73B18.html

History
=======

