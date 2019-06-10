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
   provide a flavor containing an SEV-specific `extra
   spec resource requirement
   <https://docs.openstack.org/nova/latest/user/flavors.html#extra-specs-required-resources>`_
   which will allow users booting instances with that flavor to ensure
   that their instances run on an SEV-capable compute host with SEV
   encryption enabled.

#. As a cloud user, in order to not have to trust my cloud operator
   with my secrets, I want to be able to boot VM instances with SEV
   functionality enabled.


Proposed change
===============

For Train, the goal is a minimal but functional implementation which
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

- Implement a new ``MEM_ENCRYPTION_CONTEXT`` `resource class
  <https://specs.openstack.org/openstack/nova-specs/specs/mitaka/implemented/resource-classes.html>`_
  which represents the number of guests with secure encrypted memory
  which a compute host can run concurrently (due to a limited number
  of slots for encryption keys in the memory controller).  It will be
  zero for hosts which do not support SEV.

- Update the documentation for the ``HW_CPU_AMD_SEV`` trait in
  os-traits to indicate that a) it cannot be used yet, only in the
  future when SEV support is fully implemented, and b) even at that
  point it should not be used via ``trait:HW_CPU_AMD_SEV=required``,
  because the new resource class should be used instead.

  The trait has been present `since 0.11.0
  <https://docs.openstack.org/os-traits/latest/reference/index.html#amd-sev>`_,
  and `was added in the Stein cycle
  <https://review.openstack.org/635608>`_ on the basis of the design
  in `the previous version of this spec accepted for Stein
  <https://specs.openstack.org/openstack/nova-specs/specs/stein/approved/amd-sev-libvirt-support.html>`_.
  However since then we have realised that we need to track the SEV
  capability as a discretely quantifiable resource rather than as a
  binary feature, therefore the ``MEM_ENCRYPTION_CONTEXT`` resource
  class will supersede it as the low-level mechanism for indicating
  when an SEV context is required.

  It is regrettable to have to back-pedal on this element of the
  design; however nothing used the ``HW_CPU_AMD_SEV`` trait yet so it
  seems very unlikely that this would cause an issue for anyone.  It
  will not be removed for two reasons:

  #. The os-traits project has a policy of never removing any traits,
     based on the idea that an extensible-only set of traits is easier
     to manage than one which can be shrunk.  For example, a sync of
     the traits with the placement database will never need to worry
     about removing entries or corresponding foreign keys.

  #. It seems helpful to provide the trait anyway, even though it's
     not strictly required.  In fact `the code to do so
     <https://review.openstack.org/638680>`_ is already under review,
     so hardly any extra work would be required.

     One use case suggested was implementing anti-affinity of non-SEV
     guests with SEV hosts, thereby keeping SEV hosts as free as
     possible for SEV guests.  This could be achieved simply by
     placing ``trait:HW_CPU_AMD_SEV=forbidden`` on all non-SEV
     flavors, although a more sophisticated approach might take
     advantage of a future implementation of `a parallel proposal for
     forbidden aggregates <https://review.openstack.org/609960>`_.

     Another use case might be to allow operators and users to
     distinguish between multiple mechanisms for encrypting guest
     memory available from different vendors within a single cloud,
     e.g. if the compute plane contained a mix of machines supporting
     AMD SEV and Intel `MKTME`_.

     However, any implementations of those use cases are outside the
     scope of this spec.

- Make the libvirt driver `update the ProviderTree object
  <https://docs.openstack.org/nova/latest/reference/update-provider-tree.html>`_
  with the correct inventory for the new ``MEM_ENCRYPTION_CONTEXT``
  resource class.  For example `on EPYC machines the maximum number of
  SEV guests supported is expected to be 15
  <https://www.redhat.com/archives/libvir-list/2019-January/msg00652.html>`_.

  Since it is not currently possible to obtain this limit
  programmatically via libvirt, introduce a new config option in the
  ``[libvirt]`` section of ``nova.conf`` to set the size of this
  inventory for each SEV-capable compute host.  This would default to
  ``None`` with a forward-looking meaning of "auto-detect the
  inventory, or if this is not possible, don't impose any limit".
  This would have two benefits:

  #. Operators are not forced to make any configuration changes to
     take advantage of SEV out of the box.  Guest VMs may fail to
     launch if the host's real capacity is exceeded, but if that
     becomes a problem, operators can just set the value.

  #. No configuration changes are needed once auto-detection is
     introduced.  For example, if auto-detection obtains the same
     value as a manually configured limit, a warning could be emitted
     deprecating the configuration option, and if it obtained a
     different value, an error could be raised, or at least a warning
     that the auto-detected value would be used instead.

  See the `Limitations`_ section for more information on this.

- Change the libvirt driver to include extra XML in the guest's domain
  definition when ``resources:MEM_ENCRYPTION_CONTEXT=1`` is present in
  the flavor extra specs, in order to ensure the following:

  - SEV security is enabled via the ``<launchSecurity>`` element,
    as detailed in the `SEV launch-time configuration`_ section below.

  - The boot disk cannot be ``virtio-blk`` (due to a resource constraint
    w.r.t. bounce buffers).

  - The VM uses machine type ``q35`` and UEFI via OVMF.  (``q35`` is
    required in order to bind all the virtio devices to the PCIe
    bridge so that they use virtio 1.0 and *not* virtio 0.9, since
    QEMU's ``iommu_platform`` feature is added in virtio 1.0 only.)

    If SEV's requirement of a Q35 machine type cannot be satisfied by
    ``hw_machine_type`` specified by the image (if present), or the
    value specified by ``libvirt.hw_machine_type`` in ``nova.conf``
    (`which is not set by default
    <https://docs.openstack.org/nova/rocky/configuration/config.html#libvirt.hw_machine_type>`_),
    then an exception should be raised so that the build fails.

  - The ``iommu`` attribute is ``on`` for all virtio devices.  Despite
    the name, this does not require the guest or host to have an IOMMU
    device, but merely enables the virtio flag which indicates that
    virtualized DMA should be used.  This ties into the SEV code to
    handle memory encryption/decryption, and prevents IO buffers being
    shared between host and guest.

    The DMA will go through bounce buffers, so some overhead is expected
    compared to non-SEV guests.

    (Note: virtio-net device queues are not encrypted.)

  - The ``<locked/>`` element is present in the ``<memoryBacking>``
    section of the domain's XML, for reasons which are explained in
    the `Memory locking and accounting`_ section below.

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
        <memoryBacking>
          <locked/>
          ...
        </memoryBacking>
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

  For reference, `the AMDSEV GitHub repository
  <https://github.com/AMDESE/AMDSEV/>`_ provides `a complete example
  <https://github.com/AMDESE/AMDSEV/blob/master/xmls/sample.xml>`_ of a
  domain's XML definition with `libvirt's SEV options
  <https://libvirt.org/formatdomain.html#sev>`_ enabled.

- Add support for a new ``hw:mem_encryption`` parameter in flavor
  extra specs, and a new ``hw_mem_encryption`` image property.  When
  either of these is set to ``true``, it would be translated behind
  the scenes into ``resources:MEM_ENCRYPTION_CONTEXT=1`` which would
  be added to the flavor extra specs in the ``RequestSpec`` object.
  (This change to the flavor would only affect this launch context and
  not be persisted to the database.)

  Implementing this new parameter, which hides the implementation of
  the resource inventory and allocation behind an abstraction, has
  a few advantages:

  #. It makes it more user-friendly and oriented around the
     functionality provided.

  #. It allows us to change or extend the implementation later without
     changing the user interface, for example when adding support for
     similar functionality from other vendors.

  #. The translation from image property to extra spec allows us to
     provide a special exception to the deliberate design decision
     that image properties don't normally facilitate placing
     requirements on specific resource classes in the same way that
     `extra specs are allowed to
     <https://docs.openstack.org/nova/latest/user/flavors.html#extra-specs-required-resources>`_.

SEV launch-time configuration
-----------------------------

``cbitpos`` and ``reducedPhysBits`` are dependent on the processor
family, and can be obtained through the ``sev`` element from `the
domain capabilities
<https://libvirt.org/formatdomaincaps.html#elementsSEV>`_.

``policy`` allows a particular SEV policy, as documented in the `AMD
SEV-KM API Specification`_.  Initially the policy will be hardcoded and
not modifiable by cloud tenants or cloud operators. The policy will
be::

  #define SEV_POLICY_NORM \
      ((SEV_POLICY)(SEV_POLICY_NODBG|SEV_POLICY_NOKS| \
        SEV_POLICY_DOMAIN|SEV_POLICY_SEV))

which equates to ``0x0033``.  In the future, when support is added to
QEMU and libvirt, this will permit live migration to other machines in
the same cluster [#]_ (i.e. with the same OCA cert), but doesn't
permit other guests or the hypervisor to directly inspect memory.

A future spec could be submitted to make this policy configurable via
an extra spec or image property.

`SEV-ES <https://developer.amd.com/wp-content/resources/56421.pdf>`_
(Encrypted State, which `encrypts the guest register state to protect
it from the hypervisor
<https://events.linuxfoundation.org/wp-content/uploads/2017/12/Extending-Secure-Encrypted-Virtualization-with-SEV-ES-Thomas-Lendacky-AMD.pdf>`_)
is not yet ready, but may be added to this policy later.

.. [#] Even though live migration is not currently supported by the
       hypervisor software stack, it will be in the future.

Memory locking and accounting
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The presence of the ``<locked/>`` element in the ``<memoryBacking>``
section of the domain's XML will cause libvirt to pass ``-realtime
mlock=on`` to QEMU, which in turn `causes QEMU to set RLIMIT_MEMLOCK
to RLIM_INFINITY
<https://libvirt.org/git/?p=libvirt.git;a=blob;f=src/qemu/qemu_domain.c;h=ba3fff607a93533b9b47956cc2cfa70237e7c041;hb=HEAD#l10049>`_.

This is needed due to a chain of factors listed immediately below:

- Whilst ``-realtime mlock=on`` will `cause QEMU to invoke
  mlockall(2)
  <https://github.com/qemu/qemu/blob/dafd95053611aa14dda40266857608d12ddce658/os-posix.c#L356>`_,
  to prevent pages from swapping out, this is not sufficient to
  prevent the locked pages from migrating within physical memory,
  as explained in the "migrating mlocked pages" section of the
  `Unevictable LRU infrastructure kernel documentation
  <https://www.kernel.org/doc/Documentation/vm/unevictable-lru.txt>`_.

- Similarly, whilst the use of hugepages would pin pages to prevent
  them swapping out, it would not prevent them migrating.
  Additionally `hugepages would only allow pinning of guest RAM
  <https://review.openstack.org/#/c/641994/2/specs/train/approved/amd-sev-libvirt-support.rst@167>`_,
  not the other memory chunks required by QEMU.

  Having said that, hugepages may still be useful for accounting, as
  explained below.

- All the memory pages allocated by QEMU must be pinned (not just
  those allocated for guest RAM, but also video RAM, UEFI ROM /
  pflash, pc.rom, isa-bios, and ACPI tables), so that they cannot
  even be migrated around in physical memory, let alone swapped
  out.  This is because the SEV memory encryption engine uses a
  tweak such that two identical plaintext pages at a different
  locations will have different ciphertexts, so swapping or moving
  ciphertext of two pages will not result in the plaintext being
  swapped.  In typical page migration, the pgtable tables are
  updated and contents are copied from the source to the
  destination.  However in the SEV case, the contents copy phase
  will not provide correct results because the pages contains the
  encrypted data.

- Therefore in order to pin the allocated pages to prevent them
  migrating, QEMU's SEV implementation will issue special
  ``KVM_MEMORY_ENCRYPT_{REG,UNREG}_REGION`` ioctls as documented
  in `the kernel's KVM API documentation
  <https://www.kernel.org/doc/Documentation/virtual/kvm/api.txt>`_.

  These ioctls take memory regions and pin them using the kernel
  APIs which ensures that those ranges are excluded from the page
  move rcu list.  While pinning the pages, KVM checks
  ``RLIMIT_MEMLOCK`` to ensure that it does not blindly act upon
  the request and exceed that rlimit.  If the rlimit is not large
  enough then pinning the pages through this ioctl will fail.

- Initially it was planned to ensure that the rlimit was raised
  sufficiently high enough by setting a hard memory limit via
  ``<hard_limit>`` in the ``<memtune>`` section of the
  domain's XML.  However, `it was later pointed out
  <https://review.openstack.org/#/c/641994/2/specs/train/approved/amd-sev-libvirt-support.rst@167>`_
  that not only it is very hard to calculate a safe upper limit
  for the rlimit, and that using incorrect values will cause
  virtual machines to die, but also that this could be very
  wasteful because each guest would require the worst-case
  (highest) upper limit.

- Therefore a better approach was proposed where the rlimit for
  each guest is set to ``RLIM_INFINITY``, and host memory
  reservation is enacted at the ``/machine.slice`` top-level
  cgroup, with all VMs placed inside that.  The latter will
  protect the host OS from running out of memory due to VM
  overcommit.

This problem of correct memory accounting and safe memory locking is
not specific to SEV.  Granted, SEV's requirement to lock pages in
memory to prevent the use of swap does alter the nature of the
potential impact when oversubscription occurs, so that rather than
launching VMs and incurring heavy swapping, the VMs would fail to
launch in the first place.  In fact, arguably this "fail-fast"
approach is more desirable, since it is less likely to impact other
VMs which are already running.

One suggestion proposed for more correct memory accounting was to use
hugepages for SEV guests, which are not only beneficial for
performance but also allows reuse of nova's existing ability to track
hugepages per NUMA node and account for them in the resource tracker.
However it appears that `this would only allow accounting of guest RAM
<https://review.openstack.org/#/c/641994/2/specs/train/approved/amd-sev-libvirt-support.rst@167>`_,
not the other memory chunks required by QEMU.

Other options include `reserved_host_memory_mb`_, or even simply
leaving the OS distributions to take care of configuring the rlimit in
the ``/machine.slice`` cgroup in their virtualization stacks as
mentioned above.

.. _reserved_host_memory_mb:
   https://docs.openstack.org/nova/rocky/configuration/config.html#DEFAULT.reserved_host_memory_mb

However as long as operators are given clear guidance about how to
correctly mitigate these risks associated with memory reservation (as
detailed in the `Documentation Impact`_ section below), it is proposed
that obtaining a full solution should remain outside the scope of this
spec, and therefore not block it.

Note that this memory pinning is expected to be a temporary
requirement; the latest firmwares already support page copying (as
documented by the ``COPY`` API in the `AMD SEV-KM API
Specification`_), so when the OS starts supporting the page-move or
page-migration commmand then it will no longer be needed.  However we
still need to work with older firmware and kernel combinations.

Limitations
-----------

The following limitations may be removed in the future as the
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

- Operators will initially be required to manually specify the upper
  limit of SEV guests for each compute host, via the new configuration
  option proposed above.  This is a short-term workaround to the
  current lack of mechanism for programmatically discovering the SEV
  guest limit via libvirt.

  This configuration option temporarily reduces the SEV detection code
  proposed from essential into more of a safety check, defending
  against an operator accidentally setting the config value to
  non-zero on a non-SEV host.  However the detection code is `already
  close to complete <https://review.openstack.org/#/c/633855/>`_, and
  is also still worth having long-term, since it will allow us to
  remove the requirement for operators to manually specify the upper
  limit as soon as it becomes possible to obtain it programmatically.
  At the time of writing, `a patch to expose the SEV guest limit in
  QEMU <https://marc.info/?l=qemu-devel&m=155502702424182&w=2>`_ is
  under review, but will not be available until the 4.1.0 release at
  the earliest.  `A follow-up patch to libvirt is expected
  <https://review.openstack.org/#/c/641994/2/specs/train/approved/amd-sev-libvirt-support.rst@527>`_
  which will expose it via the ``<domainCapabilities>`` XML mentioned
  above.

  This config option could later be demoted to a fallback value for
  cases where the limit cannot be detected programmatically, or even
  removed altogether when nova's minimum QEMU version guarantees that
  it can always be detected.

  Deployment tools may decide to layer an additional config value set
  centrally, representing a default non-zero limit for hosts where SEV
  is automatically detected.  So for example if all your SEV-capable
  hosts were EPYC machines with the same maximum of 15 SEV guests, you
  could set that to 15 in one place and then rely on `the automatic
  SEV detection code already proposed
  <https://review.openstack.org/#/c/633855/>`_ to set the
  ``MEM_ENCRYPTION_CONTEXT`` inventory for that host to 15, without
  having to set it manually on each host.

- Failures at VM launch-time *may* occasionally occur in the initial
  implementation, for example if the ``q35`` machine type is
  unavailable (although this should be rare, since ``q35`` is nearly
  11 years old), or some other required virtual component such as UEFI
  is unavailable.  Future work may track availability of required
  components so that failure can occur earlier, at placement time.
  This potentially increases the chance of placement finding an
  alternative host which can provide all the required components, and
  thereby successfully booting the guest.

The following limitations are expected long-term:

- The number of SEV guests allowed to run concurrently will always be
  limited.  `On EPYC machines it will be limited to 15 guests.
  <https://www.redhat.com/archives/libvir-list/2019-January/msg00652.html>`_

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

  #. Set the (largely `undocumented
     <https://bugs.launchpad.net/glance/+bug/1808868>`_)
     ``hw_cdrom_bus`` image property to ``virtio``, which is
     recommended as a replacement for ``ide``, and ``hw_scsi_model``
     to ``virtio-scsi``.

  Some potentially cleaner long-term solutions which require code
  changes are suggested as a stretch goal in the `Work Items`_ section
  below.

For the sake of eliminating any doubt, the following actions are *not*
expected to be limited when SEV encryption is used:

- Cold migration or shelve, since they power off the VM before the
  operation at which point there is no encrypted memory (although this
  could change since there is work underway to add support for `PMEM
  <https://pmem.io/>`_)

- Snapshot, since it only snapshots the disk

- Evacuate, since this is only initiated when the VM is assumed to be
  dead or there is a good reason to kill it

- Attaching any volumes, as long as they do not require attaching via
  an IDE bus

- Use of spice / VNC / serial / RDP consoles

- `VM guest virtual NUMA (a.k.a. vNUMA)
  <https://www.suse.com/documentation/sles-12/singlehtml/article_vt_best_practices/article_vt_best_practices.html#sec.vt.best.perf.numa.vmguest>`_

Alternatives
------------

It has been suggested to name the resource class in a vendor-specific
way, for example ``AMD_SEV_CONTEXT``.  This would avoid hard-coding
any assumptions that similar functionality from Intel (e.g. `MKTME`_)
and other vendors in the future would be subject to the same limit on
the number of guests with encrypted memory which can run concurrently.
However this raises other challenges; for example in a cloud with
mixed compute hardware from AMD and Intel both providing secure
encrypted guest memory functionality, extra specs are currently
incapable of expressing a requirement for *either* AMD SEV hardware
*or* Intel MKTME hardware.  Therefore there would be no way to
translate the vendor-agnostic ``hw:mem_encryption=true`` extra spec
parameter or ``hw_mem_encryption`` image property into an extra spec
parameter which would achieve the desired effect.

Some fundamentally different `approaches to SEV were originally
proposed
<https://specs.openstack.org/openstack/nova-specs/specs/stein/approved/amd-sev-libvirt-support.html#alternatives>`_
in the previous version of this spec accepted for Stein.  However
since then a significant amount of code has been both merged and
submitted for review implementing the main proposed change above, not
to mention considerable hours of discussion refining this approach.

Therefore it seems very unlikely that any of those alternatives will
be used, especially considering the move from a trait-oriented design
to one oriented around a new resource class; therefore they are
omitted here.

Data model impact
-----------------

A new resource class will be used to inventory slots for SEV guests on
SEV-capable compute hosts.

A new configuration option will be used (at least in the short term)
to specify the maximum number of SEV guests runnable on each compute
host.

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
where the ``MEM_ENCRYPTION_CONTEXT`` resource would be defined.

In the case where the SEV resource is specified on the image backing
the server rather than on the flavor, the notification would just have
the image UUID in it.  The consumer could look up the image by UUID to
check for the presence of the ``MEM_ENCRYPTION_CONTEXT`` resource,
although this does open up a potential race window where image
properties could change after the instance was created.  This could be
remedied by future work which would include image properties in the
instance launch notification, or storing the image metadata in
``instance_extra`` as is currently done for the flavor.  Alternatively
it may be sufficient to check for the translation to
``resources:MEM_ENCRYPTION_CONTEXT=1`` in the extra specs.

Other end user impact
---------------------

The end user will harness SEV through the existing mechanisms of
resources in flavor extra specs and image properties.  Later on it may
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

#. Add a new configuration option in the ``[libvirt]`` section of
   ``nova.conf`` to set the maximum number of SEV guests allowed
   per SEV compute host.

#. Add a new ``MEM_ENCRYPTION_CONTEXT`` resource class representing
   the discrete number of slots available on each SEV compute host.

#. Make the libvirt driver `update the ProviderTree object
   <https://docs.openstack.org/nova/latest/reference/update-provider-tree.html>`_
   with the correct inventory for the new ``MEM_ENCRYPTION_CONTEXT`` resource
   class.  For now, set this value using the new configuration option
   introduced above.  It should also take into account the results of
   the SEV detection code.

#. Update the documentation for the ``HW_CPU_AMD_SEV`` trait in
   os-traits.

#. Add a new ``nova.virt.libvirt.LibvirtConfigGuestSEVLaunchSecurity`` class
   to describe the ``<launchSecurity/>`` element.

#. Extend ``nova.virt.libvirt.LibvirtDriver`` to add the required XML
   to the VM's domain definition if ``MEM_ENCRYPTION_CONTEXT=1`` is in
   the ``allocations`` dictionary passed to the libvirt driver's
   ``spawn()`` method, *and* the host is SEV-capable.

#. Determine whether hugepages should be used, and if so, whether they
   can help with accounting.

#. Add support for a new ``hw:mem_encryption`` parameter in flavor
   extra specs, and a new ``hw_mem_encryption`` image property as
   described above.  Most likely these can be implemented via a new
   request filter in ``request_filter.py``.

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
      ``virtio``, with ``hw_cdrom_bus`` overriding this value where
      needed.  This is likely to be more future-proof as the use of
      very old machine types is gradually phased out, although the
      downside is a small risk of breaking legacy images.

      If there exist clouds where such legacy x86 images are common,
      the option could then be set to ``ide`` and
      ``hw_cdrom_bus=virtio`` overriding when newer machine types are
      required for SEV (or any other reason).  Although this is
      perhaps sufficiently unlikely as to make a new config option
      overkill.

Additionally documentation should be written, as detailed in the
`Documentation Impact`_ section below.

Future work
-----------

Looking beyond Train, there is scope for several strands of additional
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
  `limitations`_ here too, including the impact on config drive
  configuration, compute host maintenance, the need to correctly
  calculate `reserved_host_memory_mb`_ based on the expected maximum
  number of SEV guests simultaneously running on the host, and the
  details provided above (such as memory region sizes) which cover how
  to calculate it correctly.

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

- `MKTME <https://en.wikichip.org/wiki/x86/tme#Multi-Key_Total_Memory_Encryption>`_
  - Intel's Multi-Key Total Memory Encryption


History
=======

.. list-table:: Revisions
   :header-rows: 1

   * - Release Name
     - Description
   * - Train
     - Re-approved
   * - Stein
     - Introduced
