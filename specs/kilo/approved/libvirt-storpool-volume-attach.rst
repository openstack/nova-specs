..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

==========================================
StorPool Volume Attachment
==========================================

https://blueprints.launchpad.net/nova/+spec/libvirt-storpool-volume-attach

There are various Nova volume drivers providing access to Cinder volumes using
specific types of storage, such as LVM, RBD, etc.  The purpose of this
blueprint is to add a driver supporting the volumes defined in a StorPool
cluster.

Problem description
===================

StorPool is distributed data storage software running on standard x86 servers.
StorPool aggregates the performance and capacity of all drives into a shared
pool of storage distributed among the servers.  Within this storage pool the
user creates thin-provisioned volumes that are exposed to the clients as block
devices.  StorPool consists of two parts wrapped in one package - a server and
a client.  The StorPool server allows a hypervisor to act as a storage node,
while the StorPool client allows a hypervisor node to access the storage pool
and act as a compute node.  In OpenStack terms the StorPool solution allows
each hypervisor node to be both a storage and a compute node simultaneously.

Use Cases
---------

As a Deployer, I want to be able to attach StorPool volumes managed by Cinder
to my instances for persistent storage, taking advantage of StorPool's
performance and scalability during the instance operation, instant attachment
of the volume to the hypervisor at instance startup, and seamless migration of
the instance to a different hypervisor.

Project Priority
----------------

None.

Proposed change
===============

The proposed driver will make use of the StorPool API (based on JSON over HTTP)
to attach and detach volumes defined in the StorPool cluster and already known
to Cinder.

Alternatives
------------

None.

Data model impact
-----------------

None.

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

The requests to attach or detach a volume will be passed on to the StorPool
JSON-over-HTTP API.

Other deployer impact
---------------------

None.

Developer impact
----------------

None.


Implementation
==============

Assignee(s)
-----------

Primary assignee:
  Peter Penchev <openstack-dev@storpool.com>

Other contributors:
  None

Work Items
----------

* Write the nova.virt.libvirt.storpool driver to attach and detach volumes.

* Write tests for the StorPool driver.

* Provide a CI setup for the StorPool driver.

Dependencies
============

The StorPool driver for Cinder for handling StorPool volumes:
https://blueprints.launchpad.net/cinder/+spec/storpool-block-driver

Testing
=======

Since the test setup requires an operational StorPool cluster, the unit tests
will mostly use mocking to simulate the operations.  A separate continuous
integration environment will be set up by StorPool and access to it will be
provided for running automated CI tests.

Documentation Impact
====================

Using the StorPool driver will be documented.

References
==========

The StorPool distributed storage software: http://storpool.com/
