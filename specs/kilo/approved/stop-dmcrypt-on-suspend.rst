..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

====================================================================
Stop dm-crypt device when an encrypted instance is suspended/stopped
====================================================================

https://blueprints.launchpad.net/nova/+spec/stop-dmcrypt-on-suspend

Disconnect the dm-crypt device from encrypted LVM volume when an
instance with encrypted LVM ephemeral storage is suspended or powered off.


Problem description
===================

The recently introduced LVM ephemeral storage encryption features secures
user data at rest.  Current implementation makes user data unreadable after
the instance has been terminated.  While the instance is active (e.g.,
running, paused, suspended or powered off), on the compute host the data is
readable only by the super-user.  This protection against unauthorized
access can be strengthened further by disconnecting the dm-crypt device when
an instance is suspended or powered off and flushing the encryption key from
memory.  The dm-crypt device is what allows the encrypted data to be
accessed in the clear so disconnecting it will render the data unreadable by
anyone without the key.

Use Cases
---------

An encrypted instance operating on sensitive data is stopped but not destroyed
-- the work to be resumed later.

Project Priority
----------------

None


Proposed change
===============

The change will add code to stop the dm-crypt device and flush the key in
libvirt.driver.power_off() and libvirt.driver.suspend() and code to retrieve
instance ephemeral encryption key and restart the dm-crypt device in
libvirt.driver.power_on() and libvirt.driver.resume().

Alternatives
------------

There is no real alternative.

Data model impact
-----------------

None

REST API impact
---------------

None

Security impact
---------------

User data will be inaccessible to anyone while the instance is powered off or
suspended.

Notifications impact
--------------------

None

Other end user impact
---------------------

None

Performance Impact
------------------

The power on and resume operations will be marginally slower for encrypted
instances.

Other deployer impact
---------------------

None

Developer impact
----------------

None


Implementation
==============

Assignee(s)
-----------

Primary assignee:
  dgenin (Dan Genin)

Work Items
----------

* Add dm-crypt stop/restart functionality to suspend()/resume().
* Add dm-crypt stop/restart functionality to power_off()/power_on().


Dependencies
============

None


Testing
=======

Unit and Tempest tests will be written to verify correct operation of
the proposed feature.


Documentation Impact
====================

The extension of data-at-rest security to powered off and suspended instances
should be mentioned in OpenStack Security Guide.


References
==========

None
