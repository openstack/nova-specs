..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

================================================================
Pick guest CPU architecture based on host arch in libvirt driver
================================================================

https://blueprints.launchpad.net/nova/+spec/pick-guest-arch-based-on-host-arch-in-libvirt-driver

Implement new image meta property that allows for the selection of the
correct QEMU binary, cpu architecture, and machine type for a guest
architecture that is different than the host architecture; An x86_64
guest running on an AArch64 host, and vice versa.

Problem description
===================

Currently, in many places, Nova's libvirt driver makes decisions on how
to configure guest XML based on *host* CPU architecture
``caps.host.cpu.arch``. That is not optimal in all cases where physical
hardware support is limited for non-traditional architectures.

So all of the said code needs to be reworked to make those decisions
based on ``guest`` CPU architecture (i.e. ``guest.arch``, which should be
set based on the image metadata property, ``hw_emulation_architecture``).

A related piece of work is to distinguish between hosts that can do AArch64,
PPC64, Etc. via KVM (which is hardware-accelerated) vs. those that can only
do it via plain emulation ``TCG`` — this is to ensure that guests are not
arbitrarily scheduled on hosts that are incapable of hardware acceleration,
thus losing out on performance-related benefits.

Use Cases
---------

* As an admin/operator I want to allow for cpu architecture emulation due to
  constraints of or lack with alternate physical architecture types.

* As an admin/operator I want to deploy AArch64, PPC64, MIPs, RISC-V, and
  s390x as an emulated architecture on x86_64.

* As an admin/operator I want to deploy x86_64, PPC64, MIPs, RISC-V, and
  s390x as an emulated architecture on AArch64.

Proposed change
===============

To enable this new cpu architecture spec, an image property will
be introduced and an additional function which allows for checks and
comparisions between the host architecture and desired emulation architecture

.. note::

   The following ``hw_architecture`` image property relates to the physical
   architecture of the compute hosts. If physical nodes are not present for
   the desired architecture then the instance will not be provisioned.

Retrieve OS architecture for LibvirtConfigGuest
-----------------------------------------------

This leverages nova virt libvirt config to grab the ``os_arch`` and update
the ``hw_architecture`` image meta property with the retrieved value. With
this change we can perform the required comparisons within nova virt libvirt
driver for the ``hw_architecture`` and ``hw_emulation_architecture`` values.

.. code-block:: python

   if self.os_arch is not None:
       type_node.set("arch", self.os_arch)

Allow emulation architecture to be defined by image property
------------------------------------------------------------

To enable defining the guest architecture the following string based image
meta property will be introduced:

* ``hw_emulation_architecture``

When this image property is not defined then instance provisioning will
occur as normal. The process is demonstrated below via the 3 examples.

**Example 1** When both image meta properties are set the emulation
architecture will take precedent, and it will build on a X86_64 host that
supports emulatating AARCH64 or whatever supported architecture is inputted
in place of AARCH64.

* ``hw_emulation_architecture = AARCH64``
* ``hw_architecture = X86_64``

**Example 2** When the emulation image meta property is set the emulation
architecture will take precedent, and it will build on any host that
supports emulating X86_64 or whatever supported architecture is inputted
in place of X86_64.

* ``hw_emulation_architecture = X86_64``
* ``hw_architecture = <unset>``

**Example 3** When the ``hw_emulation_architecture`` property is unset it
will build on any host that natively supports the specified architecture.

* ``hw_emulation_architecture = <unset>``
* ``hw_architecture = AARCH64`` OR ``hw_architecture = X86_64``

Update scheduler request_filter to handle both architecture fields
------------------------------------------------------------------

Within the ``transform_image_metadata`` function, we will add the two
architecture properties to the ``prefix_map``. this in itself also requires
additional os-traits to be added for both **hw** and **compute**.

.. code-block:: python

   def transform_image_metadata(ctxt, request_spec):
       """Transform image metadata to required traits.

       This will modify the request_spec to request hosts that support
       virtualisation capabilities based on the image metadata properties.
       """
       if not CONF.scheduler.image_metadata_prefilter:
           return False

       prefix_map = {
           'hw_cdrom_bus': 'COMPUTE_STORAGE_BUS',
           'hw_disk_bus': 'COMPUTE_STORAGE_BUS',
           'hw_video_model': 'COMPUTE_GRAPHICS_MODEL',
           'hw_vif_model': 'COMPUTE_NET_VIF_MODEL',
           'hw_architecture': 'HW_ARCH',
           'hw_emulation_architecture': 'COMPUTE_ARCH',
       }


Update os-traits
----------------

Below are the os-traits proposed for the compute cpu architectures to be
supported for emulatation, where as the hardware architecture includes all
current nova supported architectures within nova objects fields.

.. code-block:: python

   TRAITS = [
       'AARCH64',
       'PPC64LE',
       'MIPSEL',
       'S390X',
       'RISCV64',
       'X86_64',
   ]

To account for the emulation of these architectures, updates will be made
to the nova virt libvirt driver ensuring that compute capability traits
are reported for each architecture emulator that is available on the hosts.

Perform architecture test against emulation
-------------------------------------------

To facilitate a simple check throughout the nova virt libvirt driver the
following function does a check and will set the appropriate guest
architecture based on emulation, if defined.

.. code-block:: python

   def _check_emulation_arch(self, image_meta):
       emulation_arch = image_meta.properties.get("hw_emulation_architecture")
       if emulation_arch:
           arch = emulation_arch
       else:
           arch = libvirt_utils.get_arch(image_meta)
       return arch


Utilization of the actual check performed through processing the image_meta
dictionary values.

.. code-block:: python

   arch = self._check_emulation_arch(image_meta)

Proposed emulated architectures and current support level
---------------------------------------------------------

All testing performed with changes proposed in this spec demonstrated that
the emulated guests maintain current support for all basic lifecycle actions.
Listed below are the proposed architectures and there current functional
level with the spec, with the plan of all being ``Tested and validated for
functional support``.

* ``X86_64`` - Tested and validated for functional support
* ``AARCH64`` - Tested and validated for functional support
* ``PPC64LE`` - Tested and validated for functional support
* ``MIPSEL`` - Awaiting libvirt patch for PCI support
* ``S390X`` - Troubleshooting guest kernel crash for functional support
* ``RISCV64`` - To be Tested

Alternatives
------------

Other attempts have been made leverage existing image meta properties such
as ``hw_architecture`` only; however, this opens various other issues with
conflicting check and alterations of core code. This also runs into issues
during the scheduling of instances as there will be no matching physical
host architectures, which is what this spec aims to solves.

While the best option is providing actual physical support for the
cpu architectures you want to test, this opens the ability to a wider
audience to perform the same type of local emulation they can with QEMU
within an openstack environment.


Data model impact
-----------------

* Adds a new set of standard traits to os-traits.
* Adds new property to image_meta objects.
* The OS arch value will be pulled into the ``LibvirtConfigGuest``.

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

This is expected to improve boot performance in a heterogeneous cloud
by reducing reschedules. By passing a more constrained request to
placement this feature should also reduce the resulting set of
allocation_candidates that are returned.

This will also ensure that native support is handled first over emulation
as it requires a specific property to be set in order to perform the
required checks.

Other deployer impact
---------------------

Ensure that all the desired QEMU binaries are installed on the physical
nodes for the cpu architectures that you would like to support.

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
  chateaulav - Jonathan Race

Feature Liaison
---------------

Feature liaison:
  Liaison Needed

Work Items
----------

- Add new traits
- Update prefilter
- Modify nova libvirt virt driver to perform checks for emulation architecture
- Add new property to image_meta objects
- Modify nova libvirt virt config to pull OS arch into LibvirtConfigGuest
- Tests

Dependencies
============

**Blueprint**

* https://blueprints.launchpad.net/nova/+spec/pick-guest-arch-based-on-host-arch-in-libvirt-driver

**Project Changesets**

* https://review.opendev.org/c/openstack/nova/+/822053
* https://review.opendev.org/c/openstack/os-traits/+/824050

**Libvirt MIPs PCI Bug**

* https://bugzilla.redhat.com/show_bug.cgi?id=1432101

Testing
=======

Unit tests will be added for validation of the following proposed changes:

* **nova virt libvirt driver** to validate handling of the
  ``hw_emulation_architecture`` image property value and associated checks.
* **nova scheduler request_filter** to ensure proper handling of the
  prefilter, with added the two new values.

Proposed updates to tempest will account for the non-native architectures
being supported through emulation.

* AARCH64 architecture will be tested with every patch
* Remaining architectures will be tested with the ``periodic-weekly`` and
  ``experimental`` pipelines.

Documentation Impact
====================

A release note will be added. As there is enduser impact, user facing
documentation will be required for the supported emulation architecture
types and the required image meta properties to need to be set.

References
==========

* http://lists.openstack.org/pipermail/openstack-discuss/2022-January/026544.html
* https://blueprints.launchpad.net/nova/+spec/pick-guest-arch-based-on-host-arch-in-libvirt-driver

History
=======

.. list-table:: Revisions
   :header-rows: 1

   * - Release Name
     - Description
   * - Yoga
     - Introduced
