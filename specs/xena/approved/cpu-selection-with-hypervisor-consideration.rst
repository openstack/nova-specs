..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

=================================================
Guest CPU selection with hypervisor consideration
=================================================

https://blueprints.launchpad.net/nova/+spec/cpu-selection-with-hypervisor-consideration

Make Nova's guest CPU selection approach more effective and reliable by
introducing two new QEMU- and libvirt-based CPU configuration APIs:
``baselineHypervisorCPU()`` and ``compareHypervisorCPU()``.  These new
APIs are more "hypervisor-literate" compared to the existing libvirt
APIs that Nova uses.  As in, the new APIs take into account what the
"host hypervisor" (meaning: KVM, QEMU, and what libvirt knows about the
host) is capable of.

Taking advantage of these newer APIs will allow Nova to make more
well-informed decisions when determining CPU models that are compatible
across different hosts.

Problem description
===================

The current guest CPU config libvirt APIs that Nova uses,
``compareCPU()`` and ``baselineCPU()``, are "not very useful" (quoting
the cover letter [1]_ of the libvirt patch series that introduced the
newer APIs), because they don't consider the capabilities of the "host
hypervisor" (KVM, QEMU and details libvirt knows about the host).  More
concretely, with the existing APIs, ``compareCPU()`` and
``baselineCPU()``, there is no way to ask if a given CPU model plus CPU
flags combination is supported by KVM and a specific QEMU binary on the
host.

For example, today operators have to be careful about how they configure
the libvirt driver with regard to `cpu_model` and
`cpu_model_extra_flags`, because the wrong combination (e.g. an invalid
CPU flag that is not supported by the host hypervisor) can lead to an
instance failing to spawn.  I.e. operators have to manually validate the
extra CPU flags they're supplying to Nova are actually supported by the
given compute host.

This spec will allow Nova [2]_ to do fine-grained validation of a given
CPU model plus CPU flags against a specific QEMU binary (and KVM) to
allow well-informed guest CPU configuration decisions.  And taking
advantage of the said two new libvirt APIs will also allow computing a
more accurate baseline guest CPU that permits live migration across
several compute nodes.  And provides a clearer picture of what CPU
features are required to get mitigations from Meltdown and Spectre.

Use Cases
---------

By taking advantage of the two CPU configuration APIs,
``baselineHypervisorCPU()`` and ``compareHypervisorCPU()``, Nova will
now be able to make meaningful decisions when determining guest CPU
models and their features:

- While determining guest CPU models, Nova can take into account
  several other aspects, e.g. the type of virtualization (pure
  emulation vs. hardware-accelerated), QEMU binary's capabilities,
  guest machine type, and CPU architcture to construct a
  better-informed guest CPU.

- Nova will be able to do more fine-grained validation of CPU models and
  flags, i.e. answer questions like: "Is the combination of Intel's
  ``IvyBridge`` CPU model plus the CPU flags ``pcid`` and ``ssbd``
  supported by the host hypervisor?"

- Armed with the above two points, Nova will also be positioned to
  better report more accurate CPU traits.  (I.e. improve the
  ``_get_cpu_traits()`` method.)

- Operators can get a more accurate view on what guest CPU models and
  features their guests can realistically expect.

Proposed change
===============

Make Nova's CPU selection strategy more effective by taking advantage of
the two new libvirt APIs: ``baselineHypervisorCPU()`` and
``compareHypervisorCPU()`` [3]_.  These APIs provide more useful ways to
determine compatible models among CPU variants, and elimiates bugs in
the older CPU config libvirt APIs along the way.

With this change, the libvirt driver will automatically validate if a
certain combination of CPU model + flags can work on a given compute
host — e.g. Nova will now be able to answer: "Is this combination of
'IvyBridge' plus CPU flags 'pcid' & 'pdpe1gb' supported by KVM, QEMU and
libvirt on the host?".  And, if the given combination of CPU model plus
flags are invalid, the ``nova-compute`` service will refuse to start,
with an actionable log message.

This will let the operator set the CPU model plus flags, and let Nova
handle the validation.

A quick description of the two APIs:

``baselineHypervisorCPU()``
  Purpose: This API computes the most feature-rich "baseline" CPU (which
  includes CPU model plus additional features) that is (a) compatible with
  all given host CPUs (as described in an XML document), so that one can
  live migrate across the said hosts; and (b) is supported by the host
  hypervisor.  It is a more useful version of the older ``baselinCPU()``,
  which does not consider any hypervisor capabilities when computing the
  baseline CPU.

  A comparison of ``baselineCPU()`` and ``baselineHypervisorCPU()`` APIs,
  in terms of what parameters they take into account:

  .. code-block:: text

      +-----------+--------------------+-----------------------------+
      |           | baselineCPU()      | baselineHypervisorCPU()     |
      +-----------+--------------------+-----------------------------+
      |           | XML document       | XML document describing     |
      |           | describing one     | one or more host CPUs       |
      |           | or more host CPUs  |                             |
      |           +--------------------+-----------------------------+
      |           |                    | path to the QEMU binary     |
      |           |                    +-----------------------------+
      |Parameters |                    | the type of virtualization  |
      |           |                    | (e.g. KVM, QEMU)            |
      |           |                    +-----------------------------+
      |           |                    | guest machine type          |
      |           |                    +-----------------------------+
      |           |                    | CPU architecture            |
      +-----------+--------------------+-----------------------------+

``compareHypervisorCPU()``
  Purpose: This API compares a given CPU description with the CPU
  capabilities the host hypervisor is able to provide.  It is a more
  useful version of the existing ``compareCPU()``, which compares the CPU
  definition with the host CPU without considering any specific hypervisor
  and its abilities.

  A comparison of ``compareCPU()`` and ``compareHypervisorCPU()`` APIs, in
  terms of what parameters they take into account:

  .. code-block:: text

      +-----------+--------------------+-----------------------------+
      |           | compareCPU()       | compareHypervisorCPU()      |
      +-----------+--------------------+-----------------------------+
      |           | XML describing the | XML describing the CPU      |
      |           | CPU to be compared | to be compared              |
      |           +--------------------+-----------------------------+
      |           |                    | path to the QEMU binary     |
      |           |                    +-----------------------------+
      |Parameters |                    | the type of virtualization  |
      |           |                    | (e.g. KVM, QEMU)            |
      |           |                    +-----------------------------+
      |           |                    | guest machine type          |
      |           |                    +-----------------------------+
      |           |                    | CPU architecture            |
      +-----------+--------------------+-----------------------------+

By making Nova use the above two APIs, it can now do more advanced
validation of CPU model plus flags compatibility, which ensures an
instance cannot be launched with CPU features that don't exist in the
host CPU.

Alternatives
------------

We could just "stay put" and keep chugging along with the existing older
libvirt APIs, ``baselineCPU()`` and ``compareCPU()``.

But that would be doing a disservice to our users, as we have more
reliable APIs that provide a more well-informed guest CPU configuration.

Data model impact
-----------------

None.

REST API impact
---------------

None.

Security impact
---------------

This implicitly improves security -- as in, with these new APIs, you
should be able to get a better sense of what CPU features are required
to get mitigations from Meltdown and Spectre.

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

The following libvirt and QEMU versions:

- For ``x86_64``: QEMU >= 2.9, libvirt >= 4.4.0

- For ``s390x``: QEMU >= 2.9, libvirt work is actively in progress
  upstream [4]_)

Developer impact
----------------

None.

Upgrade impact
--------------

For ``x86_64``, users should have the minimum-required verisons of
libvirt and QEMU to be 4.4.0 and 2.9, respectively.


Implementation
==============

Assignee(s)
-----------

Primary assignee:
  <kashyapc>, <chengsheng>

Work Items
----------

- Introduce a Nova wrapper method, baseline_hypervisor_cpu(), for
  libvirt's baselineHypervisorCPU() API.

- Introduce a Nova wrapper method, compare_hypervisor_cpu(), for
  libvirt's compareHypervisorCPU() API.

- Rework the _get_guest_cpu_model_config() method in the libvirt
  driver to take advantage of the fine-grained validation of CPU model
  plus features (against a given QEMU binary), if available on the given
  compute host.

- Rewrite the _compare_cpu() method's the logic in the libvirt driver to
  take advantage of compareHypervisorCPU().  (While at it, rename it to
  _compare_hypervisor_cpu().

- Update the check_can_live_migrate_destination() method in the libvirt
  driver to use the newer wrapper API.

- Update the get_capabilities() method in nova/virt/libvirt/host.py to
  take advantage of baseline_hypervisor_cpu(), if available on the given
  compute host.

- This can be done separately, but noting for completeness' sake: Update
  _get_cpu_traits() method to use baselineHypervisorCPU().  (Support for
  s390x shouldn't be a blocker to get started on this.)

Dependencies
============

This is not a strict dependency, but as noted earlier, support for s390x
for libvirt's compareHypervisorCPU() and baselineHypervisorCPU() is
still in progress upstream.

Testing
=======

- Introduce "fake libvirt" methods for baselineHypervisorCPU() and
  compareHypervisorCPU() APIs with minimum-required functionanlity
  (because duplicating libvirt's logic is complicated and doesn't add
  much value to replicate it).

- Unit tests.

- Potentially a couple of functional tests.

Documentation Impact
====================

Consider adding a section in the Nova admin guide on how the newer APIs
allow more reliable guest CPU configuration.  Also note explicitly that
we recommend to stick to ``host-model``, which is the the default CPU
mode for the libvirt driver.

References
==========

.. [1] "New CPU related APIs"
       -- https://www.redhat.com/archives/libvir-list/2018-May/msg01204.html

.. [2] "[RFE] Fine-grained API to validate if a given CPU model and flags
       are supported by QEMU / KVM"
       -- https://bugzilla.redhat.com/show_bug.cgi?id=1559832

.. [3] Refer to slide-28 here:
       https://kashyapc.fedorapeople.org/Effective-Virtual-CPU-Configuration-in-Nova-Berlin2018.pdf

.. [4] libvirt work for s390x:
       https://www.redhat.com/archives/libvir-list/2019-January/msg00310.html

History
=======

.. list-table:: Revisions
   :header-rows: 1

   * - Release Name
     - Description
   * - Train
     - Introduced
   * - Xena
     - Re-proposed
