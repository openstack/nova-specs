..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

=======================================================
Set ipxe url as image metadata instead of config option
=======================================================

https://blueprints.launchpad.net/nova/+spec/xenapi-set-ipxe-url-as-img-metadata

Move xenapi_ipxe_boot_menu_url to a image property so that it is user
configurable.

Problem description
===================

Currently the xenapi iPXE URL is specified as a configuration option in Nova.
Because it is a configuration option, users are unable to specify their own
iPXE URL on their own images.  The proposal is to allow the iPXE URL to be
specified as an image property.  By doing this, a customer can upload an iPXE
ISO, with the iPXE URL specified as a metadata option and boot from their own
custom configurations.

Proposed change
===============

Add the ability to specify ipxe_boot_menu_url as an image metadata property
which can override the nova configuration of xenapi_ipxe_boot_menu_url.

Alternatives
------------

Remove the main configuration option of xenapi_ipxe_boot_menu_url and rely on
the image property to populate the configuration.

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

Users will need to specify the ipxe_boot_menu_url in order to boot from their
iPXE configuration.

Performance Impact
------------------

None

Other deployer impact
---------------------

Because the settings set on the image properties would override the Nova
configuration settings, an operator could prevent users from overriding the
ipxe settings by setting policies to restrict usage of the various flags like
ipxe_boot and ipxe_boot_menu_url.

Developer impact
----------------

None

Implementation
==============

Assignee(s)
-----------

Primary assignee:
  antonym

Work Items
----------

* Create ipxe_boot_menu_url image metadata configuration to be used when
  generating iPXE ISO image.

Dependencies
============

None

Testing
=======

Testing of this feature will be covered by the XenServer CI.

Documentation Impact
====================

Change documentation to reflect that ipxe_boot_menu_url can now be specified as
an image property which will override the default configuration.

References
==========

* Original iPXE implementation:
  https://blueprints.launchpad.net/nova/+spec/xenapi-ipxe-iso-boot-support
