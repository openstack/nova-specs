..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

===========================
Use configdrive with Ironic
===========================

https://blueprints.launchpad.net/nova/+spec/use-configdrive-with-ironic

This blueprint adds support for configdrive for the Ironic virt driver, to
enable Nova to pass a configdrive to Ironic, to be used when deploying a
bare metal instance.

Problem description
===================

Instances deployed by Ironic should be able to use cloud-init (or similar
software) to put an end user's data on an instance. This is possible today with
Ironic by including cloud-init with the image, and pointing it at a Nova
metadata service.

There are two issues with this approach:

* Some deployers do not run a metadata service in their environment.

* If a deployer provisions Ironic machines using static IP address assignment,
  the instance will not have network access until cloud-init puts the network
  configuration into place. If the metadata service is the only way to get
  the network configuration, the instance is deadlocked on getting network
  access.

To solve these problems, a configdrive image can take the place of the metadata
service. In the VM world, this is typically handled by the hypervisor exposing
a configdrive image to the VM as a volume.

In Ironic's case, there is no hypervisor, so this image needs to be exposed to
the instance in some other fashion. This could be accomplished by writing the
image to a partition on the node, exposing the image via the out-of-band
mechanism (e.g. a virtual floppy in HP's iLO), or configuring the node to mount
the image from a SAN. In any case, this needs to be handled by Ironic, rather
than Nova. However, Nova has the data that belongs in the configdrive, as well
as the code to generate the image. So, it makes sense for Nova to generate an
image and pass it to Ironic.

Use Cases
---------

The main use case here is feature parity with other virt drivers. Other
drivers support configdrive today, and deployers use it. Deployers of
Ironic should also be able to use configdrives.

There are two main use cases as described above:

* Deployers that do not use the metadata service.

* Deployers that wish to use static IP assignment, where the instance
  will not have network access to get to the metadata service.

Project Priority
----------------

The kilo priorities list is currently not defined, however "virt driver
feature parity" seems important.


Proposed change
===============

Nova should generate the configdrive image and pass it to Ironic, if needed.
This should use the existing code (nova.virt.configdrive:required_by) to
determine if a configdrive should be generated.

This will consist of these steps:

* The Ironic virt driver decides if a configdrive should be generated for this
  instance. If so:

* The virt driver generates the configdrive, gzips and base64 encode it.

* The virt driver passes the encoded image to Ironic via the Ironic API.

* The Ironic service will then store the image in some system and holds
  on to a URI for it, or if no external system is configured, Ironic
  will save the image into its database. The reference implementation
  for this will be using Swift, with a configurable TTL.

* Ironic pass the image to the deploy driver that will then expose it
  to the tenant. The initial implementation will create a config drive
  partition on the disk and copy the image onto it, but it could be extended
  to use the virtual media out-of-band if the target hardware supports it.

Alternatives
------------

The only alternative to solving the problems described above, is to write
network configuration and user data directly to the image to be deployed, on
the fly. I think it is suffice to say that Ironic should not be in the business
of injecting files directly into images, nor should we force end users to
use custom images with this data already injected.

As mentioned before, Ironic's drivers may provide various mechanisms for
exposing this image to the instance. However, no matter the mechanism used,
the interaction will be the same from Nova's perspective.

Data model impact
-----------------

None.

REST API impact
---------------

None.

Security impact
---------------

None for this spec, but Ironic might store the end user data in
Swift. This may be a security concern, as this data is not encrypted
at rest.

Notifications impact
--------------------

None.

Other end user impact
---------------------

None.

Performance Impact
------------------

Generating the configdrive image and sending it to another service will cause
Nova to spend more time in Ironic's virt driver, although the additional time
spent should be relatively small.

Other deployer impact
---------------------

None.

Developer impact
----------------

None.


Implementation
==============

Assignee(s)
-----------

Primary assignee:
  jroll

Work Items
----------

* Implement the code and unit tests. This will involve changing the
  spawn() function in Ironic's virt driver to generate the configdrive,
  gzip, base64 encode it and pass it to Ironic as part of the request BODY
  of the API call to start the deployment of the Node.

Dependencies
============

This change depends on Ironic support for writing the configdrive to the
instance. [1]


Testing
=======

Unittests.


Documentation Impact
====================

Documentation may need to be updated to indicate that a configdrive may
be used with bare metal instances.


References
==========

[1] Ironic configdrive spec: https://review.openstack.org/#/c/99235/
