..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

=======================
Hyper-V UEFI SecureBoot
=======================

https://blueprints.launchpad.net/nova/+spec/hyper-v-uefi-secureboot

Secure Boot is a mechanism that starts the bootloader only if the bootloader's
signature has maintained integrity, assuring that only approved components are
allowed to run. Secure Boot is dependent on UEFI.

Problem description
===================

Secure Boot is currently disabled in the Nova Hyper-V Driver, as it did not
support Linux guests [2], only Windows guests [3]. The new
Windows / Hyper-V Server Technical Preview introduces Secure Boot support for
Linux guests. [3]

Use Cases
----------

This feature will increase the security of the spawned instances, assuring
their integrity before they boot.


Proposed change
===============

In order enable Secure Boot on an instance, the field SecureBootEnabled must
be set to True, when creating the instance's Msvm_VirtualSystemSettingData
WMI object.

As Secure Boot is not supported by all guests, enabling it for instances that
do not support it will result in a hanging VM. Thus, Secure Boot feature will
be enabled by setting the ``os_secure_boot`` image property or the
``os:secure_boot`` flavor extra spec to ``required``. Other possible values
are: ``disabled`` and ``optional``. The flavor extra spec value overrides the
image property value.

The image property values are: ``disabled, optional, required``. If the
property is not defined, the default value ``disabled`` will be used.
The flavor extra spec acceptable value is: ``required``. Any other value will
be ignored.

Linux guests are supported in Windows / Hyper-V Server Technical Preview and
they also require the bootloader's digital signature. This will also be
provided as an image property ``os_secure_boot_signature`` (string).

If the given instance requires Secure Boot but it does not contain the
``hw_machine_type=hyperv-gen2`` image  property, the instance creation should
fail, as Secure Boot requires Generation 2 VMs. Generation 2 VMs were
introduced in Windows / Hyper-V Server 2012 R2 and support for them was
introduced in the Kilo release (see Dependencies section).

Scheduling is assured by the ImagePropertiesFilter [5], which checks if the
image property ``hypervisor_version_requires`` is satisfied by the given
hosts. This is the initial approach to solving the scheduling problem. Ideally,
this problem will be solved by exposing this feature as a host capability and
having the ``os_secure_boot`` and ``os_type`` image properties match the host
capability.

Alternatives
------------

None

Data model impact
-----------------

``os_secure_boot`` field must be added to the ImageMetaProps object, as there
is no field for the image property with the same name.

REST API impact
---------------

None

Security impact
---------------

This feature will assure that the spawned instances are safe.

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

The images must be prepared for Secure Boot. For example, the VM on which the
image is prepared, it must be Generation 2 VM with Secure Boot enabled.
Instances using such images will be able to spawned with Secure Boot on or off,
while instances using images that are not prepared for Secure Boot can only
spawn with Secure Boot off.

Images should be for Generation 2 VMs images. The image property
``hw_machine_type=hyperv-gen2`` is mandatory.

Linux images requiring Secure Boot must be spawned on Windows / Hyper-V Server
Technical Preview. In order for the instances to be properly scheduled, the
images must contain the property ``hypervisor_version_requires='>=10.0'``. In
this case, the image property ``os_secure_boot_signature`` containing the
bootloader's digital signature is required.

Nova scheduler should use the ImagePropertiesFilter [5], which checks that the
hosts satisfy the ``hypervisor_version_requires`` image property. In order to
use this filter, it should be added to the scheduler's nova.conf file,
``scheduler_default_filters`` field. By default, this filter is included in the
list.

In order to properly use Secure Boot, images should be created as follows:

* Windows images (Windows 8 or Windows / Hyper-V Server 2012 R2 or newer):

  glance image-create --property hypervisor_type=hyperv \
      --property hw_machine_type=hyperv-gen2 \
      --property hypervisor_version_requires='>=6.3' \
      --property os_secure_boot=required --name win-secure \
      --disk-format vhd --container-format bare --file path/to/windows.vhdx

  or

  glance image-update --property hw_machine_type=hyperv-gen2 win-secure

  glance image-update --property os_secure_boot=required win-secure

  glance image-update --property hypervisor_version_requires='>=6.3' win-secure

* Linux images:

  glance image-create --property hypervisor_type=hyperv \
      --property hw_machine_type=hyperv-gen2 \
      --property hypervisor_version_requires='>=10.0' \
      --property os_secure_boot=required \
      --property os_secure_boot_signature=$SIGNATURE --name im-secure \
      --disk-format vhd --container-format bare --file path/to/linux.vhdx

  or

  glance image-update --property hw_machine_type=hyperv-gen2 im-secure

  glance image-update --property os_secure_boot=required im-secure

  glance image-update --property os_secure_boot_signature=$SIGNATURE im-secure

  glance image-update --property hypervisor_version_requires='>=10.0' im-secure

The ``os_secure_boot`` image property acceptable values are:
``disabled, optional, required``. If the property is not defined, ``disabled``
will be used as default value. The ``optional`` value means that the image is
capable of Secure Boot, but it will require the flavor extra spec in order to
use this feature.

Secure Boot VMs can also be requested as a flavor extra spec called
``os:secure_boot``, having the value ``required``. Example:

    nova flavor-key m1.your.flavor set "os:secure_boot=required"

Developer impact
----------------

None

Implementation
==============

Assignee(s)
-----------

Primary assignee:
  Iulia Toader <itoader@cloudbasesolutions.com>

Other contributors:
  Claudiu Belu <cbelu@cloudbasesolutions.com>

Work Items
----------

As described in the Proposed Change.

Dependencies
============

Hyper-V VM Generation 2 nova spec. Feature merged in Kilo.
    https://review.openstack.org/#/c/103945/5

Testing
=======

* Unit tests.
* Will be tested by Hyper-V CI.

Documentation Impact
====================

The new image properties and will have to be documented.

References
==========

[1] Hyper-V Generation 2 VMs
    http://blogs.technet.com/b/jhoward/archive/2013/11/04/hyper-v-generation-2-virtual-machines-part-7.aspx

[2] Secure Boot not supported on:
    * CentOS and RedHat:
        https://technet.microsoft.com/en-us/library/dn531026.aspx
    * Oracle Linux:
        https://technet.microsoft.com/en-us/library/dn609828.aspx
    * SUSE:
        https://technet.microsoft.com/en-us/library/dn531027.aspx
    * Ubuntu:
        https://technet.microsoft.com/en-us/library/dn531029.aspx

[3] Secure Boot supported on:
    * Windows:
        https://technet.microsoft.com/en-us/library/dn486875.aspx
    * Ubuntu, SUSE on Hyper-V Technical Preview:
        https://technet.microsoft.com/en-us/library/dn765471.aspx#BKMK_linux

[4] Msvm_VirtualSystemSettingData:
    https://msdn.microsoft.com/en-us/library/hh850257%28v=vs.85%29.aspx

[5] Nova scheduler ImagePropertiesFilter:
    https://github.com/openstack/nova/blob/master/nova/scheduler/filters/image_props_filter.py#L75

History
=======

.. list-table:: Revisions
   :header-rows: 1

   * - Release Name
     - Description
   * - Mitaka
     - Introduced
   * - Newton
     - Re-proposed
   * - Ocata
     - Re-proposed
