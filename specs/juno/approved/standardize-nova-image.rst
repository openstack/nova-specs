..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

======================
Standardize Nova Image
======================

https://blueprints.launchpad.net/nova/+spec/standardize-nova-image

Standardize Nova's nova.image module to work like nova.network.api
and nova.volume.cinder.

Problem description
===================

For some reason, nova.image does things differently than nova.volume and
nova.network. Instead of nova.compute.manager instantiating a
self.image_api object, like it does for self.network_api and
self.volume_api, the compute manager calls an obtuse collection of
nova.image.glance module calls.

This blueprint is around the work to make a new nova.image.api module
and have it called like other submodule "internal APIs" in Nova.

Proposed change
===============

A new nova.image.api module shall be created, following in the style
of nova.network.api and nova.volume.cinder. There will be an API class
in the nova.image.api module that follows identical conventions as the
nova.volume.cinder.API class, with methods for listing (get_all), showing
(get), creating (create), updating (update), and removing (delete)
images from the backend image store. There will be a nova.image.driver
module with a base driver class.

The nova.image.glance module will be updated to subclass the base driver
class.

Alternatives
------------

There is a series of patches in review up for Nova that tries to add
support for Glance's V2 API operations:

https://review.openstack.org/#/q/status:open+project:openstack/nova+branch:master+topic:bp/use-glance-v2-api,n,z

Unfortunately, I believe this patch series further muddies the image
service inside Nova instead of making it cleaner and standardized with
the rest of Nova's external API interfaces.

The idea of this blueprint is to lay a good foundation for future V2
Glance API work by first standardizing the image API inside of Nova.

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
None

Developer impact
----------------

See above link to Eddie Sheffield's patch series that would be affected by the
code in this blueprint. Hopefully, however, once the image API is brought in
line with the other internal-to-external Nova APIs, the work on V2 Glance API
should be quite a bit easier.

Implementation
==============

Assignee(s)
-----------

Primary assignee:
  jaypipes

Work Items
----------

 * Create the nova.image.api module that instantiates a driver
 * Create the base image driver class, modeling after the new
   nova.network.driver class created by the refactor-network-api blueprint
   code.
 * Move the existing glance code into a subclassed driver

Dependencies
============
None

Testing
=======
None

Documentation Impact
====================
None

References
==========
None
