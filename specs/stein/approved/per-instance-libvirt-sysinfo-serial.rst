..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

==========================
Per-instance serial number
==========================

Add support for providing unique per-instance serial numbers to servers.


Problem description
===================

A libvirt guest's serial number in the machine BIOS comes from the
``[libvirt]/sysinfo_serial`` configuration option [1]_, which defaults to
reading it from the compute host's ``/etc/machine-id`` file or if that does
not exist, reading it from the libvirt host capabilities. Either way, all
guests on the same host have the same serial number in the guest BIOS.

This can be problematic for guests running licensed software that charges per
installation based on the serial number because if the guest is migrated, it
will incur new charges even though it is only running a single instance of the
software.

If the guest has a specific serial unique to itself, then the license
essentially travels with the guest.

Use Cases
---------

As a user (or cloud provider), I do not want workloads to incur license
charges simply because of those workloads being migrated during normal
operation of the cloud.

Proposed change
===============

To allow users to control this behavior (if the cloud provides it), a new
flavor extra spec ``hw:unique_serial`` and corresponding image property
``hw_unique_serial`` will be introduced which when either is set to ``True``
will result in the guest serial number being set to the instance UUID.

For operators that just want per-instance serial numbers either globally
or for a set of host aggregates, a new "unique" choice will be added to the
existing ``[libvirt]/sysinfo_serial`` configuration which if set will result
in the guest serial number being set to the instance UUID. Note that the
default value for the option will not change as part of this blueprint.

The flavor/image value, if set, supersedes the host configuration.

Alternatives
------------

We could allow users to pass through a serial number UUID when creating
a server and then pass that down through to the hypervisor, but that seems
somewhat excessive for this small change. It is also not clear that all
hypervisor backends support specifying the serial number in the guest and we
want to avoid adding API features that not all compute drivers can support.
Allowing the user to specify a serial number could also potentially be abused
for pirating software unless a unique constraint was put in place, but even
then it would have to span an entire deployment (per-cell DB restrictions would
not be good enough).

Data model impact
-----------------

None besides a new ``FlexibleBooleanField`` field being added to the
``ImageMetaProps`` object.

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

None. Users can leverage the functionality by creating new servers with an
enabled flavor/image, or rebuild/resize existing servers with an enabled
flavor/image.

Performance Impact
------------------

None

Other deployer impact
---------------------

Operators that wish to expose this functionality can do so by adding the
extra spec to their flavors and/or images or setting
``[libvirt]/sysinfo_serial=unique`` in nova configuration. If they want to
restrict the functionality to a set of compute hosts, that can also be done by
restricting enabled flavors/images to host aggregates.

Developer impact
----------------

None, except maintainers of other compute drivers besides the libvirt driver
may wish to support the feature eventually.

Upgrade impact
--------------

There is not an explicit upgrade impact except that obviously older compute
code would not know about the new flavor extra spec or image property and thus
if a user was requesting a server with the property, but the serial in the
guest did not match the instance UUID, they could be confused about why it
does not work. Again, operators can control this by deciding when to enable
the feature or by restricting it to certain host aggregates.


Implementation
==============

Assignee(s)
-----------

Primary assignee:
  Zhenyu Zheng <zhengzhenyu@huawei.com> (Kevin_Zheng)

Other contributors:
  Matt Riedemann <mriedem.os@gmail.com> (mriedem)

Work Items
----------

* Add the ``ImageMetaProps.hw_unique_serial`` field.
* Add a new choice, "unique", to the ``[libvirt]/sysinfo_serial`` configuration
  option.
* Check for the flavor extra spec and image property in the libvirt driver
  where the serial number config is set.
* Docs and tests.


Dependencies
============

None


Testing
=======

Unit tests should be sufficient for this relatively small feature.


Documentation Impact
====================

* The flavor extra spec will be documented: https://docs.openstack.org/nova/latest/user/flavors.html
* The image property will be documented: https://docs.openstack.org/glance/latest/admin/useful-image-properties.html
* The new configuration option choice will be documented [1]_

References
==========

.. [1] https://docs.openstack.org/nova/latest/configuration/config.html#libvirt.sysinfo_serial

* Libvirt documentation: https://libvirt.org/formatdomain.html#elementsSysinfo
* Nova meeting discussion: http://eavesdrop.openstack.org/meetings/nova/2018/nova.2018-10-18-14.00.log.html#l-199


History
=======

.. list-table:: Revisions
   :header-rows: 1

   * - Release Name
     - Description
   * - Stein
     - Introduced
