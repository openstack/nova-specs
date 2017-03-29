..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

=====================================================
Veritas: libvirt volume driver for Veritas HyperScale
=====================================================

https://blueprints.launchpad.net/nova/+spec/veritas-hyperscale-libvirt-volume-driver

This implementation will provide a libvirt volume driver extension for Veritas
HyperScale which is a software-only storage provider which leverages commodity
direct-attached storage in a shared-nothing environment to give high
performance storage for OpenStack virtual machines.
This implementation will allow OpenStack virtual machines to use Veritas
HyperScale storage for boot/data volumes and allow for storage live migration
and other storage functions by simulating shared storage using shared-nothing
direct attached storage.

Problem description
===================

Veritas HyperScale is a storage provider for OpenStack based virtual machines.
It is a software-only solution that extends OpenStack functionality to provide
resilient, high performance storage to OpenStack virtual machines.

HyperScale will provide block storage to OpenStack VM to leverage commodity
storage and get DAS performance combined with resiliency, quality of service
and off-hosting services.

In order to support mounting such block volumes to Nova instances, a libvirt
volume driver extension that supports HyperScale block storage is required.
This blueprint proposes to add such a driver to Nova.

Use Cases
---------
* A user should be able to deploy a Nova virtual machine using HyperScale as
  the storage back-end by selecting a volume of type "hyperscale".
* A user should be able to attach and detach "hyperscale" type volumes to
  Nova virtual machines.
* A user should be able to perform operations such as live migration,
  evacuation etc. on virtual machines which are backed by "hyperscale" type
  volumes.

Proposed change
===============

A libvirt volume driver for Veritas HyperScale called vrtshyperscale.py will be
added to the nova/virt/libvirt/volume directory. This module will call a new
os-brick connector to manage connecting HyperScale volumes to, and
disconnecting them from, Nova VMs.

An entry will be added to the list of libvirt volume drivers in
nova/virt/libvirt/driver.py. This will direct volumes of 'volume_driver'
type 'veritas_hyperscale' to the correct driver.

The new os-brick connector will be added to os_brick/initiator/connectors.
It will call into a HyperScale CLI to provision and manage HyperScale volumes.

This change is accompanied by a cinder driver for Veritas HyperScale which is
tracked in the following blueprint:
https://blueprints.launchpad.net/cinder/+spec/veritas-hyperscale-cinder-driver

This software can be downloaded from the following location:
https://www.veritas.com/product/software-defined-storage/hyperscale-for-openstack.html

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

The os-brick connector makes calls to the HyperScale CLI as root.
It does so via os-brick's BaseLinuxConnector's _execute() method
which uses oslo.privsep for security.

Notifications impact
--------------------

None

Other end user impact
---------------------

End users will be able to create block volumes from Veritas HyperScale
and use them in OpenStack.

Performance Impact
------------------

None

Other deployer impact
---------------------

Veritas HyperScale software must be installed on OpenStack compute nodes.
This provides the following components which are required to use this driver:

* The HyperScale compute service
* The HyperScale CLI

Developer impact
----------------

None

Implementation
==============

Assignee(s)
-----------

Primary assignee:
  ketonne

Other contributors:
  None

Work Items
----------

* A volume driver extension for HyperScale storage
* An entry in the driver.py file for the new HyperScale volume type

Dependencies
============

Cinder blueprint for Veritas HyperScale driver
https://blueprints.launchpad.net/cinder/+spec/veritas-hyperscale-cinder-driver

Testing
=======

If required, a 3rd party CI testing system will be used and its results
submitted. The Cinder driver implementation is already being tested using
such a system.

Documentation Impact
====================

This needs to be documented as a new volume type in release notes.

References
==========

Product Link:
https://www.veritas.com/product/software-defined-storage/hyperscale-for-openstack.html
