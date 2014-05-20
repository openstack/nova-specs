..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

==================================
Libvirt-lxc User Namespace Support
==================================

https://blueprints.launchpad.net/nova/+spec/libvirt-lxc-user-namespaces

User namespaces provide a way for a process running in a container to appear to
be running as root, but are in fact running as a different user on the host.
The objective of this feature is to allow deployers to enable and configure
which users and groups are mapped between container and host.

Problem description
===================

It is a security risk to allow user processes to run as root on container
hosts. In order to mitigate this risk, it is a good idea to run processes in
those containers as non-root users. The problem with this is some processes
may like to run (or at least appear to run as root inside the container).
For example, running an init system as the init process of the container.

Further, to boot an image in a user namespaced environment, the contents of
it's filesystem must be owned by the target user for root on the host.

Proposed change
===============

User namespaces allow processes inside a container to appear to be run as root,
but are in fact running as another user. Libvirt exposes this feature through
idmaps. This change would introduce a set of elements on the instance's domain
xml to indicate which user and group ids should map between container and host.

To address the owning of the filesystem by the targeted root user, the image
will be chowned by Nova at boot time.

Config for this feature will be disabled by default. It will be up to the
deployer to enable and configure it.

New config options in libvirt group:

* uid_maps: comma separated list of mappings, maximum of 5

* gid_maps: comma separated list of mappings, maximum of 5

Format for mappings is "guest-id:host-id:count,guest-id:host-id_count,..."

Alternatives
------------

Alternative image chown points, with performance impact:

* Chown by image creator: No performance impact

  * Rejected as the end user shouldn't have to worry about it

* Chown by Glance on import: Image will take longer to become active

  * Not ideal is it introduces a dependency on import being configured properly
    in glance.


* Chown by Nova when cached: Initial boot on all hosts will take longer

  * Rejected initially as there are too many changes going on around image
    caching. Once activity around iamge caching slows down, this may be the
    ideal option.


Data model impact
-----------------

None

REST API impact
---------------

None

Security impact
---------------

This change will improve the security of containers in Nova significantly.
Before this change, processes running in containers built by Nova will be run
as the host's root user. After this change, a deployer can restrict which
user(s) processes will be run as.

It should be noted that this change is not meant to provide isolation between
guests, but instead isolation between host and guest. It is out of the scope
of this change, but is reasonable to assume that if a mechanism was created
to ensure that containers all used different UID/GIDs, user namespacing could
be used to provide further guest-guest separation. This change provides a base
that could be extended in the future for that use case.

Notifications impact
--------------------

None

Other end user impact
---------------------

Images need to be deliberately created to be run in a user namespaced
environment. The contents of an image's filesystem need to be owned by the
target uid/gid. In this iteration of this feature, Nova will chown the
image on boot.

Performance Impact
------------------

Due to the chowning of the image's filesystem on boot by Nova, there will
be a performance hit on boot depending on how many files are on the image's
filesystem.


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
  andrew-melton

Other contributors:
  rconradharris
  thomas-maddox

Work Items
----------

* Modify libvirt config.py to include new idmap xml

* Create util function to chown rootfs

* Actual setup of new instance

Dependencies
============

* Linux 3.8+ kernel

  * Early 3.8 kernels may be buggy. If user needs minimum kernel, user
    should use latest 3.8 kernel possible.


* Libvirt 1.1.1

Testing
=======

Making sure that the nova config options are properly mapped to libvirt domain
objects can easily be handled by unit testing. Functional testing for this will
not be possible until libvirt-lxc is included in the CI environment. Depending
on how chowning is implemented, functional testing could be a bit tricky.

Documentation Impact
====================

New config options.

References
==========

* http://libvirt.org/formatdomain.html#elementsOSContainer

* http://libvirt.org/drvlxc.html#secureusers

* https://lwn.net/Articles/532593/
