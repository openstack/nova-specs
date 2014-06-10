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

* The virt driver generates the configdrive and gzips it.

* The virt driver puts the gzipped image in some system and holds on to
  a URI for the image.

* The virt driver will pass this URI to Ironic.

* If present, Ironic will pass this URI to its DeployDriver, which will
  in turn provide it to the instance during provisioning, by means appropriate
  to that driver.

* Ironic uses this URI to write a configdrive partition on the
  instance during provisioning.

* The reference implementation for this will be using Swift, with a
  configurable TTL.

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

This proposal involves storing end user data in Swift. This may be a security
concern, as this data is not encrypted at rest.

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

The reference implementation will add a hard dependency on Swift for
deployers that wish to use configdrive support with Ironic. Other
implementations may remove this dependency.

The reference implementation will also add corresponding config options
for the Swift client.

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

* Add a wrapper for python-swiftclient that can, at a minimum, upload objects
  to Swift.

* Implement the code and unit tests. This will involve changing the deploy()
  function in Ironic's virt driver to generate the configdrive, upload
  it to Swift, and pass the Swift URL for the configdrive in the PATCH
  request to Ironic. The tear_down() method of Ironic's virt driver will
  be changed to remove the configdrive key from instance_info. Unit tests will
  need to be updated accordingly.

* Configure tempest tests to properly exercise this feature.


Dependencies
============

This change depends on Ironic support for writing the configdrive to the
instance. [1]


Testing
=======

Use tempest to test this feature, when configured properly.


Documentation Impact
====================

Documentation may need to be updated to indicate that a configdrive may
be used with bare metal instances.


References
==========

[1] Ironic configdrive spec: https://review.openstack.org/#/c/99235/
