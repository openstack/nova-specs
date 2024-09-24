..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

=======================================================================
libvirt driver launching instances with memory encryption by AMD SEV-ES
=======================================================================

https://blueprints.launchpad.net/nova/+spec/amd-sev-es-libvirt-support

This spec proposes work required in order to extend the existing libvirt driver
feature to launch AMD SEV-encrypted instances, to support also using AMD
SEV-ES, which is the extended version of AMD SEV, as memory encryption
mechanism.

Problem description
===================

Current libvirt driver supports launching instances with memory encryption by
`AMD's SEV (Secure Encrypted Virtualization) technology
<https://developer.amd.com/sev/>`_. However the current implementation supports
only AMD SEV, and does not support new versions. For exmaple SEV-ES also
encrypts all CPU register contents when a VM stops running, to achieve more
complete protection of VM data, but users can't leverage these features because
of this limitation.

.. note::
   At the time or writing AMD already released CPUs which supports SEV-SNP, but
   the required hypervisor features to use SEV-SNP are not yet merged into
   the underlying components(kernel, QEMU, libvirt and ovmf). So in this spec
   we focus on SEV-ES. We attempt to keep the proposal as much compatible with
   SEV-SNP as possible, based on the implementations published by AMD.

Use Cases
---------

#. As a cloud administrator, in order that my users can have more confidence
   in the security of their running instances, I want to provide an image with
   the specific properties or a flavor with the specific extra specs which will
   allow users to boot instances to ensure that their instances run on
   an SEV-ES-capable compute host with SEV-ES encryption, instead of SEV
   encryption, enabled.

#. As a cloud user, in order to reduce data leakage risks further, I want to
   be able to boot VM instances with SEV-ES functionality, instead of SEV
   functionality, enabled.

Proposed change
===============

We propose extending the existing implementation to support launching instances
with SEV functionality.

- Add detection of host SEV-ES capabilities, which checks the following items.

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

    Also the ``maxESGuests`` field should be present and its value should be
    a positive (non-zero) value.

  - ``/sys/module/kvm_amd/parameters/sev_es`` should have the value ``Y``
    to indicate that the kernel has SEV capabilities enabled.  This
    should be readable by any user (i.e. even non-root).

  - Check QEMU version to determine whether the available QEMU binary supports
    SEV-ES.

- Add the new ``HW_CPU_AMD_SEV_ES`` trait to os-traits.

- Make the libvirt driver `update the ProviderTree object
  <https://docs.openstack.org/nova/latest/reference/update-provider-tree.html>`_
  with the correct inventory for the ``MEM_ENCRYPTION_CONTEXT`` resource class
  for both SEV and SEV-ES. To represent the slots dedicated for SEV and SEV-ES,
  nested resource providers are created per-model::

    +------------+     +----------------------------+
    | compute RP +--+--+ SEV RP                     |
    +------------+  |  | trait:HW_CPU_AMD_SEV       |
                    |  +------------------------+---+
                    |  | MEM_ENCRYPTION_CONTEXT | N |
                    |  +------------------------+---+
                    |
                    |  +----------------------------+
                    +--+ SEV-ES RP                  |
                       | trait:HW_CPU_AMD_SEV_ES    |
                       +------------------------+---+
                       | MEM_ENCRYPTION_CONTEXT | N |
                       +------------------------+---+

  The SEV RP is named ``<nodename>_amd_sev`` and the SEV-ES RP is named
  ``<nodename>_amd_sev_es``, so that the RP names are unique in the cluster.

  .. note::
     SEV and SEV-ES have separate limits of guest numbers, because ASIDs are
     allocated for ES guests and non-ES guests exclusively, from the total
     ASIDs available. Minimum ASID for SEV (non-ES) guests, which is
     effectively same as maxumum ASID for ES guests, should be configured in
     BIOS (or UEFI) to use SEV-ES. A new validation to detect insufficient
     ASIDs may be implemented.

  .. note::
     SEV-SNP uses the same ASID pool for ES by default when cyphertext hiding
     is not requested, and the new trait (such as HW_CPU_AMD_SEV_SNP) may be
     added to the existing SEV-ES RP when SEV-SNP support is added with
     a separate SEV-SNP RP with the trait corrsponding to the cyphertext hiding
     feature::

        +------------+     +----------------------------+
        | compute RP +--+--+ SEV RP                     |
        +------------+  |  | trait:HW_CPU_AMD_SEV       |
                        |  +------------------------+---+
                        |  | MEM_ENCRYPTION_CONTEXT | N |
                        |  +------------------------+---+
                        |
                        |  +----------------------------+
                        +--+ SEV-ES RP                  |
                        |  | trait:HW_CPU_AMD_SEV_ES    |
                        |  | trait:HW_CPU_AMD_SEV_SNP   |
                        |  +------------------------+---+
                        |  | MEM_ENCRYPTION_CONTEXT | N |
                        |  +------------------------+---+
                        |
                        |  +-----------------------------+
                        +--+ SEV-SNP RP                  |
                           | trait:HW_CPU_AMD_SEV_SNP_CH |
                           +------------------------+----+
                           | MEM_ENCRYPTION_CONTEXT | N  |
                           +------------------------+----+

     Note that SEV-SNP support is out of the current scope and this design
     needs further dicsussion when the support is actually implemented. It is
     described here to explain the potential plan to extend the RP structure
     in the future.

- Add support for a new ``hw:mem_encryption_model`` parameter in flavor
  extra specs, and a new ``hw_mem_encryption_model`` image property. When
  either of these is set to ``amd-sev-es`` along with the parameter/propery to
  enable memory encryption, it would be internally translated to
  ``resources:MEM_ENCRYPTION_CONTEXT=1`` and
  ``trait:HW_CPU_AMD_SEV_ES=required`` which would be added to the flavor extra
  specs in the ``RequestSpec`` object. If these new model parameter/property is
  absent or set to ``amd-sev`` then it would be translated to
  ``resources:MEM_ENCRYPTION_CONTEXT=1`` and
  ``trait:HW_CPU_AMD_SEV=required``. If conflicting models are requested by
  the instance flavor and the instance image (for example the flavor has
  ``hw:mem_encryption_model=amd-sev`` but the image has
  ``hw_mem_encryption_model=amd-sev-es``) then the request is rejected. Also
  the request should be rejected when memory encryption is not requested but
  a memory encryption model is requested.

- Change the libvirt driver to include extra XML in the guest's domain
  definition when the ``hw:mem_encryption_model`` parameter in flavor extra
  spec or the ``hw_mem_encryption_model`` image property is present and
  is set to ``amd-sev-es``. The extra XML is mostly similar to the one used in
  SEV, but its guest policy field needs the SEV-ES bit (bit 2) enabled.

.. note::
   Guest attestation is currently out of our scope. Because `the existing
   feature for guest attestation <https://libvirt.org/kbase/launch_security_sev.html#guest-attestation-for-sev-sev-es-from-a-trusted-host>`_
   heavily depends on hypervisor features and is not suitable for confidential
   computing use case where users do not trust hypervisors. We aim to implement
   the guest attestation feature once SEV-SNP is generally available, because
   SEV-SNP provides a better mechanism for guest attestation, using the special
   device presented to guest machines to obtain attestation reports.

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

The end user will harness SEV-ES through the existing mechanisms of resources
in flavor extra specs and image properties.

Also `the limitations of AMD SEV-encrypted guest
<https://docs.openstack.org/nova/latest/admin/sev.html#impermanent-limitations>`_
are applied when SEV-ES is used.

Performance Impact
------------------

No performance impact on nova is anticipated.

Performance impact for the other parts are same as the existing SEV support
feature.

Other deployer impact
---------------------

In order for users to be able to use SEV-ES, the operator will need to
perform the following steps:

- Deploy SEV-ES-capable hardware as nova compute hosts.

  - AMD EPYC 7xx2 (Rome) or later

- Set minimum ASID for SEV (non-ES) guests in BIOS (or UEFI) to a value greater
  than 0.

  .. note::
     If SEV-enabled instancs are already launched in the compute node, enough
     ASIDs should be reserved for SEV.

- Ensure that they have an appropriately configured software stack, so
  that the various layers are all SEV-ES ready:

  - kernel >= 4.16
  - QEMU >= 6.0.0
  - libvirt >= 8.0.0
  - ovmf >= commit 7f0b28415cb4 2020-08-12

  .. note::
     SEV-ES enabled guests can be launched by libvirt >= 4.5, but detection of
     maximum number of SEV-ES guests via domain capability API requires libvirt
     >= 8.0.0 .

A cloud administrator will need to define SEV-ES-enabled flavors as described
above, unless it is sufficient for users to define SEV-ES-enabled images.

The `[libvirt] num_memory_encrypted_guests` option is effective only for SEV,
but a new option for SEV-ES is NOT added. Instead, the detection capability in
libvirt is required to use SEV-ES. The `num_memory_encrypted_guests` option
will be deprecated to reduce complexity.

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
  kajinamit (irc: tkajinam)

Other contributors:
  None

Work Items
----------

#. Add the new ``HW_CPU_AMD_SEV_ES`` trait for os-traits

#. Add detection of host SEV-ES capabilities as detailed above and reshaping
   of existing MEMO_ENCRYPTION_CONTEXT resource.

#. Add ``mem_encryption_model`` property to ImageMeta object

#. Update scheduler util to request ``MEM_ENCRYPTION_CONTEXT`` resource and
   ``HW_CPU_AMD_SEV_ES`` trait when the ``mem_encryption_model`` property or
   the equivalent flavor extra spec is set to ``amd-sev-es``

#. Update libvirt driver to set the SEV-ES policy bit when the property is
   present.

#. Update image property schema in glance to validate the new
   ``mem_encryption_model`` property.

#. Update documentations.

Unit tests and functional tests should be added according to new logic.

Future work
-----------

None


Dependencies
============

* Special hardware which supports SEV-ES for development, testing, and CI.

* Recent versions of the hypervisor software stack which all support
  SEV-ES, as detailed in `Other deployer impact`_ above.


Testing
=======

The ``fakelibvirt`` test driver will need adaptation to emulate
SEV-ES-capable hardware.

Corresponding unit/functional tests will need to be extended or added
to cover:

- detection of SEV-ES-capable hardware and software, e.g. perhaps as an
  extension of
  ``nova.tests.functional.libvirt.test_report_cpu_traits.LibvirtReportTraitsTests``

- the use of a trait to include extra SEV-specific libvirt domain XML
  configuration, e.g. within
  ``nova.tests.unit.virt.libvirt.test_config``


Documentation Impact
====================

- Update the entry in `the Feature Support Matrix
  <https://docs.openstack.org/nova/latest/user/support-matrix.html>`_,
  to explain now AMD SEV-ES is supported in addition to AMD SEV.

- Update the existing `AMD SEV
  <https://docs.openstack.org/nova/latest/admin/sev.html>`_ guide to include
  information about SEV-ES.

Other non-nova documentation should be updated too:

- The `documentation for os-traits
  <https://docs.openstack.org/os-traits/latest/>`_ should be extended
  where appropriate.


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
   * - 2024.2 Dalmatian
     - Approved
   * - 2025.1 Epoxy
     - Re-proposed
