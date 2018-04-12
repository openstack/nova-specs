..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

==========================================
Support traits in Glance
==========================================

https://blueprints.launchpad.net/nova/+spec/glance-image-traits

This blueprint proposes to extend the granular scheduling of compute instances
to use traits provided by glance image metadata in addition to the traits
provided by the flavor [1]_.

Problem description
===================

Currently, traits provided by the flavor are used by the scheduler only if:

1. Administrator creates a flavor with the traits required.
2. User picks the correct flavor with the required traits from the list.

Cloud administrative users might want to put some qualitative attributes on
workload images directly to assert control on where these workloads will be
scheduled.  These attributes can then be used as hints by the scheduler so that
it can pick the right set of compute hosts which can support these workloads
without the need for flavors to be pre-created and user needing to pick the
right flavor.

The attributes on the image can be used to specify traits required on the hosts
similar to traits on the flavor. For example support for a specific CPU
instruction set, NIC features or whether it's a trusted host, etc.

Use Cases
---------

As a cloud administrator, I want to be able to assert further control on where
certain workloads can be launched and be operational.

For example, if a workload instance will be applying an encryption algorithm or
will process privacy data, there might be specific capabilities/traits that the
instance needs on the hosts.

The administrator would be able to add these capability requirements to the
glance image as required traits. This would allow the nova scheduler to
automatically select only hosts which have those traits.

For administrative users

* Allow administrators to specify a set of traits that an image requires.

Proposed change
===============

Currently the traits information specified in the flavor is being collected as
part of the boot request. This information is provided to the Placement API
which uses it to filter out resource providers which do not have those traits
associated with them.

We propose to allow traits to be specified in the image metadata to be part of
the boot request work flow. The boot request will combine the traits
information provided by the flavor AND the image metadata into a union of the
two. This union set will be passed to the Placement API to generate allocation
candidates.

The glance image already allows users to specify additional properties as
key:value pairs. We will be re-using the same mechanism used by nova to encode
traits information in nova's flavor metadata items.

We propose to add `trait:` as a prefix so we can reuse the same name space as
the traits specified in the flavor extra_specs.

The trait syntax in the glance image's additional properties looks like::

    trait:HW_CPU_X86_AVX2=required
    trait:CUSTOM_TRUSTED_HOST=required

For now the only valid value is `required`. Validation of traits specified as
part of the image additional properties is out of scope for this change.

Due to the difficulty of attempting to reconcile `granular request groups`_
between an image and a flavor, only the (un-numbered) ``trait`` group is
supported. The traits listed there are merged with those of the un-numbered
request group from the flavor.

Based on the `ironic driver traits spec`_ implemented we need to send image
traits to ironic similar to how we are sending `extra_specs` traits to ironic.

**Dealing with rebuild**

In case of rebuild with new image(host and flavor staying the same), we need to
make sure the image traits(if updated) are taken into account. Ideally the
scheduler would request new candidates from placement and makes sure the
current host is part of that list, but this is problematic in-case the compute
is close to full as the current host will be excluded. This is described in the
issue `rebuild should not check with placement`_.

To resolve the above, the conductor can do `pre-flight` checks on the rebuild
request to make sure the image traits can still be accommodated within the
current allocations for that instance.

The conductor can request current allocations for the instance using
`GET /allocations/{instance_uuid}` and collect all the resource providers and
their corresponding traits from the allocations. It can then check to see if
any of the requested image traits are missing from the set of traits above.
If there are any missing traits, we can fail the rebuild.

Alternatives
------------

Continue with the current model of utilizing the traits provided as part of the
flavor in the boot request.

This would mean that the cloud administrator would need to create specific
flavors with traits required for the workload image and the end user needs to
select the flavor with the configured traits.

One other aspect to look at would be, because the flavor describes both the
quantitative and qualitative aspects of the request, the number of flavors will
need to increase substantially if we are given a mix of workloads.

In a typical Openstack installation with 7 flavors(nano -> xlarge) if we need
to add one trait to each of the flavors we will end up with 14 flavors. If we
need to add combinations of traits along with the quantitative aspects, this
number will grow pretty quickly.

Another potential alternative is to provide traits directly as part of the
instance boot request. But this has the same issue where the end user could
forget to select the right traits.

With Image based traits the administrator sets the traits once on the image and
the approach is immune to user errors during launch.

Another alternative is to use the AggregateImagePropertiesIsolation
filter to filter select hosts within specific host aggregates. Host aggregate
metadata is not standardized unlike the traits and also requires host
aggregates to be pre-created with duplicated standard traits which is not
ideal.

**Dealing with rebuild**

see `rebuild should not check with placement`_

*Alternative 1*

If the image's required traits have changed from the original image, we can
reject the rebuild request at the API layer with a clear error message. This is
a simpler approach but comes with draw backs.

In scenarios where a user is trying to do a rebuild that should be valid, the
request would get rejected because old image traits != new image traits. It
seems like unnecessary user and admin pain.

*Alternative 2*

The scheduler can request traits of current host using the existing
`GET /resource_providers/{UUID}/traits` API and try to match the
traits returned for the current host against the traits specified in the image.

If the traits do not match, `NoValidHost` exception will be raised before the
filters are run. If the traits match, then the request will continue to be
processed as it does currently(passing through the various filters etc)

Potential issue with this is that the traits on the image maybe attached to a
nested resource provider under the compute node. For example, in case the
instance is running on a host which has two SRIOV nic's. One is normal SRIOV
nic, another one with some kind of offload feature.

So, the original request is::

    resources=SRIOV_VF:1

The instance gets a VF from the normal SRIOV nic.

But with the new image, the new request is::

    resources=SRIOV_VF:1
    traits=HW_NIC_OFFLOAD_XX

To handle nested resource providers and gather their traits we might need to
make multiple `GET /resource_providers/{UUID}/traits` for every resource
provider present in the tree.

Ideally this request should fail since we can't ensure we allocated VF from the
other SRIOV PF.

This alternative can also be implemented in the ImagePropertiesFilter in case
of rebuild. But this is not ideal since none of the other filters make any API
calls during the filtering process.

*Other alternatives*

Few other alternatives have been discussed on the ML [2]_.


Data model impact
-----------------

Update `ImageMetaProps` class to return traits as key:value

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

None.

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
  Arvind Nadendla <arvind.nadendla@intel.com>

Other contributors:
  Mohammed Karimullah <karimullah.mohammed@intel.com>

Work Items
----------

* Update `ImageMetaProps` class to return traits
* Update Nova Scheduler to extract properties from `ImageMeta` and pass them
  to the Placement API
* Update Nova Conductor to validate the image traits match the existing
  allocations for the instance during a rebuild
* Need to update the ironic virt driver to push traits from images to nodes
  based on `ironic driver traits spec`_

Dependencies
============

None.

Testing
=======

Unit tests and functional tests for building up requests shall be added.

Documentation Impact
====================

* Update `property keys`_ page to explain use of traits similar to
  `flavor traits doc`_ traits section

.. _property keys: https://docs.openstack.org/python-glanceclient/pike/cli/property-keys.html
.. _flavor traits doc: https://docs.openstack.org/nova/latest/user/flavors.html

References
==========

.. [1] http://specs.openstack.org/openstack/nova-specs/specs/queens/approved/request-traits-in-nova.html

.. [2] http://lists.openstack.org/pipermail/openstack-dev/2018-April/129726.html

.. _ironic driver traits spec: https://review.openstack.org/#/c/508116/
.. _granular request groups: http://specs.openstack.org/openstack/nova-specs/specs/rocky/approved/granular-resource-requests.html#numbered-request-groups
.. _rebuild should not check with placement: https://bugs.launchpad.net/nova/+bug/1750623

History
=======

.. list-table:: Revisions
   :header-rows: 1

   * - Release Name
     - Description
   * - Rocky
     - Introduced
