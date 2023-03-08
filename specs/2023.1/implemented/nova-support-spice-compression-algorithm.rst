..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

===========================================================
Add configuration options to set SPICE compression settings
===========================================================

https://blueprints.launchpad.net/nova/+spec/nova-support-spice-compression-algorithm

This spec proposes to add SPICE-related options to a Nova configuration.
These options can be used to enable and set the SPICE compression settings for
libvirt (QEMU/KVM) provisioned instances. Note that those options are only
taken into account if SPICE support is enabled (and the VNC support is
disabled).


Problem description
===================

Sometimes, network bandwidth is limited especially if physical network hardware
is involved in an OpenStack setup, e.g. if old network switches with limited
uplink bandwidth are used. Nevertheless, a data-intensive transfer of console
data between compute nodes and remote console clients should be possible in
such an infrastructure. Here it would be beneficial if builtin compression
settings could be activated for transport protocols (currently only SPICE) in
order to transmit graphic-intense desktop content in networks with limited
bandwidth while gaining an acceptable quality of experience (QoE).

Use Cases
---------

* An operator should be able to decide how to configure a desktop (console)
  transport via SPICE. In particular, he should be able to configure the SPICE
  compression algorithms and modes in order to

    - lower network bandwidth for graphical console accesses from (remote)
      networks with limited bandwidth. Users can benefit from such a
      configuration especially if they access a graphical console of an
      instance from home.
    - completely turn off default compression settings for local console
      accesses while keeping latency as low as possible within a local (wired)
      network. Such a configuration can be useful if users should only have
      local access to graphical instances for visualizing computation results.
    - select an appropriate SPICE video detection/streaming for graphic-intense
      use cases such as office work, media editing, and visualization of
      computation results, depending on the available network bandwidth and the
      QoE to be achieved.

* A user should be able to access the graphical console of an instance from
  Horizon's built-in spice-html5 client as before, even from (remote) networks
  with limited bandwidth (e.g. from home).


Proposed change
===============

This spec proposes to add configuration options for all transport protocols in
OpenStack that support the explicit activation of builtin compression settings.
Currently only the integrated SPICE protocol allows the activation of various
image [1]_ and video [2]_ compression settings to lower the network bandwidth
while improving data transmission for graphic-intense desktops. Since SPICE is
only supported by the libvirt hypervisor (through the QEMU backend), all other
hypervisors and transport protocols are not affected by this proposed change.
Libvirt already provides an automatic configuration of SPICE-related
compression settings for the QEMU backend (see the ``spice`` documentation in
the libvirt XML domain documentation [3]_). Therefore, the change only requires
to make the libvirt hypervisor driver capable to generate a valid libvirt XML
config with activated SPICE compression settings. The OpenStack configuration
for the config generation should be stored in the ``spice`` configuration group
of a Nova configuration. This configuration group should be extended with
configuration options that are capable of specifying the SPICE-related
compression settings (choose compression algorithms and toggle compression
modes on/off).

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

None.

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

The following SPICE-related options will be added to the ``spice``
configuration group of a Nova configuration:

* ``image_compression`` = [ ``auto_glz`` \| ``auto_lz`` \| ``quic`` \|
  ``glz`` \| ``lz`` \| ``off`` ];
* ``jpeg_compression`` = [ ``auto`` \| ``never`` \| ``always`` ];
* ``zlib_compression`` = [ ``auto`` \| ``never`` \| ``always`` ];
* ``playback_compression`` = [ ``True`` \| ``False`` ];
* ``streaming_mode`` = [ ``filter`` \| ``all`` \| ``off`` ];

Each configuration option is optional and can be set explictly to configure the
associated SPICE compression setting for libvirt. If all configuration options
are not set, then none of the SPICE compression settings will be configured for
libvirt, which corresponds to the behavior before this proposed change. In this
case, the built-in defaults from the libvirt backend (e.g. QEMU) are used.

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
  bahnwaerter

Other contributors:
  None

Feature Liaison
---------------

Feature liaison:
  None

Work Items
----------

* Add SPICE-related configuration options to the Nova configuration.
* Create documentation for the SPICE-related configuration options.
* Extend the SPICE config generation in the libvirt hypervisor driver.

Dependencies
============

None.


Testing
=======

* Implement unit tests for each function to cover testing of added and changed
  methods.


Documentation Impact
====================

* Extend the Nova configuration documentation and add documentation for the
  SPICE-related compression settings.


References
==========

.. [1] SPICE image compression:
       https://www.spice-space.org/spice-user-manual.html#_image_compression
.. [2] SPICE video compression:
       https://www.spice-space.org/spice-user-manual.html#_video_compression
.. [3] libvirt Domain XML format:
       https://libvirt.org/formatdomain.html#graphical-framebuffers


History
=======

.. list-table:: Revisions
   :header-rows: 1

   * - Release Name
     - Description
   * - 2023.1 Antelope
     - Introduced
