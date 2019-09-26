..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

=============================================
Configure maximum number of volumes to attach
=============================================

https://blueprints.launchpad.net/nova/+spec/conf-max-attach-volumes

Currently, there is a limitation in the libvirt driver restricting the maximum
number of volumes to attach to a single instance to 26. Depending on virt
driver and operator environment, operators would like to be able to attach
more than 26 volumes to a single instance. We propose adding a configuration
option that operators can use to select the maximum number of volumes allowed
to attach to a single instance.


Problem description
===================

We've had customers ask for the ability to attach more than 26 volumes to a
single instance and we've seen launchpad bugs opened from users trying to
attach more than 26 volumes (see `References`_). Because the supportability of
any number of volumes depends heavily on which virt driver is being used and
the operator's particular environment, we propose to make the maximum
configurable by operators. Choosing an appropriate maximum number will require
tuning with the specific virt driver and deployed environment, so we expect
operators to set the maximum, test, tune, and adjust the configuration option
until the maximum is working well in their environment.

Use Cases
---------

* Operators wish to be able to attach a maximum number of volumes to a single
  instance, with the ability to choose a maximum well-tuned for their
  environments.

Proposed change
===============

When a user attempts to attach more than 26 disk devices with the libvirt
driver, the attach fails in the ``reserve_block_device_name`` method in
nova-compute, which is eventually called by the ``attach_volume`` method in
nova-api. The ``reserve_block_device_name`` method calls
``self.driver.get_device_name_for_instance`` to get the next available device
name for attaching the volume. If the driver has implemented the method, this
is where an attempt to go beyond the maximum allowed number of disk devices to
attach, will fail. The libvirt driver fails after 26 disk devices have been
attached. Drivers that have not implemented ``get_device_name_for_instance``
appear to have no limit on the maximum number of disk devices. The default
implementation of ``get_device_name_for_instance`` is located in the
``nova.compute.utils`` module. Only the libvirt driver has provided its own
implementation of ``get_device_name_for_instance``.

The ``reserve_block_device_name`` method is a synchronous RPC call (not cast).
This means we can have the configured allowed maximum set differently per
nova-compute and still fail fast in the API if the maximum has been exceeded
during an attach volume request.

For a server create, rebuild, evacuate, unshelve, or live migrate request, if
the maximum has been exceeded, the server will go into the ``ERROR`` state and
the server fault message will indicate the failure reason.

Note that the limit in the libvirt driver is actually on the total number of
disk devices allowed to attach to a single instance including the root disk
and any other disks. It does not differentiate between volumes and other disks.

We propose to add a new configuration option
``[compute]max_disk_devices_to_attach`` IntOpt to use to configure the maximum
allowed disk devices to attach to a single instance per nova-compute. This way,
operators can set it appropriately depending on what virt driver they are
running and what their deployed environment is like. The default will be
unlimited (-1) to keep the current behavior for all drivers except the libvirt
driver.

The configuration option will be enforced in the
``get_device_name_for_instance`` methods, using the count of the number of
already attached disk devices. Upon failure, an exception will be propagated to
nova-api via the synchronous RPC call to nova-compute, and the user will
receive a 403 error (as opposed to the current 500 error).

Alternatives
------------

Other ways we could solve this include: choosing a new hard-coded maximum only
for the libvirt driver or creating a new quota limit for "maximum disk devices
allowed to attach" (see the ML thread in `References`_).

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

Deployers will be able to set the ``[compute]max_disk_devices_to_attach``
configuration option to control how many disk devices are allowed to be
attached to a single instance per nova-compute in their deployment.

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
  melwitt

Other contributors:
  yukari-papa

Work Items
----------

* Add a new configuration option ``[compute]max_disk_devices_to_attach``,
  IntOpt
* Modify (or remove) the libvirt driver's implementation of the
  ``get_device_name_for_instance`` method to accomodate more than 26 disk
  devices
* Add enforcement of ``[compute]max_disk_devices_to_attach`` to the
  ``get_device_name_for_instance`` methods
* Add handling of the raised exception in the API to translate to a 403 to the
  user, if the maximum number of allowed disk devices is exceeded


Dependencies
============

None

Testing
=======

The new functionality will be tested by new unit and functional tests.


Documentation Impact
====================

The documentation for the new configuration option will be automatically
included in generated documentation of the configuration reference.

References
==========

* https://bugs.launchpad.net/nova/+bug/1770527

* https://bugs.launchpad.net/nova/+bug/1773941

* http://lists.openstack.org/pipermail/openstack-dev/2018-June/131289.html


History
=======

Optional section intended to be used each time the spec is updated to describe
new design, API or any database schema updated. Useful to let reader understand
what's happened along the time.

.. list-table:: Revisions
   :header-rows: 1

   * - Release Name
     - Description
   * - Stein
     - Introduced
