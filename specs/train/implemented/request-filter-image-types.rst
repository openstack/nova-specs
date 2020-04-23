..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

==============================
Request Filter for Image Types
==============================

https://blueprints.launchpad.net/nova/+spec/request-filter-image-types

Nova supports multiple hypervisor drivers with multiple potential
configurations, most of which support some subset of the allowable
image types [1]_ that can be uploaded to glance. Nova needs a way to
make sure that it picks compute nodes that are capable of using the
type of image requested by the user.

Problem description
===================

Currently, Nova will happily schedule instances to compute nodes with
no regard for whether or not the compute node can even read the format
that the requested image is stored in. For example, if the other
properties match, the scheduler will choose a vmware host to boot a
qcow image, which it may not be able to even read. The existing
methods for preventing this include drastic global policy [2]_ to
auto-convert all images to flat raw files, or to do a lot of
hand-rolled segregating of the deployment to prevent images from
landing on inappropriate compute nodes.

Use Cases
---------

- As an operator, I want to have multiple hypervisors (of the same
  arch) in my deployment and still be able to utilize native optimized
  image formats.
- As an operator, I want to be able to use multiple classes of compute
  nodes with varying backend storage systems, some of which have image
  type requirements.
- As a user I want to be able to upload a native optimized image, have
  it be available immediately without conversion, and be able to boot
  it to a suitable host in the deployment.

Proposed change
===============

Nova has the information available to be able to connect new instances
with compute nodes that can support the image requested.  There is a
gap between the services that know about image support (i.e. the
compute node and virt driver) and the services that make decisions
about where to put new instances (i.e. the scheduler). This work aims
to bridge that gap so nova can make better decisions.

By exposing virt driver image format support as capabilities, and by
translating those capabilities to traits, we can report those to
placement so they are discoverable. The scheduler can examine the
format of the image during a server create or move request and ask
placement only for compute nodes that support that type (i.e. via a
new scheduler request filter). In other words, the request filter
works by mapping the image format to the appropriate trait and
including it as a required trait in the request.

Alternatives
------------

One alternative, as always, is to do nothing. Currently people solve
this in a variety of ways, from telling glance to auto-convert
everything to raw (i.e. the universal format), to hand-maintaining
aggregates and metadata to prevent images from landing in groupings of
hosts that will not be able to boot them.

Another alternative could be to do this as a scheduler filter. That
would still require the virt drivers to expose their supported types,
but would have the downside of much more (inefficient) filtering of
hosts in the scheduler.

Data model impact
-----------------

No changes are required to Nova's data model, nor placement's, but
os-traits will need to gain suitable traits for the image types we
plan to expose.

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

Performance should not be impacted negatively, but could be improved
depending on what current hacks are in place in deployer's systems to
provide this. Performance is definitely improved if operators are
currently requiring glance to flatten all images to raw, as after this
they would be able to leverage native optimized image formats.

Other deployer impact
---------------------

This effort will add a scheduler request filter, which (as is typical
with these) will bring a new boolean config toggle in the form of
``[scheduler]/filter_hosts_by_image_type_support``. The virt drivers
should be able to determine which image format capabilities to expose
from existing configuration data and thus do not need additional
configuration elements. The toggle for this could potentially be
removable in the future and just default to this behavior, if all the
virt drivers expose and continue to maintain proper image support
capability traits.

Developer impact
----------------

None

Upgrade impact
--------------

The new request filter will be disabled by default, and must remain
disabled until after an upgrade has completed so that compute nodes
will have registered their supported types. If the new filter were to
be enabled by default (or before the upgrade is complete), the
scheduler would receive no results from placement, as no nodes would
appear to support the required image formats.


Implementation
==============

Assignee(s)
-----------

Primary assignee:
  danms

Work Items
----------

* Add traits to os-traits
* Add capabilities and trait translations to the base virt driver
* Augment each in-tree driver with code to expose the desired capabilities
* Add a scheduler request filter for image types
* Enable the filter in a tempest gate job
* Add words to the existing scheduler documentation about request filters

Dependencies
============

None.

Testing
=======

Existing request filters are suitably covered by functional tests, and
this is no exception. We should also be able to enable this request
filter in a tempest job and have it exercise this code.


Documentation Impact
====================

Operators are impacted, and the existing scheduler documentation
around request filters will be augmented to cover this topic.

References
==========

.. [1] Glance image allowable disk formats: https://docs.openstack.org/image-guide/image-formats.html#disk-formats
.. [2] Glance forced format configuration: https://docs.openstack.org/glance/latest/configuration/glance_api.html#taskflow_executor.conversion_format

* Virt driver capabilities are now exposed as traits: https://review.openstack.org/#/c/538498/

History
=======

.. list-table:: Revisions
   :header-rows: 1

   * - Release Name
     - Description
   * - Train
     - Introduced
