..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

=========================================================
libvit driver launching instances with stateless firmware
=========================================================

Since v8.6.0, libvirt allows launching instance with stateless firmware, which
disables the potential attack surface from hypervisor. This work aims to
introduce the required feature to allow users to use this feature.


Problem description
===================

Libvirt v8.6.0 introduced the new feature to launch instance with stateless
firmware. When an instance is launched with this feature enabled along with
UEFI, the instance uses a ready-only firmware image without NVRAM file. This
feature is useful for confidential computing use case, because it prevents
injection into firmware vars from hypervisor. It also allows more complete
measurement of elements involved in the boot chain of the instance which is
the key requirement of remote attestation. This is described in
`the libvirt guide <https://libvirt.org/kbase/launch_security_sev.html>`_.

However this libvirt feature can't be enabled in instances launched by current
nova, because nova does not set the stateless option. Also nova always injects
nvram file into libvirt domain XML.

Use Cases
---------

#. As a cloud administrator, in order that my users can have more confidence in
   the security of their running instances, I want to allow my users to
   enforce stateless firmware for their instances.

#. As a user, I want to prevent risk caused by firmware variables injected by
   hypevisor, for instances which load very confidential data.


Proposed change
===============

We propose adding a new image property to request stateless firmwre, so that
users can create their instance with stateless firmware.

- Add the new ``COMPUTE_SECURITY_STATELESS_FIRMWARE`` trait to os-traits.

- Make libvirt driver check the current version of libvirt and report
  the ``supports_stateless_firmware`` capability when the version is equal or
  newer than v8.6.0. This capability should be mapped to
  the ``COMPUTE_SECURITY_STATELESS_FIRMWARE`` trait.

- Add the new ``hw_firmware_stateless`` image property, which accept boolean
  values and is ``false`` by default. If the property is set to ``true`` then
  nova translate it to requiring the ``COMPUTE_SECURITY_STATELESS_FIRMWARE``
  trait.

- Change the libvirt driver to adds the ``stateless`` option to the ``loader``
  element of libvirt domain XML and skip injecting nvram file, if instance
  metadata of the instance contains ``hw_firmware_stateless`` property set to
  ``true``.

Alternatives
------------

None

Data model impact
-----------------

A new trait and new image property will be used to present availability and
request of stateless firmware feature in libvirt.

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

The end user will be able to use statless firmware for their instances through
the existing image property mechanism.

Performance Impact
------------------

None

Other deployer impact
---------------------

In order for users to be able to use this feature, the operator will need to
deploy libvirt v8.6.0 or later in the deployment.

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

#. Add the new ``COMPUTE_SECURITY_STATELESS_FIRMWARE`` trait to os-traits.

#. Make libvirt driver check libvirt version and present availability of
   stateless firmware in compute node capabilities, as
   the ``COMPUTE_SECURITY_STATELESS_FIRMWARE`` trait, based on the detected
   version.

#. Add the new ``hw_firmware_stateless`` image property to the ImageMeta
   object

#. Update scheduler util to require ``COMPUTE_SECURITY_STATELESS_FIRMWARE``
   trait when the ``hw_firmware_stateless`` property in instance image
   properties is set to ``true``

#. Make libvirt driver set ``stateless="yes"`` in the loder element when
   instance image properties contains the ``hw_firmware_stateless``
   property set to ``true``.

#. Update documentations

#. Update image property schema in glance to validate
   the new ``hw_firmware_stateless`` property.

Unit tests and functional tests should be added according to new logic.

Future work
-----------

None


Dependencies
============

Libvirt v8.6.0 or later.


Testing
=======

The ``fakelibvirt`` test driver will need adaptation to emulate libvirt older
than v8.6.0 and libvirt v8.6.0 or later.

Corresponding unit/functional tests will need to be extended or added
to cover:

- detection of the statless firmware support by libvirt

- the use of a trait to include extra stateless loader option in domain XML
  configuration.


Documentation Impact
====================

- Update `the Feature Support Matrix
  <https://docs.openstack.org/nova/latest/user/support-matrix.html>`_, to
  include stateless firmware support.

- Update the existing `AMD SEV
  <https://docs.openstack.org/nova/latest/admin/sev.html>`_ guide to include
  information about stateless firmware.


References
==========

- `libvirt's Domain XML format
  <https://libvirt.org/formatdomain.html#bios-bootloader>`_

- `libvirt's SEV options <https://libvirt.org/formatdomain.html#sev>`_


History
=======

.. list-table:: Revisions
   :header-rows: 1

   * - Release Name
     - Description
   * - 2024.2 Dalmatian
     - Introduced
