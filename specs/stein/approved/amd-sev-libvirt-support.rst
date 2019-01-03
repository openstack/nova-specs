..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

====================================================
libvirt driver launching AMD SEV-encrypted instances
====================================================

https://blueprints.launchpad.net/nova/+spec/amd-sev-libvirt-support

This spec proposes work required in order for nova's libvirt driver to
support launching of KVM instances which are encrypted using `AMD's
SEV (Secure Encrypted Virtualization) technology
<https://developer.amd.com/sev/>`_.


Problem description
===================

While data is typically encrypted today when stored on disk, it is
stored in DRAM in the clear.  This can leave the data vulnerable to
snooping by unauthorized administrators or software, or by hardware
probing.  New non-volatile memory technology (NVDIMM) exacerbates this
problem since an NVDIMM chip can be physically removed from a system
with the data intact, similar to a hard drive.  Without encryption any
stored information such as sensitive data, passwords, or secret keys
can be easily compromised.

AMD's SEV offers a VM protection technology which transparently
encrypts the memory of each VM with a unique key.  It can also
calculate a signature of the memory contents, which can be sent to the
VM's owner as an attestation that the memory was encrypted correctly
by the firmware.  SEV is particularly applicable to cloud computing
since it can reduce the amount of trust VMs need to place in the
hypervisor and administrator of their host system.

Use Cases
---------

#. As a cloud administrator, in order that my users can have greater
   confidence in the security of their running instances, I want to
   provide a flavor containing an SEV-specific `required trait extra
   spec
   <https://docs.openstack.org/nova/latest/user/flavors.html#extra-specs-required-traits>`_
   which will allow users booting instances with that flavor to ensure
   that their instances run on an SEV-capable compute host with SEV
   encryption enabled.

#. As a cloud user, in order to not have to trust my cloud operator
   with my secrets, I want to be able to boot VM instances with SEV
   functionality enabled.

Proposed change
===============

For Stein, the goal is a minimal but functional implementation which
would satisfy the above use cases.  It is proposed that initial
development and testing would include the following deliverables:

- Add detection of host SEV capabilities.  Logic is required to check
  that the various layers of the hardware and software hypervisor
  stack are SEV-capable:

  - The presence of the following XML in the response from a libvirt
    `virConnectGetDomainCapabilities()
    <https://libvirt.org/html/libvirt-libvirt-domain.html#virConnectGetDomainCapabilities>`_
    API call `indicates that both QEMU and the AMD Secure Processor
    (AMD-SP) support SEV functionality
    <https://libvirt.org/git/?p=libvirt.git;a=commit;h=6688393c6b222b5d7cba238f21d55134611ede9c>`_::

        <domainCapabilities>
          ...
          <features>
            ...
            <sev supported='yes'/>
              ...
            </sev>
          </features>
        </domainCapabilities>

    This functionality-oriented check should preempt the need for any
    version checking in the driver.

  - ``/sys/module/kvm_amd/parameters/sev`` should have the value ``1``
    to indicate that the kernel has SEV capabilities enabled.  This
    should be readable by any user (i.e. even non-root).

  Note that both checks are required, since the presence of the first
  does not imply the second.

- Support a standard trait which would be automatically detected per
  compute host based on the above logic.  This would most likely be
  called ``HW_CPU_AMD_SEV`` or similar, as an extension of `the
  existing CPU traits mapping
  <https://github.com/openstack/nova/blob/c5a7002bd571379818c0108296041d12bc171728/nova/virt/libvirt/utils.py#L47>`_.

- When present in the flavor, this standard trait would indicate that
  the libvirt driver should include extra XML in the guest's domain
  definition, in order to ensure the following:

  - SEV security is enabled.

  - The boot disk cannot be ``virtio-blk`` (due to a resource constraint
    w.r.t. bounce buffers).

  - The VM uses machine type ``q35`` and UEFI via OVMF.  (``q35`` is
    required in order to bind all the virtio devices to the PCIe
    bridge so that they use virtio 1.0 and *not* virtio 0.9, since
    QEMU's ``iommu_platform`` feature is added in virtio 1.0 only.)

  - The ``iommu`` attribute is ``on`` for all virtio devices.  Despite
    the name, this does not require the guest or host to have an IOMMU
    device, but merely enables the virtio flag which indicates that
    virtualized DMA should be used.  This ties into the SEV code to
    handle memory encryption/decryption, and prevents IO buffers being
    shared between host and guest.

    The DMA will go through bounce buffers, so some overhead is expected
    compared to non-SEV guests.

    (Note: virtio-net device queues are not encrypted.)

  - All the memory regions allocated by QEMU must be pinned, so that
    they cannot be swapped to disk.  This can be achieved by setting a
    hard memory limit via ``<hard_limit>`` in the ``<memtune>``
    section of the domain's XML.  This does *not* reflect a
    requirement for additional memory; it is only required in order to
    achieve the memory pinning.

    Another method for pinning the memory is to enable `hugepages
    <https://docs.openstack.org/nova/rocky/admin/huge-pages.html>`_ by
    booting with the ``hw:mem_page_size=large`` property set either on
    the flavor or the image, although these have the minor
    disadvantages of requiring the operator or user to remember one
    extra detail, and also may require undesirable duplication of
    flavors or images.

    Note that this memory pinning is expected to be a temporary
    requirement; the latest firmwares already support page copying (as
    documented by the ``COPY`` API in the `AMD SEV-KM API
    Specification`_), so when OS starts supporting the page-move or
    page-migration commmand then it will no longer be needed.

    Based on instrumentation of QEMU, the limit per VM should be
    calculated and accounted for as follows:

    =======================  =====================  ==========================
    Memory region type       Size                   Accounting mechanism
    =======================  =====================  ==========================
    VM RAM                   set by flavor          placement service
    video memory             set by flavor/image    placement service
    UEFI ROM                 4096KB                 `reserved_host_memory_mb`_
    UEFI var store (pflash)  4096KB                 `reserved_host_memory_mb`_
    pc.rom                   128KB                  `reserved_host_memory_mb`_
    isa-bios                 128KB                  `reserved_host_memory_mb`_
    ACPI tables              2384KB                 `reserved_host_memory_mb`_
    =======================  =====================  ==========================

.. _reserved_host_memory_mb:
   https://docs.openstack.org/nova/rocky/configuration/config.html#DEFAULT.reserved_host_memory_mb

    It is also recommended to include an additional padding of at
    least 256KB for safety, since ROM sizes can occasionally change.
    For example the total of 10832KB required here for ROMs / ACPI
    tables could be rounded up to 16MB.

    The first two values are expected to commonly vary per VM, and
    are already accounted for dynamically by the placement service.

    The remainder have traditionally (i.e. for non-SEV instances) been
    accounted for alongside the overhead for the host OS via nova's
    memory pool defined by the `reserved_host_memory_mb`_ config
    option, and this does not need to change.  However, whilst the
    overhead incurred is no different to that required for non-SEV
    instances, it is much more important to get the hard limit right
    when pinning memory; if it's too low, the VM will get killed, and
    if it's too high, there's another risk of the host's OOM killer
    being invoked, or failing that, the host crashing because it
    cannot reclaim the memory used by the guest.

    Therefore it may be prudent to implement an extra check which
    multiplies this reservation requirement by the number of instances
    and ensures that it does not cause the host's memory usage to
    exceed what's available.  This can probably be initially
    implemented as a check in the driver, but regardless, the way to
    avoid this over-commitment must be documented so that operators
    can correctly plan memory usage and configure their cloud
    accordingly.

  So for example assuming a 4GB VM::

      <domain type='kvm'>
        <os>
          <type arch='x86_64' machine='pc-q35-2.11'>hvm</type>
          <loader readonly='yes' type='pflash'>/usr/share/qemu/ovmf-x86_64-ms-4m-code.bin</loader>
          <nvram>/var/lib/libvirt/qemu/nvram/sles15-sev-guest_VARS.fd</nvram>
          <boot dev='hd'/>
        </os>
        <launchSecurity type='sev'>
          <cbitpos>47</cbitpos>
          <reducedPhysBits>1</reducedPhysBits>
          <policy>0x0037</policy>
        </launchSecurity>
        <memtune>
          <hard_limit unit='KiB'>4718592</hard_limit>
          ...
        </memtune>
        <devices>
          <rng model='virtio'>
            <driver iommu='on'/>
            ...
          </rng>
          <memballoon model='virtio'>
            <driver iommu='on' />
            ...
          </memballoon>
          ...
          <video>
            <model type='qxl' ram='65536' vram='65536' vgamem='16384' heads='1'  primary='yes'/>
          </video>
          ...
        </devices>
        ...
      </domain>

If SEV's requirement of a Q35 machine type cannot be satisfied by
``hw_machine_type`` specified by the image (if present), or the value
specified by ``libvirt.hw_machine_type`` in ``nova.conf`` (`which is
not set by default
<https://docs.openstack.org/nova/rocky/configuration/config.html#libvirt.hw_machine_type>`_),
then an exception should be raised so that the build fails.

``cbitpos`` and ``reducedPhysBits`` are dependent on the processor
family, and can be obtained through the ``sev`` element from `the
domain capabilities
<https://libvirt.org/formatdomaincaps.html#elementsSEV>`_.

``policy`` allows a particular SEV policy, as documented in `the AMD
SEV-KM API Specification`.  Initially the policy will be hardcoded and
not modifiable by cloud tenants or cloud operators. The policy will
be::

  #define SEV_POLICY_NORM \
      ((SEV_POLICY)(SEV_POLICY_NODBG|SEV_POLICY_NOKS| \
        SEV_POLICY_ES|SEV_POLICY_DOMAIN|SEV_POLICY_SEV))

which equates to ``0x0037``.  In the future, when support is added to
QEMU and libvirt, this will permit live migration to other machines in
the same cluster [#]_ (i.e. with the same OCA cert) and uses SEV-ES,
but doesn't permit other guests or the hypervisor to directly inspect
memory.  If the upstream support for SEV-ES does not arrive in time
then SEV-ES will be not be included in the policy.

A future spec could be submitted to make this configurable via an
extra spec or image property.

For reference, `the AMDSEV GitHub repository
<https://github.com/AMDESE/AMDSEV/>`_ provides `a complete example
<https://github.com/AMDESE/AMDSEV/blob/master/xmls/sample.xml>`_ of a
domain's XML definition with `libvirt's SEV options
<https://libvirt.org/formatdomain.html#sev>`_ enabled.

The sum of the work described above could also mean that images with
the property ``trait:HW_CPU_AMD_SEV=required`` would similarly affect
the process of launching instances.

.. [#] Even though live migration is not currently supported by the
       hypervisor software stack, it will be in the future.

Limitations
-----------

The following limitations will be removed in the future as the
hardware, firmware, and various layer of software receive new
features:

- SEV-encrypted VMs cannot yet be live-migrated, or suspended,
  consequently nor resumed.  As already mentioned, support is coming
  in the future.  However this does mean that in the short term, usage
  of SEV will have an impact on compute node maintenance, since
  SEV-encrypted instances will need to be fully shut down before
  migrating off an SEV host.

- SEV-encrypted VMs cannot contain directly accessible host devices
  (PCI passthrough).  So for example mdev vGPU support will not
  currently work.  However technologies based on vhost-user should
  work fine.

- The boot disk of SEV-encrypted VMs cannot be ``virtio-blk``.  Using
  ``virtio-scsi`` or SATA for the boot disk works as expected, as does
  ``virtio-blk`` for non-boot disks.

The following limitations are expected long-term:

- The operating system running in an encrypted virtual machine must
  contain SEV support.

- The ``q35`` machine type does not provide an IDE controller,
  therefore IDE devices are not supported.  In particular this means
  that nova's libvirt driver's current default behaviour on the x86_64
  architecture of attaching the config drive as an ``iso9660`` IDE
  CD-ROM device will not work.  There are two potential workarounds:

  #. Change ``CONF.config_drive_format`` in ``nova.conf`` from `its
     default value
     <https://docs.openstack.org/nova/rocky/configuration/config.html#DEFAULT.config_drive_format>`_
     ``iso9660`` to ``vfat``.  This will result in ``virtio`` being
     used instead.  However this per-host setting could potentially
     break images with legacy OS's which expect the config drive to be
     an IDE CD-ROM.  It would also not deal with other CD-ROM devices.

  #. Set the (largely undocumented) ``hw_cdrom_bus`` image property to
     ``virtio-scsi``, which is recommended as a replacement for
     ``ide``.

  Some potentially cleaner long-term solutions which require code
  changes are suggested as a stretch goal in the `Work Items`_ section
  below.

For the sake of eliminating any doubt, the following actions are *not*
expected to be limited when SEV encryption is used:

- Cold migration or shelve, since they power off the VM before the
  operation at which point there is no encrypted memory

- Snapshot, since it only snapshots the disk

- Evacuate, since this is only initiated when the VM is assumed to be
  dead or there is a good reason to kill it

- Attaching any volumes, as long as they do not require attaching via
  an IDE bus

- Use of spice / VNC / serial / RDP consoles

- vNUMA

Alternatives
------------

#. Rather than immediately implementing automatic detection of
   SEV-capable hosts and providing access to these via a new standard
   trait (``HW_CPU_AMD_SEV`` or similar),

   - `create a custom trait
     <https://docs.openstack.org/osc-placement/latest/cli/index.html#trait-create>`_
     specifically for the purpose of marking flavors as SEV-capable,
     and then

   - `manually assign that trait
     <https://docs.openstack.org/osc-placement/latest/cli/index.html#resource-provider-trait-set>`_
     to each compute node which is SEV-capable.

   This would have the minor advantages of slightly decreasing the
   amount of effort required in order to reach a functional prototype,
   and giving operators the flexibility to choose on which compute
   hosts SEV should be allowed.  But conversely it has the
   disadvantages of requiring merging of hardcoded references to a
   custom trait into nova's ``master`` branch, requiring extra work
   for operators, and incurring the risk of a compute node which isn't
   capable of SEV (either due to missing hardware or software support)
   being marked as SEV-capable, which would most likely result in VM
   launch failures.

#. Rather than using a single trait to both facilitate the matching of
   instances requiring SEV with SEV-capable compute hosts *and*
   indicate to nova's libvirt driver that SEV should be used when
   booting, the trait could be used solely for scheduling of the
   instance on SEV hosts, and an additional extra spec property such
   as ``hw:sev_policy`` could be used to ensure that the VM is defined
   and booted with the necessary extra SEV-specific domain XML.

   However this would create extra friction for the administrators
   defining SEV-enabled flavors, and it is also hard to imagine why
   anyone would want a flavor which requires instances to run on
   SEV-capable hosts without simultaneously taking advantage of those
   hosts' SEV capability.  Additionally, whilst this remains a simple
   Boolean toggle, using a single trait remains consistent with `a
   pre-existing upstream agreement on how to specify options that
   impact scheduling and configuration
   <http://lists.openstack.org/pipermail/openstack-dev/2018-October/135446.html>`_.

#. Rather than using a standard trait, a normal flavor extra spec
   could be used to require the SEV feature; however it is understood
   that `this approach is less preferable because traits provide
   consistent naming for CPU features in some virt drivers, and
   querying traits is efficient
   <https://docs.openstack.org/nova/latest/admin/configuration/schedulers.html#computecapabilitiesfilter>`_.

Data model impact
-----------------

A new trait will be used to denote SEV-capable compute hosts.

No new data objects or database schema changes will be required.

REST API impact
---------------

None, although future work may require extending the REST API so that
users can verify the hardware's attestation that the memory was
encrypted correctly by the firmware.  However if such an extension
would not be useful in other virt drivers across multiple CPU vendors,
it may be preferable to deliver this functionality via an independent
AMD-specific service.

Security impact
---------------

This change does not add or handle any secret information other than
of course data within the guest VM's encrypted memory.  The secrets
used to implement SEV are locked inside the AMD hardware.  The
hardware random number generator uses the CTR_DRBG construct from
`NIST SP 800-90A <https://en.wikipedia.org/wiki/NIST_SP_800-90A>`_
which has not been found to be susceptible to any back doors.  It uses
AES counter mode to generate the random numbers.

SEV protects data of a VM from attacks originating from outside the
VM, including the hypervisor and other VMs.  Attacks which trick the
hypervisor into reading pages from another VM will not work because
the data obtained will be encrypted with a key which is inaccessible
to the attacker and the hypervisor.  SEV protects data in caches by
tagging each cacheline with the owner of that data which prevents the
hypervisor and other VMs from reading the cached data.

SEV does not protect against side-channel attacks against the VM
itself or attacks on software running in the VM.  It is important to
keep the VM up to date with patches and properly configure the
software running on the VM.

This first proposed implementation provides some protection but is
notably missing the ability for the cloud user to verify the
attestation which SEV can provide using the ``LAUNCH_MEASURE``
firmware call.  Adding such attestation ability in the future would
mean that much less trust would need to be placed in the cloud
administrator because the VM would be encrypted and integrity
protected using keys the cloud user provides to the SEV firmware over
a protected channel.  The cloud user would then know with certainty
that they are running the proper image, that the memory is indeed
encrypted, and that they are running on an authentic AMD platform with
SEV hardware and not an impostor platform setup to steal their data.
The cloud user can verify all of this before providing additional
secrets to the VM, for example storage decryption keys.  This spec is
a proposed first step in the process of obtaining the full value that
SEV can offer to prevent the cloud administrator from being able to
access the data of the cloud users.

It is strongly recommended that `the OpenStack Security Group
<openstack-security@lists.openstack.org>`_ is kept in the loop and
given the opportunity to review each stage of work, to help ensure
that security is implemented appropriately.

Notifications impact
--------------------

It may be desirable to access the information that the instance is
running encrypted, e.g. a billing cloud provider might want to impose
a security surcharge, whereby encrypted instances are billed
differently to unencrypted ones.  However this should require no
immediate impact on notifications, since the instance payload in the
versioned notification has the flavor along with its extra specs,
where the SEV enablement trait would be defined.

In the case where the SEV trait is specified on the image backing the
server rather than on the flavor, the notification would just have the
image UUID in it.  The consumer could look up the image by UUID to
check for the presence of the SEV trait, although this does open up a
potential race window where image properties could change after the
instance was created.  This could be remedied by future work which
would include image properties in the instance launch notification, or
storing the image metadata in ``instance_extra`` as is currently done
for the flavor.

Other end user impact
---------------------

The end user will harness SEV through the existing mechanisms of
traits in flavor extra specs and image properties.  Later on it may
make sense to add support for scheduler hints (see the `Future Work`_
section below).

Performance Impact
------------------

No performance impact on nova is anticipated.

Preliminary testing indicates that the expected performance impact on
a VM of enabling SEV is moderate; a degradation of 1% to 6% has been
observed depending on the particular workload and test.  More details
can be seen in slides 4--6 of `AMD's presentation on SEV-ES at the
2017 Linux Security Summit
<http://events17.linuxfoundation.org/sites/events/files/slides/AMD%20SEV-ES.pdf>`_.

If compression is being used on swap disks then more storage may be
required because the memory of encrypted VMs will not compress to a
smaller size.

Memory deduplication mechanisms such as KSM (kernel samepage merging)
would be rendered ineffective.

Other deployer impact
---------------------

In order for users to be able to use SEV, the operator will need to
perform the following steps:

- Deploy SEV-capable hardware as nova compute hosts.

- Ensure that they have an appropriately configured software stack, so
  that the various layers are all SEV ready:

  - kernel >= 4.16
  - QEMU >= 2.12
  - libvirt >= 4.5
  - ovmf >= commit 75b7aa9528bd 2018-07-06

Finally, a cloud administrator will need to define SEV-enabled flavors
as described above, unless it is sufficient for users to define
SEV-enabled images.

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
  adam.spiers

Other contributors:
  Various developers from SUSE and AMD

Work Items
----------

It is expected that following sequence of extensions, or similar, will
need to be made to nova's libvirt driver:

#. Add detection of host SEV capabilities as detailed above.

#. Consume the new SEV detection code in order to provide the
   ``HW_CPU_AMD_SEV`` trait.

#. Add a new ``nova.virt.libvirt.LibvirtConfigGuestFeatureSEV`` class.

#. Extend ``nova.virt.libvirt.LibvirtDriver._set_features()`` to add
   the required XML to the VM's domain definition if the new trait is
   in the flavor of the VM being launched.

#. Since live migration between hosts is not (yet) supported for

   - SEV-encrypted instances, nor

   - `between unencrypted and SEV-encrypted states in either direction
     <https://github.com/qemu/qemu/commit/8fa4466d77b44f4f58f3836601f31ca5e401485d>`_,

   prevent nova from live-migrating any SEV-encrypted instance, or
   resizing onto a different compute host.  Alternatively, nova could
   catch the error raised by QEMU, which would be propagated via
   libvirt, and handle it appropriately.  We could build in
   higher-layer checks later if it becomes a major nuisance for
   operators.

#. Similarly, attempts to suspend / resume an SEV-encrypted domain are
   not yet supported, and therefore should either be prevented, or the
   error caught and handled.

#. (Stretch goal) Adopt one of the following suggested code changes
   for reducing or even eliminating usage on x86 architectures of the
   IDE bus for CD-ROM devices such as the config drive:

   #. Simply change `the hardcoded usage of an IDE bus for CD-ROMs on
      x86
      <https://github.com/openstack/nova/blob/396156eb13521a0e7af4488a8cd4693aa65a0da2/nova/virt/libvirt/blockinfo.py#L267>`_
      to ``scsi`` to be consistent with all other CPU architectures,
      since it appears that the use of ``ide`` only remains due to
      legacy x86 code and the fact that support for other CPU
      architectures was added later.  The ``hw_cdrom_bus=ide`` image
      property could override this on legacy images lacking SCSI
      support.

   #. Auto-detect the cases where the VM has no IDE controller, and
      automatically switch to ``scsi`` or ``virtio-scsi`` in those
      cases.

   #. Introduce a new ``nova.conf`` option for specifying the default
      bus to use for CD-ROMs.  Then for instance the default could be
      ``scsi`` (for consistency with other CPU architectures) or
      ``virtio-scsi``, with ``hw_cdrom_bus`` overriding this value
      where needed.  This is likely to be more future-proof as the use
      of very old machine types is gradually phased out, although the
      downside is a small risk of breaking legacy images.

      If there exist clouds where such legacy x86 images are common,
      the option could then be set to ``ide`` and
      ``hw_cdrom_bus=virtio-scsi`` overriding when newer machine types
      are required for SEV (or any other reason).  Although this is
      perhaps sufficiently unlikely as to make a new config option
      overkill.

Additionally documentation should be written, as detailed in the
`Documentation Impact`_ section below.

Future work
-----------

Looking beyond Stein, there is scope for several strands of additional
work for enriching nova's SEV support:

- Extend the `ComputeCapabilitiesFilter
  <https://docs.openstack.org/nova/rocky/admin/configuration/schedulers.html#computecapabilitiesfilter>`_
  scheduler filter to support scheduler hints, so that SEV can be
  chosen to be enabled per instance, eliminating the need for
  operators to configure SEV-specific flavors or images.

- If there is sufficient demand from users, make the SEV policy
  configurable via an extra spec or image property.

- Provide some mechanism by which users can access the attestation
  measurement provided by SEV's ``LAUNCH_MEASURE`` command, in order
  to verify that the guest memory was encrypted correctly by the
  firmware.  For example, nova's API could be extended; however if
  this cannot be done in a manner which applies across virt drivers /
  CPU vendors, then it may fall outside the scope of nova and require
  an alternative approach such as a separate AMD-only endpoint.


Dependencies
============

* Special hardware which supports SEV for development, testing, and CI.

* Recent versions of the hypervisor software stack which all support
  SEV, as detailed in `Other deployer impact`_ above.

* UEFI bugs will need to be addressed if not done so already:

  - `Bug #1607400 “UEFI not supported on SLES” : Bugs : OpenStack Compute (nova) <https://bugs.launchpad.net/nova/+bug/1607400>`_
  - `Bug #1785123 “UEFI NVRAM lost on cold migration or resize” : Bugs : OpenStack Compute (nova) <https://bugs.launchpad.net/nova/+bug/1785123>`_
  - `Bug #1633447 “nova stop/start or reboot --hard resets uefi nvram...” : Bugs : OpenStack Compute (nova) <https://bugs.launchpad.net/nova/+bug/1633447>`_


Testing
=======

The ``fakelibvirt`` test driver will need adaptation to emulate
SEV-capable hardware.

Corresponding unit/functional tests will need to be extended or added
to cover:

- detection of SEV-capable hardware and software, e.g. perhaps as an
  extension of
  ``nova.tests.functional.libvirt.test_report_cpu_traits.LibvirtReportTraitsTests``

- the use of a trait to include extra SEV-specific libvirt domain XML
  configuration, e.g. within
  ``nova.tests.unit.virt.libvirt.test_config``

There will likely be issues to address due to hard-coded assumptions
oriented towards Intel CPUs either in Nova code or its tests.

Tempest tests could also be included if SEV hardware is available, either
in the gate or via third-party CI.


Documentation Impact
====================

- A new entry should be added in `the Feature Support Matrix
  <https://docs.openstack.org/nova/latest/user/support-matrix.html>`_,
  which refers to the new trait and shows the current `limitations`_.

- The `KVM section of the Configuration Guide
  <https://docs.openstack.org/nova/rocky/admin/configuration/hypervisor-kvm.html>`_
  should be updated with details of how to set up SEV-capable
  hypervisors.  It would be prudent to mention the current
  `limitations`_ here too, including the impact on compute host
  maintenance, and the need to correctly calculate
  `reserved_host_memory_mb`_ based on the expected maximum number of
  SEV guests simultaneously running on the host.

Other non-nova documentation should be updated too:

- The `documentation for os-traits
  <https://docs.openstack.org/os-traits/latest/>`_ should be extended
  where appropriate.

- The `"Hardening the virtualization layers" section of the Security
  Guide
  <https://docs.openstack.org/security-guide/compute/hardening-the-virtualization-layers.html>`_
  would be an ideal location to describe the whole process of
  providing and consuming SEV functionality.

References
==========

- `AMD SEV landing page <https://developer.amd.com/sev>`_

- `AMD SEV-KM API Specification
  <https://developer.amd.com/wp-content/resources/55766.PDF>`_

- `AMD SEV github repository containing examples and tools
  <https://github.com/AMDESE/AMDSEV/>`_

- `Slides from the 2017 Linux Security Summit describing SEV and
  preliminary performance results
  <http://events17.linuxfoundation.org/sites/events/files/slides/AMD%20SEV-ES.pdf>`_

- `libvirt's SEV options <https://libvirt.org/formatdomain.html#sev>`_

History
=======

.. list-table:: Revisions
   :header-rows: 1

   * - Release Name
     - Description
   * - Stein
     - Introduced
