..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

===================================================================
Support filtering of allocation_candidates by forbidden aggregates
===================================================================

https://blueprints.launchpad.net/nova/+spec/placement-req-filter-forbidden-aggregates

This blueprint proposes to specify forbidden aggregates in the `member_of`
query parameter of the `GET /allocation_candidates` placement API during
scheduling.

Problem description
===================

If flavor or image doesn't contain any ``required`` or ``forbidden``
traits, then all resource providers will be eligible to be returned in the
``GET /allocation_candidates`` API call depending on the availability of the
requested resources. Some of the resource providers (compute host) could be
special ones like `Licensed Windows Compute Host`, meaning any VM booted on
this compute host will be considered as licensed Windows image and depending
on the usage of VM operators will charge it to their end-users. As an operator,
I want to avoid booting non-windows OS images/volumes on aggregates which
contains `Licensed Windows Compute Hosts`. The existing
``AggregateImagePropertiesIsolationFilter`` scheduler filter does restricts
windows license images to windows license host aggregates but the problem is it
doesn't exclude other images without matching metadata.

Consider following example to depict the licensing use case.
Operator adds image metadata to classify images as below:

.. code::

  image 1 properties: {"os_distro": "windows"} (added by an operator)
  image 2 properties: {} (added by a normal end user)

  Host aggregate 1 metadata: {"os_distro": "windows"}

Now when user boots an instance using image 2, then this scheduler filter
allows to boot instance in host aggregate 1 which is a problem.

Use Cases
---------

Some of the compute hosts are `Licensed Windows Compute Host`, meaning any VMs
booted on such compute host will be considered as licensed Windows image and
depending on the usage of VM, operator will charge it to the end-users.
As an operator, I want to avoid booting non Windows OS images/volumes on
the `Licensed Windows Compute Hosts` thereby enabling operators to

* Avoid wasting licensing resources.

* Charge users correctly for their VM usage.

Proposed change
===============

Add a new placement request filter ``forbidden_aggregates`` and a new config
option of type boolean ``enable_forbidden_aggregates_filter``. Operator will
set `True` to enable the request filter. By default the value will be set to
`False`. Operator will need to set aggregate metadata key/value pairs
`trait:<trait_name>=required` with traits which they expect to match with the
`trait:<trait_name>=required` set in the flavor and images of the create
server request from request_spec object. In the new request filter, it will
get the required traits set in both flavor and images from request_spec object
and compare it with the required traits set in the aggregate metadata.
If any of the traits are not matching with the aggregate metadata, it will
include that aggregate as forbidden aggregate in the ``member_of`` query
parameter of ``GET /allocation_candidates`` API. If there are multiple
forbidden aggregates, then the query parameter should be like:

``&member_of=!in:<agg1>,<agg2>,<agg3>``

Example, how to set multiple traits to the metadata of an aggregate,

.. code::

  openstack aggregate set --property trait:CUSTOM_WINDOWS_LICENSED=required 123
  openstack aggregate set --property trait:CUSTOM_XYZ=required 123

Operator will need to set ``trait:<trait_name>=required`` to images for
windows OS images.

.. code::

  openstack image set --property trait:CUSTOM_WINDOWS_LICENSED=required <image_uuid>

Example, how to enable ``forbidden_aggregates`` placement request filter:

.. code::

  [scheduler]
  enable_forbidden_aggregates_filter = True

This ``forbidden_aggregates`` placement request filter supersedes
existing ``IsolatedHostsFilter`` except it:-

* Relies on aggregates rather than individual hosts (which won't scale in
  large environments like a public cloud).

* Relies on image properties rather than specific image IDs, which again
  won't scale.

With this placement request filter in place, there is a possibility we can
deprecate ``IsolatedHostsFilter`` scheduler filter for reasons as stated above.

Alternatives
------------

Option 1: `Strict-isolation-group-hosts-images`_ spec

The main issues with this spec are:

* Adding a new scheduler filter which yet again depends on metadata key for
  host aggregates.

* A compute node associated with multiple host aggregates. This is a
  fundamental problem with nova host aggregates that doesn't exist in placement
  aggregates.

Option 2: `Bi-directional-enforcement-of-traits`_ spec

The main issue with this spec is:

It's not placement's job to make operators have an easy life. Operators
should be required to set up their deployment's providers with an appropriate
set of traits, put providers into appropriate aggregates, put appropriate
metadata on their own images and flavors, and configure *Nova* with the set
of configuration options that would allow these things to be used properly.

Option 3: Use `IsolatedHostsFilter`_ scheduler filter

It doesn't really scale in a large public cloud with thousands of hosts and
images. Also, if you add new hosts in the system, you will need to modify the
config option ``isolated_hosts`` from ``filter_scheduler`` section and restart
nova scheduler services.

Data model impact
-----------------

None.

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

DB call to fetch aggregates with value `required` in the
``forbidden_aggregates`` placement request filter will marginally impact the
overall processing time of each `select_destination` request.

Other deployer impact
---------------------

A new config boolean option ``enable_forbidden_aggregates_filter`` will be
added in nova.conf which will be used by nova-scheduler service.
The default value of this config option will be set to false.

.. code::

  enable_forbidden_aggregates_filter=False

To enable `forbidden_aggregates` request filter, operator should set this
config option to true.

Developer impact
----------------

None.

Upgrade impact
--------------

Starting from Rocky release, nova host aggregates are mirrored in placement
service (Implemented in `mirror_nova_host_aggregates`_). But if there is any
problem in mirroring, operator can sync it manually with ``nova-manage``
command:

``nova-manage placement sync_aggregates``

This spec will not sync traits to placement and it will not add these
traits to the compute node resource providers that belongs to the aggregates
which has metadata key=value pair with syntax `trait:<trait_name>=required`.
Please refer to the `Nova meeting log`_ and `Mailing thread`_ where we have
mutually agreed to let operator sync these traits manually. In future,
if required, a utility tool can be developed for syncing these traits which is
outside the scope of this spec.

Implementation
==============

Assignee(s)
-----------

Primary assignee:
    shilpa.devharakar <shilpa.devharakar@nttdata.com>

Work Items
----------

* Add a placement request filter ``forbidden_aggregates``.
* Modify ``resources_from_request_spec`` method to add forbidden aggregates to
  the Destination object.
* Modify ``RequestGroup`` class `to_querystring` method to generate a
  `member_of` query parameter to pass forbidden aggregates in format
  ``&member_of=!in:<agg1_uuid>,<agg2_uuid>,<agg3_uuid>``.
* Add unit and functional tests for the changes.
* Add releasenotes.

Dependencies
============

This spec is dependent on `negative-aggregate-membership`_ which supports
passing forbidden aggregates in the `member_of` query parameter.

Testing
=======

Add normal functional and unit testing.

Documentation Impact
====================

Add documentation to explain how to use ``forbidden_aggregates`` placement
request filter.

References
==========

.. _negative-aggregate-membership: https://review.openstack.org/#/c/603352/4/specs/stein/approved/negative-aggregate-membership.rst
.. Launchpad Bug: https://bugs.launchpad.net/nova/+bug/1677217
.. _Bi-directional-enforcement-of-traits: https://review.openstack.org/#/c/593475/2/specs/stein/approved/bi-directional-traits.rst
.. _Strict-isolation-group-hosts-images: https://review.openstack.org/#/c/381912/17/specs/rocky/approved/strict_isolation_of_group_of_hosts_for_image.rst
.. _mirror_nova_host_aggregates: https://specs.openstack.org/openstack/nova-specs/specs/rocky/implemented/placement-mirror-host-aggregates.html
.. _IsolatedHostsFilter: https://docs.openstack.org/nova/latest/admin/configuration/schedulers.html#isolatedhostsfilter
.. _Nova meeting log: http://eavesdrop.openstack.org/meetings/nova/2019/nova.2019-06-13-14.00.log.html#l-267
.. _Mailing thread: http://lists.openstack.org/pipermail/openstack-discuss/2019-June/006950.html
.. Rocky PTG: https://etherpad.openstack.org/p/nova-ptg-rocky
.. Stein PTG: https://etherpad.openstack.org/p/nova-ptg-stein

History
=======

.. list-table:: Revisions
   :header-rows: 1

   * - Release Name
     - Description
   * - Stein
     - Introduced
   * - Train
     - Re-proposed
