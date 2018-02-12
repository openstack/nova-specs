..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

====================
Hyper-V vTPM Devices
====================

https://blueprints.launchpad.net/nova/+spec/hyper-v-vtpm-devices

Windows / Hyper-V Server Technical Preview introduced the ability to attach
vTPM devices to the Hyper-V VMs, offering the users the posibility to use it
to enhance their security and system integrity.

Problem description
===================

Currently, there Hyper-V Driver doesn't support adding vTPM devices to
instances. This blueprint is addresing this issue.

Use Cases
----------

Trusted Platform Module (TPM) technology is designed to provide hardware-based,
security-related functions and it includes multiple security mechanisms to make
it tamper resistant. Some of the key advantages of using TPM technology are:

* Generate, store, and limit the use of cryptographic keys.
* Use TPM technology for platform device authentication by using the TPM’s
  unique RSA key, which is burned into itself.
* Help ensure platform integrity by taking and storing security measurements.
* TPM-based Virtual Smart Card.

The shielded VMs make use of the vTPM devices. Shielded VMs should be used in
cases where the security of the spawned instance is essential. They are
encrypted (BitLocker or other means), ensuring that the only the designated
owners can access the virtual machine. [2]

A few features of the Shielded VMs are:

* Cannot inspect the disks.
* Cannot inspect the memory.
* Canoot inspect the processes.
* Cannot attach debuggers to the system.
* Cannot change the configuration.

In short, even if the administrator of the hypervisor host is compromised, all
the existent virtual machine data is safe.

For more information and use cases for vTPM, check the References section [1].

Project Priority
-----------------

None

Proposed change
===============

This feature is not available in earlier versions than Windows / Hyper-V Server
Technical Preview. vTPM devices cannot be created on an earlier version.

If the given instance requires a vTPM device but it does not contain the
``hw_machine_type=hyperv-gen2`` image property, the instance creation will
fail, as vTPM can be only added for Generation 2 VMs. Generation 2 VMs were
introduced in Windows / Hyper-V Server 2012 R2 and support for them was
introduced in the Kilo release (see Dependencies section).

As vTPM is not supported by all guests, enabling it for instances that do not
support it is pointless. Thus, creating instances with vTPM devices is done by
setting the ``os_vtpm`` image property or the ``os:vtpm`` flavor extra spec to
``required``. Other possible values are: ``disabled`` and ``optional``. The
flavor extra spec value overrides the image property value.

The image property ``os_vtpm_keys`` contains a comma separated UUID list,
which are references to the Barbican stored secrets. Maximum 6 references can
be added, due to nova InstanceSystemMetadata model's limitation to 255 bytes.
Those secrets contains data that must be set into the vTPM. This is mandatory
for Shielded VMs. Providing this image property without requesting a vTPM
device will result in an exception. If one of the Barbican secrets cannot be
fetched, an exception will be raised.

Scheduling is assured by the ImagePropertiesFilter [5], which checks if the
image property ``hypervisor_version_requires`` is satisfied by the given
hosts. This is the initial approach to solving the scheduling problem. Ideally,
this problem will be solved by exposing this feature as a host capability and
having the ``os_vtpm_device`` image property or ``os:vtpm_device`` flavor extra
spec match the host capability.

The following operations are to be implemented:

* Add Barbican authentication config options.
* Fetch the vTPM keys from Barbican using python-barbicanclient and the image
  property ``os_vtpm_keys``, which is a comma separated UUID list, which are
  references to Barbican secrets.
* Create Host Guardian Service KeyProtector with the previously fetched
  encyption key and register it in the Host Guardian, if the image property
  ``os_vtpm_keys`` is provided.
* Add vTMP device to the Generation 2 VM, enable it and add the previously
  created KeyProtector to it.

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

Users will be able to use vTPM, which is useful to control access control and
authentication. This can lead to enhanced VM security.

The VM encryption keys must be protected. They will have to be stored in
Barbican as secrets, and make sure that the service is properly set up. For
more information, see the References section [4].

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

In order for this feature to be usable, the Host Guardian Service will have
to be enabled and the hosts must be Guarded (the Guardian Service key must be
imported in the local host). [2]

Barbican is needed, in order to properly use this feature [4]. It will be used
to store the VM encryption keys as secrets. In order to be able to use it,
config options regarding Barbican authentication will have to be set in the
compute node's nova.conf file, under the [barbican] section. A sample will be
provided. (WIP)

VMs with vTPMs cannot be migrated from an Active Directory to another or to
an Unguarded Host. In order to ensure that the scheduler will not pick a host
outside the current Active Directory, all the Guarded Hosts in the Active
Directory should be added to the same aggregate.

This feature is only available in Windows / Hyper-V Server Technical Preview
and in order to ensure proper scheduling, the ``hypervisor_version_requires``
image property should be set to ``>=10.0``.

The images must be prepared for Shielded VMs. For example, the VM on which the
image is prepared, it must be Generation 2 VM, have a vTPM device with a
Host Guardian Service KeyProtector set. The attached drives must be encrypted
using BitLocker or any encryption program [2]. Then, the key data must be
stored into Barbican as a secret. [4]

In order to create instances with vTPM device attached, the user will have to
request it in the following ways:

* Image property ``os_vtpm`` set to ``required``.
* Image property ``os_vtpm`` set to ``optional`` and flavor extra spec
  ``os:vtpm`` set to ``required``.

Contradicting image property and flavor extra spec will result in failing to
create instance.

Any key data should be stored into Barbican as secrets and create the image
property ``os_vtpm_keys`` containing the comma separated references to the
secrets (maximum 6 references, due to a length limitation - maximum 255
characters), otherwise the instances will be spawned with no data stored in the
vTPMs. Example value: UUID1,UUID2,UUID3

If the ``os_vtpm_keys`` image property is set, the image property
``os_vtpm`` or the flavor extra spec ``os:vtpm`` must be set to ``required``,
otherwise the instance will not spawn.

Image creation example:

  glance image-create --property hypervisor_type=hyperv \
        --property hw_machine_type=hyperv-gen2 \
        --property hypervisor_version_requires='>=10.0' \
        --property os_vtpm=required \
        --property os_vtpm_keys=$key_refs --name im-secure \
        --disk-format vhd --container-format bare --file path/to/image.vhdx

or

  glance image-update --property hw_machine_type=hyperv-gen2 win-secure

  glance image-update --property hypervisor_version_requires='>=10.0' im-secure

  glance image-update --property os_vtpm=required im-secure

  glance image-update --property os_vtpm_keys=$key_refs im-secure

The ``os_vtpm`` image property acceptable values are:
``disabled, optional, required``. If the property is not defined, ``disabled``
will be used as default value. The ``optional`` value means that the image
guest OS can use the vTPM, but it will require the flavor extra spec in order
for the instance to be created with a vTPM device.

Flavor extra spec example:

  nova flavor-key m1.your.flavor set "os:vtpm=required"

Developer impact
----------------

None

Implementation
==============

Assignee(s)
-----------

Primary assignee:
  Claudiu Belu <cbelu@cloudbasesolutions.com>

Work Items
----------

As described in the Proposed Change section.

Dependencies
============

Hyper-V VM Generation 2 nova spec. Feature merged in Kilo.
    https://review.openstack.org/#/c/103945/5

Testing
=======

* Unit tests.
* Feature will be tested by Hyper-V CI.

Documentation Impact
====================

New image property and flavor extra spec will have to be documented.
New Barbican credentials config options will have to be documented.

References
==========

[1] Trusted Platform Module Technology Overview
  https://technet.microsoft.com/en-us/library/jj131725.aspx

[2] Shielded VMs and Guarded Fabric Validation Guide:
  https://gallery.technet.microsoft.com/Shielded-VMs-and-Guarded-44176db3

[3] Harden the Fabric: Protecting Tenant Secrets in Hyper-V
  https://channel9.msdn.com/Events/Ignite/2015/BRK3457

[4] Barbican storing secrets:
  https://github.com/cloudkeep/barbican/wiki/Barbican-Quick-Start-Guide

History
=======
