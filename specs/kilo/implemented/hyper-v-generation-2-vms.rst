..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

==========================================
Hyper-V generation 2 VMs
==========================================

https://blueprints.launchpad.net/nova/+spec/hyper-v-generation-2-vms

Introduction of Hyper-V generation 2 VMs support in the Nova Hyper-V
compute driver.

Problem description
===================

Hyper-V Server 2012 R2 introduces a new feature for virtual machines named
"generation 2", consisting mainly in a new virtual firmware and better support
for synthetic devices.

Use Cases
----------

The main advantages are:

* secureboot support
* reduced boot time
* virtual devices completely synthetic (no emulation)
* UEFI firmware in place of BIOS
* support for live resize of boot disks (expand)

Operating systems supporting generation 2:

* Windows Server 2012 / Windows 8 and above
* Newer Linux kernels

Other operating systems not supporting generation 2, including previous
versions of Windows won't install or boot, so generation 1 needs to be retained
as the default.

The image must be in VHDX format.

Project Priority
-----------------

None

Proposed change
===============

The Hyper-V compute driver creates a generation 2 VM based on a property
defined in the instance image, defaulting to generation 1.

The compute driver will raise an exception if the provided image has the VHD
format or if the requested VM Generation is not supported by the host (e.g.:
if the image requests VM Generation 2 but the host is Windows Hyper-V / Server
2012 or older and does not support that feature).

Generation 2 VMs don't support IDE devices, which means that local boot and
ephemeral disks must be attached to a SCSI controller, while retaining IDE
support for generation 1 instances (where SCSI boot is not supported).

The Hyper-V Generation 2 VMs will have Secure Boot disabled, since it is not
supported by all Linux distributions, see [3]. A blueprint will be proposed in
order to enable Secure Boot.

Proposed image property to identify the desired generation and related values:

hw_machine_type={hyperv-gen1,hyperv-gen2}

If there are multiple versions of Hyper-V as compute nodes in an OpenStack
deployment (e.g.: Windows Hyper-V / Server 2012 and Windows Hyper-V / Server
2012 R2), then this property is necessary, in order for the scheduler to select
an incompatible compute node for a VM Generation 2 instance:

hypervisor_version_requires='>=6.3'

Hypervisor version 6.3 is equivalent to Windows Hyper-V / Server 2012 R2.

Examples:

glance image-create --property hypervisor_type=hyperv \
    --property hw_machine_type=hyperv-gen2 \
    --property hypervisor_version_requires='>=6.3' --name image-gen2 \
    --disk-format vhd --container-format bare --file path/to/image.vhdx

or

glance image-update --property hw_machine_type=hyperv-gen2 image-gen2
glance image-update --property hypervisor_version_requires='>=6.3'

Alternatives
------------

Generation 1 VMs are currently supported.

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

There are a couple of things that must be taken into account when deploying
Generation 2 VMs. For more details, see [4]. Most notable restrictions are:

* Images used for Generation 1 VMs cannot be used for Generation 2 VMs. Images
  must be created by installing the guest OS in a Generation 2 VM.

* Guest OSes must be 64-bit.

* RemoteFX is not supported for Generation 2 VMs.

* Ubuntu images need extra preparation before they can be used for Generation 2
  VMs. For more details, see [5], Note section, point 11.

Developer impact
----------------

None

Implementation
==============

Assignee(s)
-----------

Primary assignee:
  cbelu

Other contributors:
  alexpilotti

Work Items
----------

* Nova Hyper-V driver implementation
* Unit tests

Dependencies
============

None

Testing
=======

Unit tests. The Hyper-V CI will still run using Generation 1 VMs and the plan
is to have a subset of Tempest tests using a Generation 2 VM.

Documentation Impact
====================

The Nova driver documentation should include an entry about this topic
including when to use and when not to use generation 2 VMs. A note on the
relevant Glance image property should be added as well.

References
==========

[1] Initial discussion (Juno design summit):
    https://etherpad.openstack.org/p/nova-hyperv-juno

[2] Hyper-V Generation 2 VMs
    http://blogs.technet.com/b/jhoward/archive/2013/11/04/hyper-v-generation-2-virtual-machines-part-7.aspx

[3] Secure Boot on:
    * CentOS and RedHat:
        https://technet.microsoft.com/en-us/library/dn531026.aspx
    * Oracle Linux:
        https://technet.microsoft.com/en-us/library/dn609828.aspx
    * SUSE:
        https://technet.microsoft.com/en-us/library/dn531027.aspx
    * Ubuntu:
        https://technet.microsoft.com/en-us/library/dn531029.aspx

[4] Hyper-V Generation 2 VMs FAQ:
    https://technet.microsoft.com/en-us/library/dn282285

[4] Ubuntu Generation 2 VMs preparation:
    https://technet.microsoft.com/en-us/library/dn531029.aspx
