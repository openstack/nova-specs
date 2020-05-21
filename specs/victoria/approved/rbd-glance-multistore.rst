..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

=======================================================
Libvirt RBD image backend support for glance multistore
=======================================================

https://blueprints.launchpad.net/nova/+spec/rbd-glance-multistore

Currently, Nova does not natively support a deployment where there are
multiple Ceph RBD backends that are known to glance. If there is only
one, Nova and Glance collaborate for fast-and-light image-to-VM
cloning behaviors. If there is more than one, Nova generally does not
handle the situation well, resulting in silent slow-and-heavy behavior
in the worst case, and a failed instance boot failsafe condition in
the best case. We can do better.

Problem description
===================

There are certain situations where it is desirable to have multiple
independent Ceph clusters in a single openstack deployment. The most
common would be a multi-site or edge deployment where it is important
that the Ceph cluster is physically close to the compute nodes that it
serves. Glance already has the ability to address multiple ceph
clusters, but Nova is so naive about this that such a configuration
will result in highly undesirable behavior.

Normally when Glance and Nova collaborate on a single Ceph deployment,
images are stored in Ceph by Glance when uploaded by the operator or
the user. When Nova starts to boot an instance, it asks Ceph to make a
Copy-on-Write clone of that image, which extremely fast and
efficient, resulting in not only reduced time to boot and lower
network traffic, but a shared base image across all compute nodes.

If, on the other hand, you have two groups of compute nodes, each with
their own Ceph deployment, extreme care must be taken currently to
ensure that an image stored in one is not booted on a compute node
assigned to the other. Glance can represent that a single logical
image is stored in one or both of those Ceph stores and Nova looks at
this during instance boot. However, if the image is not in its local
Ceph cluster, it will quietly download the image from Glance and then
upload it to its local Ceph as a raw flat image each time an instance
from that image is booted. This results in more network traffic and
disk usage than is expected. We merged a workaround to make Nova
refuse to do this antithetical behavior, but it just causes a failed
instance boot.

Use Cases
---------

- As an operator I want to be able to have a multi-site single Nova
  deployment with one Ceph cluster per site and retain the
  high-performance copy-on-write behavior that I get with a single
  one.

- As a power user which currently has to pre-copy images to a
  remote-site ceph backend with glance before being able to boot an
  instance, I want to not have to worry about such things and just
  have Nova do that for me.

Proposed change
===============

Glance can already represent that a single logical image is stored in
multiple locations. Recently, it gained an API to facilitate copying
images between backend stores. This means that an API consumer can
request that it copy an image from one store to another by doing an
"import" operation where the method is "copy-image".

The change proposed in this spec is to augment the existing libvirt
RBD imagebackend code so that it can use this image copying API when
needed. Currently, we already look at all the image locations to find
which one matches our Ceph cluster, and then use that to do the
clone. After this spec is implemented, that code will still examine
all the *current* locations, and if none match, ask Glance to copy the
image to the appropriate backend store so we can continue without
failure or other undesirable behavior.

In the case where we do need Glance to copy the image to our store,
Nova can monitor the progress of the operation through special image
properties that Glance maintains on the image. These indicate that the
process is in-progress (via ``os_glance_importing_to_stores``) and
also provide notice when an import has failed (via
``os_glance_failed_import``). Nova will need to poll the image,
waiting for the process to complete, and some configuration knobs will
be needed to allow for appropriate tuning.

Alternatives
------------

One alternative is always to do nothing. This is enhanced behavior on
top of what we already support. We *could* just tell people not to use
multiple Ceph deployments or add further checks to make sure we do not
do something stupid if they do.

We could teach nova about multiple RBD stores in a more comprehensive
way, which would basically require either pulling ceph information out
of Glance, or configuring Nova with all the same RBD backends that
Glance has. However, we would need to teach Nova about the topology
and configure it to not do stupid things like use a remote Ceph just
because the image is there.

Data model impact
-----------------

None.

REST API impact
---------------

None.

Security impact
---------------

Users can already use the image import mechanism in Glance, so Nova
using it on their behalf does not result in privilege escalation.

Notifications impact
--------------------

None.

Other end user impact
---------------------

This removes the need for users to know details about the deployment
configuration and topology, as well as eliminates the need to manually
pre-place images in stores.

Performance Impact
------------------

Image boot time will be impacted in the case when a copy needs to
happen, of course. Performance overall will be much better because
operators will be able to utilize more Ceph clusters if they wish,
and locate them closer to the compute nodes they serve.

Other deployer impact
---------------------

Some additional configuration will be needed in order to make this
work. Specifically, Nova will need to know the Glance store name that
represents the RBD backend it is configured to use. Additionally,
there will be some timeout tunables related to how often we poll the
Glance server for status on the copy, as well as an overall timeout
for how long we are willing to wait.

Developer impact
----------------

The actual impact to the imagebackend code is not large as we are just
using a new mechanism in Glance's API to do the complex work of
copying images between backends.

Upgrade impact
--------------

In order to utilize this new functionality, at least Glance from
Ussuri will be required for a Victoria Nova. Individual
``nova-compute`` services can utilize this new functionality
immediately during a partial upgrade scenario so no minimum service
version checks are required. The control plane does not know which RBD
backend each compute node is connected to, and thus there is no need
for control-plane-level upgrade sensitivity to this feature.


Implementation
==============

Assignee(s)
-----------
Primary assignee:
  danms

Feature Liaison
---------------

Feature liaison:
  danms

Work Items
----------

* Plumb the ``image_import`` function through the
  ``nova.image.glance`` modules

* Teach the libvirt RBD imagebackend module how to use the new API to
  copy images to its own backend when necessary and appropriate.

* Document the proper setup requirements for administrators


Dependencies
============

* Glance requirements are already landed and available

Testing
=======

* Functional testing should be relatively easy to implement for decent
  coverage.

* Devstack and tempest testing is *possible* although probably not
  very fruitful. The simplest way to do this is to deploy a devstack
  with both ceph and file stores. Uploading an image to the file store
  will cause it to be copied to the RBD backend on first boot,
  providing a very relevant (from Nova's perspective) single-RBD
  analog of the multi-RBD environment. That will require devstack
  changes, as well as a tempest test. It may be doable without tempest
  *config* changes requiring tempest to be told about the stores.


Documentation Impact
====================

This is largely admin-focused. Users that are currently aware of this
limitation already have admin-level knowledge if they are working
around it. Successful implementation will just eliminate the need to
care about multiple Ceph deployments going forward. Thus admin and
configuration documentation should be sufficient.

References
==========

* https://blueprints.launchpad.net/glance/+spec/copy-existing-image

* https://docs.openstack.org/glance/latest/admin/interoperable-image-import.html

* https://review.opendev.org/#/c/699656/8

History
=======

.. list-table:: Revisions
   :header-rows: 1

   * - Release Name
     - Description
   * - Victoria
     - Introduced
