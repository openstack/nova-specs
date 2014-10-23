..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

================================================================
Support KVM/libvirt on System z (S/390) as a hypervisor platform
================================================================

https://blueprints.launchpad.net/nova/+spec/libvirt-kvm-systemz

Add support for KVM/libvirt in Linux on System z as a Nova hypervisor
platform.  The existing Nova driver for KVM/libvirt will be used. There are
some platform-specific changes needed in the Nova driver to get the platform
going.

Additional OpenStack functionality beyond initial Nova support is not part of
this blueprint; we will have specific additional blueprints for that, as
needed.

A 3rd party Continuous Integration environment for OpenStack for KVM/libvirt
on System z will be established and maintained.


Problem description
===================

The existing Nova driver for KVM/libvirt does not work unchanged for KVM on
System z.

The issues currently known, are:

1. The System z machine type (``'s390-ccw-virtio'``) needs to be returned by
   ``LibvirtDriver._get_machine_type()``, if the host architecture is System z.
   This then causes the ``os/type/@machine`` attribute in the libvirt
   domain.xml to be set up accordingly.

2. The CPU capabilities returned by libvirt on System z do not include the
   ``model`` element. This is intended to be added to libvirt, but until then
   we need a temporary circumvention in the Nova driver (adding the model
   information from /proc/cpuinfo if not present and if on S390x).

3. For the interactive console and the log of OpenStack instances, console
   devices need to be generated (instead of serial devices), if the host
   architecture is System z (see `[2]`_).  These console devices need to have a
   target type ``"sclp"`` for the interactive console of OpenStack, and
   ``"sclplm"`` for the log of OpenStack.

   Background: Linux on System z writes its messages during its early boot
   phases to an interface called "SCLP".  SCLP is available in QEMU as a
   console device.  As a result, it is also a console device in libvirt, with
   type="pty" and target type="sclp" for the interactive console of OpenStack,
   and with type="file" and target type="sclplm" ("lm" for "line mode") for the
   log of OpenStack.  If we use the default target type ("virtio"), we will not
   capture the messages written by Linux in its early boot phases, and we do
   want to provide them.

   Changing the default target type for console devices in libvirt to "sclp" or
   "sclplm" (e.g. dependent on the ``console/@type`` attribute) would be a
   backwards incompatible change of libvirt.

   If commonality in the Nova driver across the libvirt platforms is important:
   A console device could also be used for other platforms including x86, and
   is already used in one of the code paths in the current Nova driver.  Serial
   devices in libvirt are meant to represent serial ports (aka RS-232), so they
   are not an ideal choice anyway, for interactive console and log.

4. The FCP support in the libvirt volume driver needs to be adjusted to
   the System z specific format of the device file paths.

In the hypervisor support matrix
(https://wiki.openstack.org/wiki/HypervisorSupportMatrix),
the (new) column for KVM/libvirt on System z is intended to look like the
column for KVM/libvirt on x86, except that the following functions will not be
supported (in addition to those marked as not supported for KVM/libvirt on
x86):

* VNC Console
* SPICE Console
* Inject Networking

For block storage, Cinder will be supported.

For networking, Neutron will be supported. Nova networking should work but will
not be a focus.

As a result, all features marked as required on
https://wiki.openstack.org/wiki/HypervisorSupportMatrix/Requirements
will be supported for KVM/libvirt on System z.

Use Cases
---------

Use OpenStack with KVM on System z

Project Priority
----------------

None


Proposed change
===============

Change code in the libvirt Nova driver to address these issues, dependent on
the host capabilities indicating a CPU architecture of ``arch.S390X``.
For details, see section `Work Items`_.

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

None (no need for platform-specific parameters in nova.conf as part of this
blueprint)

Developer impact
----------------

None (changes should not affect other libvirt platforms)

Implementation
==============

Assignee(s)
-----------

Primary assignee:
  mzoeller

Other contributors:
  maiera

Work Items
----------

In ``nova/virt/libvirt/driver.py``:

* For issue 1:
  In ``LibvirtDriver._get_machine_type()``, return the System z machine type
  (``'s390-ccw-virtio'``), if the host architecture is System z.
* For issue 2:
  In `` LibvirtDriver._get_host_capabilities()``,  add the ``model`` variable
  to the capabilities, if not present and if the host architecture is System z;
  the model is based on the machine type from /proc/cpuinfo.
* For issue 3:
  In ``LibvirtDriver._get_guest_config()``, create console devices instead of
  serial devices for the interactive console and for the log, with target type
  "sclplm" (for the log) and "sclp" (for the interactive console), if the host
  architecture is System z.

In ``nova/virt/libvirt/config.py``:

* For issue 3:
  In ``LibvirtConfigGuestChar.__init__()`` and ``format_dom()``, add support
  for specifying a target type.

In ``nova/virt/libvirt/volume.py``:

* For issue 4:
  The FCP support in the libvirt volume driver needs to be adjusted to
  the System z specific format of the device file paths.

In ``nova/virt/libvirt/utils.py``:

* For issue 4:
  Possibly, supporting utility functions for the FCP support issue are needed.

Doc changes (see section `Documentation Impact`_).


Dependencies
============

* Software versions:

  - Linux kernel: 3.10 or higher
  - libvirt: 1.0.4 or higher
  - qemu: 1.4.0 or higher

* 3rd party CI environment for KVM/libvirt on System z set up

* Future replacements for temporary circumventions:

  - libvirt patch to add model information to CPU capabilities.

Testing
=======

Unit test:

* Existing Nova unit tests should suffice for the generic bits of Nova.
* Additional Nova unit tests for any s390-specific behaviors will be written.

3rd party CI:

* A 3rd party CI environment for KVM/libvirt on Systemz will be set up and run
  by by IBM, to run full tempest tests.


Documentation Impact
====================

* No changes needed in config docs.

* Doc changes for the platform will be made as needed (details are to be
  determined).


References
==========

* _`[1]` libvirt: Domain XML format, Device Addresses,
  http://libvirt.org/formatdomain.html#elementsAddress

* _`[2]` libvirt: Domain XML format, Console,
  http://libvirt.org/formatdomain.html#elementCharConsole

* _`[3]` Linux on System z Device Driver book,
  http://public.dhe.ibm.com/software/dw/linux390/docu/l316dd25.pdf

* _`[4]` Linux on System z,
  http://www.ibm.com/developerworks/linux/linux390/
