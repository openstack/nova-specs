..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

==========================================
Intel TDX support for libvirt driver
==========================================

https://blueprints.launchpad.net/nova/+spec/intel-tdx-libvirt-support

This spec proposes the required changes to extend nova's libvirt driver to be
able to launch Intel Trust Domain Extensions (TDX) encrypted virtual machines.
TDX provides hardware-enforced isolation for virtual machines, protecting guest
memory and CPU state from the hypervisor and other privileged software, similar
to AMD's SEV-SNP technology but for Intel processors.

Problem description
===================

Intel Trust Domain Extensions (TDX) is a confidential computing technology
that provides hardware-based isolation for virtual machines. Currently,
OpenStack Nova supports AMD SEV and SEV-ES for confidential VMs, but lacks
support for Intel's equivalent technology. This limits users with Intel
hardware from leveraging confidential computing capabilities in OpenStack.

TDX creates Trust Domains (TDs) which are hardware-isolated VMs with encrypted
memory and CPU state, protected from the Virtual Machine Monitor (VMM),
hypervisor, and other non-TD software. While confidential computing has
growing applications in edge and IoT environments, this is particularly
important for cloud environments where tenants need strong guarantees about
data confidentiality and integrity from software-based attacks. OpenStack Nova
primarily serves multi-tenant cloud infrastructure where the separation of
responsibilities between cloud operators and tenants makes confidential
computing especially valuable.

Use Cases
---------

- As a cloud user with sensitive workloads, I want to be able to launch VMs
  with confidential computing enabled to ensure my data and applications are
  protected from unauthorized access by the hypervisor or other tenants.

- As a cloud operator running Intel 5th Generation Xeon Scalable
  Processors (Emerald Rapids) or later, I want to offer
  TDX-based confidential computing as a service to my tenants.

- As a cloud user in a regulated industry, I want to use TDX to reduce the
  trust I need to place in the cloud provider's software stack while still
  benefiting from cloud infrastructure, understanding that physical security
  remains the responsibility of the cloud provider.

Proposed change
===============

This spec proposes extending the existing memory encryption support in Nova's
libvirt driver to support Intel TDX, building on the existing SEV/SEV-ES
implementation. It leverages the generalization introduced by
``generalize-sev-code`` blueprint and the functionality of
``libvirt-firmware-auto-selection``.

The required changes for other confidential computing implementations, like AMD
SEV-SNP and ARM CCA, will likely be similar to these since they share
similarities with Intel TDX.

1. **Detection of TDX host capabilities**:

Extend the libvirt driver to detect support for Intel TDX on the host through
libvirt host and dom capabilities, as well as kernel kvm parameters. This is
very similar to current capabilities checks for AMD SEV/SEV-ES.

- Libvirt dom capabilities:

.. code-block:: xml

  <domainCapabilities>
    ...
    <features>
      ...
      <tdx supported='yes'/>
    </features>
  </domainCapabilities>


- kvm_intel parameter (should be set to Y):
  ``/sys/module/kvm_intel/parameters/tdx``

TDX requires ``libvirt.cpu_mode`` to be host-passthrough. This will be checked
along with the above and disable TDX if it is not configured, logged
accordingly.

2. **Add TDX to Intel OS traits**:

Introduce ``HW_CPU_X86_INTEL_TDX`` trait to the os-traits library for
scheduling TDX-capable instances to appropriate hosts, following the pattern of
existing ``HW_CPU_X86_AMD_SEV`` and ``HW_CPU_X86_AMD_SEV_ES`` traits.

3. **Resource tracking**:

Intel TDX needs a hardware key (TDX key) per TDX enabled VM. The maximum number
is configured in BIOS and dependent on hardware. To track this, a new child
resource provider for TDX is introduced. This will be parallel to the existing
SEV and SEV-ES ones but will be called TDX RP with
``traits:HW_CPU_X86_INTEL_TDX`` and ``resources:MEM_ENCRYPTION_CONTEXT``. ::

    +------------+     +--------------------------------+
    | compute RP +--+--+ SEV RP                         |
    +------------+  |  | trait:HW_CPU_X86_AMD_SEV       |
                    |  +----------------------------+---+
                    |  | MEM_ENCRYPTION_CONTEXT     | N |
                    |  +----------------------------+---+
                    |
                    |  +--------------------------------+
                    +--+ TDX RP                         |
                       | trait:HW_CPU_X86_INTEL_TDX     |
                       +----------------------------+---+
                       | MEM_ENCRYPTION_CONTEXT     | N |
                       +----------------------------+---+

For AMD SEV the maximum number of possible guests is extracted from Libvirt dom
capabilities. TDX does not have an entry there and instead utilizes the
``misc`` cgroup controller in the kernel. This can be read directly and without
elevated privileges.

- ``/sys/fs/cgroup/misc.capacity`` — the total number of TDX KeyIDs
  (Trust Domain keys) available on the host, set at boot time from the
  TDX module and BIOS configuration. Example content::

      tdx 63

The ``total`` in the resource provider then corresponds to ``misc.capacity``.
It excludes the key used by TDX module and thus that number directly
corresponds to the maximum number of TDX enabled VMs.

4. **Image and flavor**:

Use the existing ``hw:mem_encryption=True`` flavor extra spec and
``hw_mem_encryption=true`` image property, and introduce
``hw:mem_encryption_model=intel-tdx`` to specify TDX encryption, following the
pattern used for SEV (``amd-sev``, ``amd-sev-es``).

Internally these properties will be translated into
``resources:MEM_ENCRYPTION_CONTEXT=1`` and
``trait:HW_CPU_X86_INTEL_TDX=required``. Conflicting requests between flavor
and image will be rejected.

The current implementation defaults to ``trait:HW_CPU_X86_AMD_SEV=required`` if
no ``hw:mem_encryption_model`` is configured but ``hw:mem_encryption=True`` is.
This could potentially be a problem if only Intel TDX is the supported memory
encryption technology in the deployment (and thus no AMD SEV). The simple
solution is to document that ``hw:mem_encryption_model`` needs to be set to use
Intel TDX. This spec will not change anything regarding the default logic.

5. **XML generation**:

Extend the libvirt driver to support the generation of the launch security
object needed for TDX (LibvirtConfigGuestTDXLaunchSecurity). This is similar to
SEV/SEV-ES, although it includes other options. Outtake from Libvirt
documentation:

.. code-block:: xml

  <launchSecurity type='tdx'>
       <policy>0x10000001</policy>
       <mrConfigId>xxx</mrConfigId>
       <mrOwner>xxx</mrOwner>
       <mrOwnerConfig>xxx</mrOwnerConfig>
       <quoteGenerationSocket path="/var/run/tdx-qgs/qgs.socket"/>
  </launchSecurity>

The current implementation of SEV/SEV-ES does not expose any configuration of
the options. Therefore, for an initial implementation of TDX the following is
proposed:

- Hardcode policy to ``0x10000000``, which disables debugging, but keeps
  SEPT_VE_DISABLE. This is the default policy with debugging disabled.
- quoteGenerationSocket is optional, but needed for attestation. By default (if
  path is omitted) it will include the default socket path:
  ``/var/run/tdx-qgs/qgs.socket``. This default should not conflict with other
  sockets and will integrate directly with the Quote Generation Service (QGS)
  for attestation.
- Remaining fields are meant for user configuration and will be left as
  default (empty).

The resulting launchSecurity:

.. code-block:: xml

  <launchSecurity type='tdx'>
       <policy>0x10000000</policy>
       <quoteGenerationSocket/>
  </launchSecurity>

The firmware will be selected automatically following the changes in
``libvirt-firmware-auto-selection``. Thus, no additional XML needs to be
generated to specify TDX firmware.

6. **Verify flavor/image**:

Introduce MemEncryptionConfigTdx (based on MemEncryptionConfig) to verify
instance flavor and image configuration. Intel TDX requires machine_type q35
and UEFI firmware, this aligns with existing checks for SEV. Stateless firmware
is also required, which is configured on the image with
``hw_firmware_stateless=True``.

Using an SCSI boot drive is not supported as TDX firmware does not include the
necessary drivers. This applies to both legacy SCSI and virtio-scsi, therefore
the instance should be rejected if any of the following fields are configured:

- ``hw_disk_bus=scsi``
- ``hw_scsi_model=virtio-scsi``, this can be expanded to ensure that it is not
  set at all since all values will imply SCSI, currently there is only one
  value though.

Block device mappings configuration with ``hw_disk_bus=scsi`` also needs to be
rejected. Only needed if the block device is intended to be booted from.

TDX also does not support suspend. Live-migration support is ongoing, but not
yet there. A reject function like ``reject_sev_instances`` will therefore be
needed to reject these operations.

Alternatives
------------

The generalization of the SEV implementation makes the approach for TDX clear,
but below are some alternative approaches for when TDX differs from the current
implementation of SEV.

1. **Detection of TDX host capabilities**:

TDX also exposes values in MSR that indicates if it is enabled on the host, it
essentially just reports what is configured in BIOS. Using MSR requires
elevated privileges and is thus not preferred. Kernel logs also contains some
information.

The minimum required Libvirt, QEMU and kernel versions could also be included
in these capabilities checks. However, these are implicitly checked already
with the other checks and potentially can be misleading due to backporting and
for example the Canonical TDX preview for Ubuntu 24.04. Where this becomes
necessary is when Nova starts using functionality which these checks don't
cover. This is not yet the case in this spec.

3. **Resource tracking**:

Another file is also exposed to track the current number of TDX keys in use.

- ``/sys/fs/cgroup/misc.current`` — the number of TDX KeyIDs currently
  allocated across all processes and VMs on the host, maintained in
  real time by the kernel. Example content::

      tdx 3

This will not be leveraged since Nova will handle the tracking.

4. **Image and flavor**:

This spec could also address the problem with the default by making it
configurable or providing a generic trigger so that Nova is able to identify
the most fitting ``hw:mem_encryption_model``. These solutions make it better
for the users, but ideally there would be no default since the different
technologies imply vastly different integrity and confidentiality. AMD SEV
would for instance not satisfy a lot of what Intel TDX or AMD SEV-SNP brings.
This is thus considered out of scope for this spec since Intel TDX with proper
documentation should work correctly without changing the default logic.

5. **XML generation**:

Several different approaches were considered for the configuration of the
launchSecurity object:

- Expose policy as a host configuration. This field is a concern for the end
  user, and it complicates attestations if different hosts have different
  policies.
- Other value for the default policy. For example enable bit 63 for performance
  monitoring.
- Expose quoteGenerationSocket path as a host config (nova.conf). This would
  allow operators to define the socket path per host. This is only needed to
  support fine-grain control of the setup and there is little value added by
  having this be configurable on the host, more value is added by a user
  defined configuration.
- Expose quoteGenerationSocket path as user configuration via the API. This
  would match the implementation in Libvirt. An end-user could want to decide
  which Quote Generation Service to use and thus select the associated path.
- Expose policy, mrConfigId, mrOwner and mrOwnerConfig as user configuration
  via the API. Ideally something like this is needed, but it also introduces a
  lot of unwanted complexity, especially since Nova currently exposes a
  confidential computing agnostic api. Intel TDX is also functional without
  user configuration of these fields.
- A generic interface for all user provided configuration with all confidential
  computing implementations. Deemed out of scope. Once support for AMD SEV-SNP
  and ARM CCA is in a generic interface can be made.
- Wait for generic interface. Hold all of Intel TDX support until a generic
  interface for user provided options for confidential computing is implemented
  in Nova. TDX will function without the user provided data and getting partial
  TDX support is considered better than none.

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

Users that want to use Intel TDX will need to:

Ensure their images support UEFI boot and are configured with
``hw_firmware_type=uefi`` (image property) or use flavors with
``hw:firmware_type=uefi`` (flavor extra spec).

Ensure images use Q35 machine type (``hw_machine_type=q35`` image property) or
use flavors with ``hw:machine_type=q35`` (flavor extra spec), or rely on
host-configured defaults via ``libvirt.hw_machine_type`` in nova.conf.

Ensure the guest OS includes TDX support.

Set appropriate image properties or flavor extra specs to request TDX.

There are some limitations with using Intel TDX. Reboot and live migration is
as of now not supported. Libvirt fakes reboots with a shutdown and power on
sequence for Intel TDX. Many of the limitations with AMD SEV are also present
in Intel TDX:

https://docs.openstack.org/nova/latest/admin/sev.html#limitations

Notable differences:

* memlocked is not required for TDX

Other limitations:

* Hugepages (hw:mem_page_size) support is ongoing but not merged, see patches:

https://lore.kernel.org/kvm/20260106101646.24809-1-yan.y.zhao@intel.com/

hugepages will not prevent the VM from booting. Larger pages (2MB or 1GB) will
be demoted to the standard page size.

* host cpu type (host-passthrough) is required.

.. note::

  host-passthrough can be more limiting for live-migration, as described at
  https://docs.openstack.org/nova/latest/admin/cpu-models.html#host-passthrough.
  These limitations still apply to Intel TDX, but since live-migration is not
  supported it is not yet a concern. Non-TDX instances on a TDX node will,
  however, have these limitations since host-passthrough is a node-wide
  configuration and a prerequisite for Intel TDX.

* The firmware (TDVF) for TDX purposefully excludes some drivers. This includes
  the SCSI driver and thus SCSI storage types cannot be used for the boot
  device. See patch:

https://github.com/tianocore/edk2/commit/c3f4f5a949a9e94bafe081c24dbd4110834b11ea

* VNC consoles are not supported. Configuring VNC will not stop the VM from
  starting, but the console will be effectively unusable due to TDX.

Performance Impact
------------------

- Additional host capabilities check.

- Intel TDX impacts memory performance (3-5%) when enabled. This is expected
  for confidential computing.

Other deployer impact
---------------------

Operators deploying Intel TDX support will need to:

- **Deploy TDX-capable hardware**:

Intel 5th Gen Xeon Scalable Processors or later with TDX support enabled in
BIOS.

- **Install required software stack**:

   - Linux kernel >= 6.16 with TDX host support
   - QEMU >= 10.1
   - libvirt >= 11.6.0
   - TDX module firmware

These requirements can be fulfilled with Ubuntu 25.10 and later

.. note::

  Ubuntu 24.04 can be used with a tech preview from Canonical. The versions of
  QEMU, Libvirt and kernel are significantly older than that of the above
  requirements, but patched to include TDX support.

  More info at:
  https://github.com/canonical/tdx

- **Quote Generation Service (QGS)**

For attestation the Quote Generation Service needs to run on the host. This is
distributed by Intel, but has to be setup by the operator.

The platform also needs to be registered with Intel.

Attestation is not required, although it is arguably what makes confidential
computing useful. TDX VMs will still boot with memory encryption without these
services but cannot be verified.

- **Configure Nova**:

   - Set ``libvirt.hw_machine_type`` to ``x86_64=q35``.
   - Ensure ``libvirt.virt_type`` is set to ``kvm``.
   - Set ``libvirt.cpu_mode`` to ``host-passthrough``.

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
  antia3 (Anton Iacobaeus)

Other contributors:
  None

Feature Liaison
---------------

Liaison Needed

Work Items
----------

- Add Intel TDX to host capabilities
- Add OS trait for TDX (os-traits)
- Add TDX to mem_encryption image and flavor
- Add XML generation for TDX launchSecurity
- Add TDX key slot resource tracking
- Add constraint checks for TDX flavors/images

All work items will also include unit testing.

Dependencies
============

- **libvirt-firmware-auto-selection**

(blueprint in progress for 2026.1): Required for automatic TDVF firmware
selection. TDX implementation should use this infrastructure rather than manual
firmware configuration.

- **generalize-sev-code**:

(blueprint in progress for 2026.1): Required to provide generalized
abstractions for memory encryption support. This spec uses the structure
provided by this blueprint.

- **Libvirt >= 11.6.0**:

Required for TDX support in domain capabilities and XML generation.

- **QEMU >= 10.1**:

Required for TDX guest support.

- **Linux Kernel/KVM >= 6.16**:

Required for TDX module support in the host.

- **os-traits library**:

Needs update to add ``HW_CPU_X86_INTEL_TDX`` trait.

- **Hardware**:

Development, testing, and CI requires Intel TDX capable hardware.

Testing
=======

The fakelibvirt test driver will need to be extended with Intel TDX
capabilities.

Unit testing covers the individual functionality of:

- Host capabilities
- XML generation
- image/flavor constraints
- Resource tracking for TDX key slots

Tempest and integration tests will require Intel TDX hardware, if made
available through third-party CI.

Documentation Impact
====================

**Admin Documentation** (docs.openstack.org/nova/latest/admin/):

- New section on Intel TDX setup and configuration (similar to existing AMD
  SEV section at admin/sev.html)
- Hardware requirements and BIOS configuration steps
- Software stack requirements (kernel, QEMU, libvirt, TDX module)
- Configuration options for nova.conf
- Limitations and known issues

Intel TDX enabling guide covers a lot of this already and can be referenced.

**User Documentation** (docs.openstack.org/nova/latest/user/):

- How to request TDX instances via flavors or image properties
- Guest OS requirements for TDX
- default configuration options of launchSecurity object
- Limitations on operations (live migration, suspend, and so on)
- Functional limitations (VNC console, huge-pages, and so on)
- How to verify that TDX is active (on guest)
- Basic attestation example

Intel TDX enabling guide also covers parts of this.

**API Documentation**:

- Update existing flavor extra specs and image properties documentation to
  include ``intel-tdx`` as a valid value for ``hw_mem_encryption_model``
- Update os-trait documentation to include ``HW_CPU_X86_INTEL_TDX``

References
==========

* Intel TDX Overview:
  https://www.intel.com/content/www/us/en/developer/tools/trust-domain-extensions/overview.html

* Intel TDX Documentation:
  https://www.intel.com/content/www/us/en/developer/tools/trust-domain-extensions/documentation.html

* Intel TDX Enabling Guide:
  https://cc-enabling.trustedservices.intel.com/intel-tdx-enabling-guide/01/introduction/

* Linux Kernel TDX Documentation:
  https://docs.kernel.org/arch/x86/tdx.html

* QEMU TDX Documentation:
  https://www.qemu.org/docs/master/system/i386/tdx.html

* Libvirt TDX patches (v4):
  https://www.mail-archive.com/devel@lists.libvirt.org/msg11385.html

* Blueprint: generalize-sev-code:
  https://blueprints.launchpad.net/nova/+spec/generalize-sev-code

* Blueprint: libvirt-firmware-auto-selection:
  https://blueprints.launchpad.net/nova/+spec/libvirt-firmware-auto-selection

* Mailing list discussion:
  https://lists.openstack.org/archives/list/openstack-discuss@lists.openstack.org/thread/263HB7Q3J6IBE7TIFXHQRWFEPVS42D5T/

* Canonical TDX repository (example configurations):
  https://github.com/canonical/tdx

History
=======

.. list-table:: Revisions
   :header-rows: 1

   * - Release Name
     - Description
   * - 2026.2 Hibiscus
     - Introduced
