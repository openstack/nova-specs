..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

==========================================
Add support for emulated virtual TPM
==========================================

Include the URL of your launchpad blueprint:

https://blueprints.launchpad.net/nova/+spec/add-emulated-virtual-tpm

There are a class of applications which expect to use a TPM device to store
secrets.  In order to run these applications in a virtual machine, it would be
useful to expose a virtual TPM device within the guest.  Accordingly, the
suggestion is to add a placement trait which could be requested in the
flavor or image which would cause such a device to be added to the VM by the
relevent virt driver.


Problem description
===================

Currently there is no way to create virtual machines within nova that provide
a virtual TPM device to the guest.

Use Cases
---------

Support the virtualizing of existing applications and operating systems which
expect to make use of physical TPM devices.  At least one hypervisor
(libvirt/qemu) currently supports the creation of an emulated TPM device which
is associated with a per-VM "swtpm" process on the host, but there is no way to
tell nova to enable it.

Proposed change
===============

In recent libvirt and qemu (and possibly other hypervisors as well) there is
support for an emulated vTPM device.  We propose to modify nova to make use
of this capability.

For the libvirt virt driver in particular, there is support for vTPM as of
libvirt 4.5. The desired libvirt XML arguments are something like this::

    ...
    <devices>
      <tpm model='tpm-tis'>
        <backend type='emulator' version='2.0'>
        </backend>
      </tpm>
    </devices>
    ...

Support for emulated TPM requires qemu 2.11 at a minimum, though qemu 2.12 is
recommended by the author.  The virt driver code should add suitable version
checks (in the case of LibvirtDriver, this would include checks for both
libvirt and qemu).  Currently emulated TPM is only supported for x86, though
this is an implementation detail rather than an architectural limitation.

Support for emulated TPM also requires the "swtpm" binary and libraries to be
available on the host.  If there is no way to check whether this is available
from the hypervisor, we may need to add a hypervisor-specific nova.conf flag
indicating that we want to enable emulated TPM support. This would presumably
default to `false` for minimal surprise on upgrades.

In order to request this functionality (and to allow scheduling to nodes that
provide this functionality) we propose to define two new traits,
`COMPUTE_SECURITY_TPM_1_2` and `COMPUTE_SECURITY_TPM_2_0`.
(The emulated TPM is just a process running on the host, so the concept of
inventory doesn't apply.) The two traits represent the two different versions
of the TPM spec that are currently supported. (A summary of the differences
between the two versions is currently available here_.) The flavor extra-specs
or image properties could then specify something like
`trait:COMPUTE_SECURITY_TPM_1_2=required` to indicate that they wish to have
access to a TPM.  Virt drivers which could provide a TPM to their instances
would be responsible for setting either (or both) of the two traits on the
compute nodes.  If an instance has specified one of the traits in the flavor
or image, the virt driver will do whatever is needed to provide a TPM to the
instance. If for any reason this is not possible, the instance creation will
fail.

When using `COMPUTE_SECURITY_TPM_2_0`, there are two possible device models for
the emulated TPM device, `TIS` and `CRB`.  By default the `TIS` model will be
used, but it can also be explicitly specified by setting
`hw:tpm_model=TIS` in the image or `hw_tpm_model=TIS` in
the image properties.  The CRB option can be specified by setting
`hw:tpm_model=CRB` in the flavor (or via the equivalent image
property).  In the case of libvirt/qemu, the version of libvirt that supports
TPM 2.0 (v4.5.0) also supports the `CRB` device model.

If both the flavor and the image specify a TPM trait or device model and the
two values do not match, an exception will be raised.  If the CRB model is
specified with `COMPUTE_SECURITY_TPM_1_2` the hypervisor will fail to create
the instance.

As a future enhancement beyond the scope of the immediate work, it would be
possible to extend this to support physical TPM passthrough.  In this case the
virt driver would also advertise an inventory with a resource class of ``PTPM``
with ``total=1`` (since current hardware only has a single TPM), and the image
or flavor could request it by specifying `resources:PTPM=1`.  The trait would
not be necessary in this case, as the desire for a TPM in the instance is
implied by the resource request.  Also, for TPM passthrough the device model
is controlled by the actual hardware device.

As part of implementing the this feature, the nova cold migration code will
need to copy over the directory containing the emulated TPM files.  For
libvirt this would mean copying the file under
/var/lib/libvirt/swtpm/<instance> from within
LibvirtDriver.migrate_disk_and_power_off().

Shelve/unshelve could be supported by saving the persistent TPM data as a
glance image during the shelve operation, and recreating it (and deleting
the image) during unshelve.

Resizing will result in a reschedule, so shouldn't be a problem.  If the admin
resizes from a flavor with TPM to a flavor without TPM nova won't care, but it
might cause problems in the guest.

Rebuilding to a new image is problematic if the new image specifies a TPM
trait and the current host cannot provide TPM support.  This will cause the
rebuild to fail.  In this case, the user would need to rebuild with a suitable
image.

It should be noted that if a compute node goes down and the VM has to be
rebuilt on another compute node then we're going to lose any emulated TPM data.
In the shared-storage case this is exactly analogous to taking the hard drive
out of one physical machine and putting it into another physical machine.

.. _here: https://en.wikipedia.org/wiki/Trusted_Platform_Module#TPM_1.2_vs_TPM_2.0

Alternatives
------------

Rather than using a trait, we could instead use a resource with a large
inventory.


Data model impact
-----------------

None

REST API impact
---------------

None

Security impact
---------------

The guest will be able to use the emulated TPM for all the security enhancing
functionality that a physical TPM provides, in order to protect itself against
attacks from within the guest.  The guest must still trust the host.

Notifications impact
--------------------

None

Other end user impact
---------------------

There are no immediate plans to make emulated TPM work over shelve/unshelve.
To make this work reliably would require saving the persistent TPM data file
to a glance image or swift object on "shelve" and then recover the data on
"unshelve".

Instances which use UEFI NVRAM are currently in a similar position, as the
NVRAM is not persisted over shelve/unshelve.

Performance Impact
------------------

Negligible.

Other deployer impact
---------------------

None

Developer impact
----------------

The various virt drivers would be able to implement the emulated vTPM as
desired.

Upgrade impact
--------------

If a config option is needed to opt-in to emulated TPM support, the operator
would need to set the config option appropriately after an upgrade.


Implementation
==============

Assignee(s)
-----------

Primary assignee:
  cfriesen

Other contributors:
  None

Work Items
----------

* Support for new placement traits

* Libvirt driver changes to report traits to placement

* Libvirt driver changes to enable specifying libvirt XML

* Libvirt driver changes to copy vTPM files on cold migration.


Dependencies
============

* Up-to-date qemu/libvirt

* "swtpm" binary and libraries


Testing
=======

Unit and functional testing will be added.


Documentation Impact
====================

Operations Guide and End User Guide will be updated appropriately.
Feature support matrix will be updated.


References
==========

* Qemu docs on tpm:
  https://github.com/qemu/qemu/blob/master/docs/specs/tpm.txt

* Libvirt XML to request emulated TPM device:
  https://libvirt.org/formatdomain.html#elementsTpm


History
=======

.. list-table:: Revisions
   :header-rows: 1

   * - Release Name
     - Description
   * - Stein
     - Introduced
   * - Train
     - Re-proposed
