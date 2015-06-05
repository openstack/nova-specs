..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

===================================================
Use the os-brick library for libvirt volume drivers
===================================================

https://blueprints.launchpad.net/nova/+spec/use-os-brick-library

Introduce the usage of the os-brick library into Nova.  The library
will be used inside the libvirt volume drivers for volume discovery
and removal for all of the supported protocols.  os-brick will also
be used to collect the initiator information, which is the connector
object, passed to Cinder during for volume attaches.


Problem description
===================

For several OpenStack releases now, there has been duplicate code
between Cinder and Nova with respect to volume discovery and removal.
Since the Havana release, Cinder has been incubating an embedded
library called 'brick'.   The brick library's purpose was to collect
initiator information, discover volumes being attached to a host and to
remove volumes already attached.  This is essentially the purpose of
Nova's libvirt volume drivers.

Cinder has offically removed the embedded brick library and has switched
to using the pypi os-brick library at the start of the Liberty release.

This spec lays out the removal of the duplicate code in Nova's
libvirt volume drivers that exists in the os-brick library.


Use Cases
----------

The main use case for using the os-brick library is when Nova needs to attach
or detach a volume.  The primary work flow is this, Nova collects the initiator
information into a connector object, which gets passed to Cinder to export the
volume.  Cinder passes back the target information and Nova uses that target
information to discover the volume showing up.  Instead of using the embedded
code in Nova to collect the initiator information, and discover the target
volume showing up, Nova will use the os-brick library to do that work.  The
os-brick library will also be used for volume removal when a Nova needs to
detach a volume.


Project Priority
-----------------

None

Proposed change
===============

First os-brick needs to be a new requirement for Nova.   Then rework the
libvirt volume drivers to remove their internal code for volume discovery
and removal, and replace the code with calls to os-brick Connector objects.
Finally, replace the Nova virt/utils code that collects the initiator
information that gets passed to Cinder at volume attach time.


Alternatives
------------

Nova can continue to have duplicate code that does the same work as os-brick.
This is less than desirable as fixing bugs and adding new features needs to
be done in Nova as well as os-brick.

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

None

Performance Impact
------------------

None

Other deployer impact
---------------------

os-brick will be a required pypi library for Nova.

Developer impact
----------------

One of the positive benefits of using this external library is that the Nova
team won't have to maintain the internals of os-brick's code for volume
discovery and removal. os-brick is owned by the Cinder team and any bug
fixes and new features added will benefit Nova.


Implementation
==============

Assignee(s)
-----------

Who is leading the writing of the code? Or is this a blueprint where you're
throwing it out there to see who picks it up?

If more than one person is working on the implementation, please designate the
primary author and contact.

Primary assignee:
  walter-boring

Work Items
----------

* Convert Nova's code to use os-brick for collecting the initiator information
  into the connector object.

* Convert each of the supported libvirt volume drivers to use os-brick
  Connector objects.

* Rework the libvirt volume driver unit tests.


Dependencies
============

Import the os-brick library as a requirement for Nova.

Testing
=======

To test this out correctly, we have to change the unit tests in Nova that
look at the internals of volume discovery for iSCSI, FC, etc to test out
the os-brick library APIs.   Ensure that each of the os-brick Connector
objects are loaded correctly for each of the support transports.

We will rely on the os-brick unit tests and releases for volume discovery
and removal to work properly, so there is no need to test all of the
internals for how iSCSI volume attaches work.

Documentation Impact
====================

We are simply moving the existing functionality of volume discovery
and removal from Nova's embedded libvirt volume drivers to use os-brick.
So, there is no doc impact.

References
==========

* Cinder's adoption of os-brick:
  https://review.openstack.org/#/c/155552/

* https://github.com/openstack/os-brick

* https://pypi.python.org/pypi/os-brick

History
=======

Back in the Havana time frame we discussed the idea of creating a shared
library for doing volume discovery and removal as well as local volume
management for Nova and Cinder.   The os-brick library is the first step
in that direction that solves the volume discover and removal shared code.


.. list-table:: Revisions
   :header-rows: 1

   * - Release Name
     - Description
   * - Liberty
     - Introduced
