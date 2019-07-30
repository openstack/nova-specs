..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

=====================================================
Allow Secure Boot (SB) for QEMU- and KVM-based guests
=====================================================

https://blueprints.launchpad.net/nova/+spec/allow-secure-boot-for-qemu-kvm-guests

Problem description
===================

Today, Nova's libvirt driver only has support for generic UEFI boot, but
not Secure Boot (the goal of which is to: "make sure no unsigned kernel
code runs on the machine") for QEMU and KVM guests.  Secure Boot
protects guests from boot-time malware, and validates that the code
executed by the guest firmware is trusted.

More precisely, the libvirt driver has the OVMF (the open source
implementation of UEFI for virtual machines) binary file's path
hard-coded in a variable::

    [...]
    DEFAULT_UEFI_LOADER_PATH = {
        "x86_64": "/usr/share/OVMF/OVMF_CODE.fd",
        "aarch64": "/usr/share/AAVMF/AAVMF_CODE.fd"
    }
    [...]

The above only provides generic UEFI boot [1]_, but not Secure Boot.
Also it is not robust to hardcode OVMF binary file paths this way.

This specification proposes to extend the existing support for UEFI boot
in Nova's libvirt driver to also support Secure Boot.  Refer to the
sections :ref:`Proposed change <Proposed change>` and :ref:`Work Items
<Work items>` for what needs to be done to support the Secure Boot for
KVM / QEMU guests.  In this spec, we focus only the ``x86_64``
architecture.

NB: Nova's Hyper-V driver already has support for Secure Boot; it was
added in commit: 29dab99 -- "Hyper-V: Adds Hyper-V UEFI Secure Boot"
[2]_.

Use Cases
---------

A non-exhaustive list:

* Protect the Nova instances being launched from boot-time malware from
  the guest side.

* Secure Boot will prevent the Nova instance from running untrusted code
  by requiring a trusted signature on UEFI binaries.  More detail on it,
  refer to the "Testing Secure Boot" guide here [3]_.

* Secure Boot will allow trustworthy code in Nova instances to: (a)
  enable the Secure Boot operational mode (for protecting itself), and;
  (b) prevent malicious code in the guests from circumventing the actual
  security of the Secure Boot operational mode.

* And, as a refresher, benefits of using OVMF are listed in the
  "Motivation" section of the OVMF white paper [4]_.  And for a more
  detailed treatment of Secure Boot, refer to this [5]_.


.. _`Proposed change`:

Proposed change
===============

To allow Secure Boot for KVM and QEMU guests, the following are the
rough set of planned changes:

- Reuse the existing Nova metadata property, ``os_secure_boot`` (added
  for Hyper-V support) to allow user to request Secure Boot support.

- In the initial implemetation, Nova will only support the default UEFI
  keys, which will work with most distributions (Debian, Ubuntu, SUSE,
  Fedora, CentOS and RHEL)—as they provide a variables file ("VARS")
  with default UEFI keys enrolled.  (If you don't trust the default UEFI
  keys, then it is equivalent to you not trusting the filesystem where
  your compute node is running.)  If later desired, we can reuse the
  existing image metadata property, ``os_secure_boot_signature`` that
  lets you specify bootloader's signature.

- Make Nova use libvirt's interface for auto-selecting firmware
  binaries; this was added in libvirt 5.2 [6]_.  Why?

  Problem: Today, Nova does not have a sensible way of knowing which
  firmware binary to select.  All it sees is the firmware binary path
  that is hard-coded, which is ugly and fragile.  Not least of all, it
  is non-trivial to tell whether that binary supports Secure Boot or
  not.

  Solution: Here is where libvirt's firmware auto-selection comes into
  picture.  It takes advantage of a lot of work done in QEMU and OVMF,
  and fixes the above mentioned problem by providing a robust interface.
  As in, libvirt can now pick up the *correct* OVMF binary, with Secure
  Boot (SB) and System Management Mode (SMM) enabled, with a convenient
  XML config::

        <os firmware='efi'>
          <loader secure='yes'/>
        </os>

  We will use the libvirt's formal interface that allows auto-selecting
  firmware binaries—it is also far less code for Nova.  And we will
  document that Nova will only support Secure Boot given they have
  ``MIN_LIBVIRT_SECURE_BOOT_VERSION`` and
  ``MIN_QEMU_SECURE_BOOT_VERSION`` constants.

  This libvirt feature takes advantage of QEMU's firmware description
  schema [7]_.

- Make Nova programatically query the getDomainCapabilities() API to
  check if libvirt supports the relevant Secure Boot-related features.
  Introduce a _has_uefi_secure_boot_support() method to check if libvirt
  can support the feature.  This can be done by checking for the
  presence of ``efi`` and ``secure`` XML attributes from the output of
  the getDomainCapabilities() API.

- In the initial implementation, there will be no scheduler support to
  isolate hosts that are not Secure Boot-capable, similar to existing
  basic UEFI boot support.  Nova will error-out if the host hypervisor
  does not support Secure Boot.


Low-level background on different kinds of OVMF builds
------------------------------------------------------

[Thanks: Laszlo Ersek, OVMF maintainer, for the below discussion.  I
added, with permission, a good chunk of verbatim text from Laszlo.]

One feature that can be built into OVMF is the "Secure Boot Feature".
This is different from the operational mode called "Secure Boot" (SB).
If the firmware contains the feature, then the guest can enable or
disable the operational mode. If the firmware does not contain the
feature, then the guest cannot enable the operational mode.

Another feature that can be built into OVMF is called "SMM" (Secure
Management Mode). This means a driver stack that consists of a set of
privileged drivers that run in SMM, and another, interfacing set of
unprivileged drivers that only format requests for the privileged half,
and parse responses from it. Once the SMM feature is built into OVMF,
then SMM emulation by the QEMU platform is *non-optional*, it is
required.

The Secure Boot Feature and the SMM feature stack are orthogonal. You
can build OVMF in all four configurations. However, if you want to allow
trustworthy code in your guests to enable the Secure Boot operational
mode (for protecting itself), and *also* want to prevent malicious code
in your guests from *circumventing* the actual security of the Secure
Boot operational mode, then you have to build *both* features into OVMF.

NB: Different distributions ship different kinds of builds.  E.g.
Fedora ships both variants of OVMF firmware binaries: one without either
SB or SMM, and the other with both SB or SMM. Other distributions ship
different builds as well, and under different pathnames.  Even if they
ship an SB+SMM OVMF build, the path name for the firmware binary may be
different.

OVMF binary files and variable store ("VARS") file paths
--------------------------------------------------------

Each distribution has its *own* (but slightly different) path name of
OVMF:

- SUSE:
   - package name: "qemu-ovmf-x86_64";
   - ``/usr/share/qemu/ovmf-x86_64-opensuse-code.bin`` is the firmware
     binary built with SB and SMM
   - ``/usr/share/qemu/ovmf-x86_64-opensuse-vars.bin`` is the variable
     store template that matches the above binary

- Fedora:
   - package name: "edk2-ovmf" (x86_64)
   - ``/usr/share/edk2/ovmf/OVMF_CODE.fd`` is a firmware binary built
     without either SB or SMM
   - ``/usr/share/edk2/ovmf/OVMF_CODE.secboot.fd`` is a firmware
     binary built with both SB and SMM
   - ``/usr/share/edk2/ovmf/OVMF_VARS.fd`` is the variable store
     template that matches both of the above binaries
   - ``/usr/share/edk2/ovmf/OVMF_VARS.secboot.fd`` is the variable store
     template *with* the default UEFI keys enrolled

- RHEL-7.6:
   - package name: "ovmf" (x86_64)
   - ``/usr/share/OVMF/OVMF_CODE.secboot.fd`` is the firmware binary,
     built with SB plus SMM
   - ``/usr/share/OVMF/OVMF_VARS.secboot.fd`` is the matching variable
     store template

- Debian:
   - package name: "ovmf" (x86_64)
   - ``/usr/share/OVMF/OVMF_CODE.fd`` is the firmware binary built with
     SB plus SMM.

- Ubuntu:
   - same as Debian

This is one of the tricky parts, but thankfully, the libvirt release 5.2
vastly simplifies the OVMF file name handling — by providing an
interface to auto-select firmware (which in turn, takes advantage of the
firmware description files from QEMU (provided by QEMU 2.9 and above).

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

With this feature, KVM- and QEMU-based Nova instances can get Secure
Boot support.  Thus protecting the guests from boot-time malware, and
ensures the code that the firmware executes only trusted code.

Notifications impact
--------------------

None.

Other end user impact
---------------------

None.

Performance Impact
------------------

None.

Other deployer impact
---------------------

None.

Developer impact
----------------

None.

Upgrade impact
--------------

None.

Implementation
==============

Assignee(s)
-----------

Primary assignee:
    Kashyap Chamarthy <kchamart@redhat.com>


.. _`Work Items`:

Work Items
----------

Taking the ``x86_64`` architecture as an example here.  The following
are the work items for enabling Secure Boot support for QEMU and KVM
guests:

1. Make sure Nova configures the SMM (System Management Mode) hypervisor
   feature in the guest XML when Secure Boot is requested::

      <features>
        [...]
        <smm state='on'/>
      </features>

   Note that when using libvirt's firmware auto-selection feature,
   libvirt will auto-add the SMM feature when starting the guest when SB
   is requested, because SMM and SB go hand-in-hand.

2. Make sure the OVMF ``loader`` and ``nvram`` related guest XML snippet
   looks as follows (for a Fedora guest with Q35 machine type using an
   OVMF build with SMM + SB enabled)::

      <os>
        <type arch='x86_64' machine='pc-q35-3.0'>hvm</type>
        <loader readonly='yes' secure='yes' type='pflash'>/usr/share/edk2/ovmf/OVMF_CODE.secboot.fd</loader>
        <nvram template='/export/vmimages/fedora_VARS.secboot.fd'>/var/lib/libvirt/qemu/nvram/fedora_VARS.secboot.fd</nvram>
        <boot dev='hd'/>
      </os>

   Note that Nova doesn't need to worry about the NVRAM store, from a
   file management point of view — because with libvirt's firmware
   auto-selection feature, it also detects the NVRAM store associated
   with the firmware image, copies it into the guest's private path, and
   asks the guest to use it.

   NB-1: The paths for the UEFI binary are different for different
   distributions — but libvirt will handle that for us.

   NB-2: Q35 machine type is *mandatory* for Secure Boot with OVMF.

3. For guests to truly get Secure Boot, we need to ensure that the
   non-volatile store ("VARS") file (in the above example,
   `fedora_VARS.secboot.fd`) has the default UEFI keys enrolled.

   There are two ways to achieve that.  The first, use the "VARS"
   template file (*with* UEFI keys enrolled) that is shipped by your
   Linux distribution; this is the preferred method.  The second, you
   can enroll the default UEFI keys in the "VARS" file, using the
   ``UefiShell.iso`` + ``EnrollDefaultKeys.efi`` utilities shipped by
   various Linux distributions (as part of their EDK2 / OVMF packages),
   and place it in the appropriate location.  There is a tool (refer
   below) some Linux distributions ship which automates the key
   enrollment process.  The tool is used as follows:

   (a) Run the ``ovmf-vars-generator`` tool (adjust the parameters
       based on distibution) once::

            $> ./ovmf-vars-generator \
                  --ovmf-binary /usr/share/edk2/ovmf/OVMF_CODE.secboot.fd \
                  --uefi-shell-iso /usr/share/edk2/ovmf/UefiShell.iso \
                  --ovmf-template-vars /usr/share/edk2/ovmf/OVMF_VARS.fd \
                  --fedora-version 29 \
                  --kernel-path /tmp/kernel \
                  --kernel-url /path/to/vmlinuz \
                  template_VARS.fd
            ...
            INFO:root:Created and verified template_VARS.fd

   (b) Reboot the guest with a pointer to a unique copy of the above
       ``template_VARS.fd``.  At which point, you will *actually* see
       Secure Boot enabled. Which can be verified via `dmesg`::

            (fedora-vm)$ dmesg | grep -i secure
            [    0.000000] secureboot: Secure boot enabled
            [    0.000000] Kernel is locked down from EFI secure boot; see man kernel_lockdown.7

   However, as noted earlier, no need to run the above steps manually.
   Most common Linux distributions (SUSE, Fedora, RHEL) already ship a
   "VARS" file with default UEFI keys enrolled.  Debian and Ubuntu are
   actively working on it [8]_.

   If your distribution doesn't ship a "VARS" file with default UEFI
   keys enrolled, here [9]_ is a little Python tool,
   ``ovmf-vars-generator`` that will automate the above three steps.
   This is packaged in Fedora as a sub-RPM of EDK2/OVMF, called
   'edk2-qosb'.  Ubuntu has included this tool in its firmware package.

4. Document the way to generate the above-mentioned "VARS" file using
   the tool ``ovmf-vars-generator``.  This tool is already shipped as a
   sub-package (called: 'edk2-qosb') of the main 'edk2' / OVMF in
   different distributions.  And Ubuntu and Debian are also working to
   ship this script.


Dependencies
============

* For the SMM (System Management Mode) feature, only the QEMU Q35
  machine type is supported.

* QEMU >=2.4 to get Secure Boot support.

* QEMU >=4.1.0 (releases in July/August 2019) to get the firmware
  descriptor documents that conform to QEMU's ``firmware.json``
  specification.  Here [10]_ are some examples of the said "firmware
  descriptor documents".  (NB: This does *not* block the spec for Train,
  and is a convenient-to-have.)

* libvirt >=5.3 (releases in May 2019) for the firmware auto-selection
  feature and the ability to query the availability of ``efi`` [11]_
  firmware via the getDomainCapabilities() API.

Testing
=======

This feature should be possible (assuming the earlier-mentioned
minimum libvirt and QEMU versions are available) to test in the upstream
gating environment.  Where the Nova instance should be able to boot a
KVM guest with Secure Boot (using OVMF), and verify in `dmesg` that
Secure Boot is *actually* in effect.


Documentation Impact
====================

Document how to boot ``x86_64`` Nova instances with Secure Boot for QEMU
and KVM guests using OVMF.  And update Glance's "Useful image
properties" documentation [12]_.


References
==========

.. [1] The blueprint that added initial support for booting from a UEFI
       image:
       https://specs.openstack.org/openstack/nova-specs/specs/mitaka/implemented/boot-from-uefi.html

.. [2] https://specs.openstack.org/openstack/nova-specs/specs/ocata/implemented/hyper-v-uefi-secureboot.html

.. [3] https://wiki.ubuntu.com/UEFI/SecureBoot/Testing

.. [4] The OVMF whitepaper:
       http://www.linux-kvm.org/downloads/lersek/ovmf-whitepaper-c770f8c.txt

.. [5] An overview of Secure Boot:
       http://www.rodsbooks.com/efi-bootloaders/secureboot.html

.. [6] The libvirt feature that allows auto-selection of firmware:
       https://libvirt.org/git/?p=libvirt.git;a=commitdiff;h=1dd24167b
       ("news: Document firmware autoselection for QEMU driver")

.. [7] QEMU's firmware schema file that describes the different uses
       and properties of virtual machine firmware:
       https://git.qemu.org/?p=qemu.git;a=blob;f=docs/interop/firmware.json

.. [8] Refer to the first point:
        "debian/patches/enroll-default-keys.patch: Build
        EnrollDefaultKeys.efi to provide an automated way of injecting
        Microsoft signing keys in VMs that need them." --
        https://launchpad.net/ubuntu/+source/edk2/0~20190309.89910a39-1ubuntu1

.. [9] A tool to generate OVMF variables file with default Secure Boot keys
       enrolled -- https://github.com/puiterwijk/qemu-ovmf-secureboot/

.. [10] The EDK2 firmware descriptor files are located here:
        https://git.qemu.org/?p=qemu.git;a=tree;f=pc-bios/descriptors.
        E.g. the descriptor for "UEFI firmware for x86_64, with Secure
        Boot and SMM":
        https://git.qemu.org/?p=qemu.git;a=blob;f=pc-bios/descriptors/50-edk2-x86_64-secure.json;

.. [11] The BIOS-related libvirt guest XML attributes:
        https://libvirt.org/formatdomain.html#elementsOSBIOS


.. [12] https://docs.openstack.org/glance/rocky/admin/useful-image-properties.html


History
=======

.. list-table:: Revisions
   :header-rows: 1

   * - Release Name
     - Description
   * - Train
     - Introduced

