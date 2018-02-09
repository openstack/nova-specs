..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

======================
Request traits in Nova
======================

https://blueprints.launchpad.net/nova/+spec/request-traits-in-nova

This blueprint aims to standardize the request of required qualitative
attributes using resource provider traits.

Problem description
===================

Cloud administrators currently have to deal with free-formed flavor extra_specs
and image metadata in order to specify capabilities in a launch request.
Without standardization of capabilities, there is no possibility of
interoperable OpenStack clouds. We have introduced traits to manage the
qualitative parts of ResourceProviders in Placement [1]_. Administrators should
be able to associate a set of required traits with flavors.

Use Cases
---------

For administrative users:

* Allow administrators to specify a set of traits that a flavor requires.

Proposed change
===============

We propose to store traits in flavor extra_specs and collect traits from
flavor in a boot request. Image metadata association is not in the scope of
this blueprint. The scheduler will pass traits to the
GET /allocation_candidates endpoint in the Placement API to filter out resource
providers without each of the required traits.

The trait syntax in flavor extra_specs looks like::

    trait:HW_CPU_X86_AVX2=required
    trait:STORAGE_DISK_SSD=required

The trait in the key of extra spec is for avoiding the length limit of the
value of extra spec. The only valid value is `required`. For any other
value will be considered as invalid.

Alternatives
------------

Instead of storing traits in flavor extra_specs we could add traits as a fields
of flavor model and save them into database. However, as the concept of flavor
maybe removed from Nova in the future, adding new fields into flavor should be
avoided.

Considering traits preference, we currently have some ideas about "Where to
specify preferences" and "How to order preferences", but they may not be
settled in this spec.

Data model impact
-----------------

None.

REST API impact
---------------

There is no direct API change. But when invaid traits in the flavor extra spec
or the invalid value in the trait extra spec, the server booting with that
flavor will fail. The server will get into the `error` status, just same as
the scheduling failed. This needn't new microversion, since it considers as
scheduling failed case which is current API behavior.

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


Implementation
==============

Assignee(s)
-----------

Primary assignee:
  Lei Zhang <lei.a.zhang@intel.com>

Other contributors:
  Alex Xu <hejie.xu@intel.com>
  Ed Leafe <ed@leafe.com>
  cyx1231st <yingxin.cheng@intel.com>

Work Items
----------

Extract traits from flavor extra_specs.


Dependencies
============

Dependent on a blueprint, Add trait support in the allocation candidates
API [2]_, which enables querying resource providers based on traits
for Placement service.


Testing
=======

Unit tests and functional tests for building up requests shall be added. The
functional test will be the end-to-end test for the trait integration between
nova and placement, the test should include the boot and migration cases.

Documentation Impact
====================

The user guide for specifying traits in flavor needs to be documented.

References
==========

.. [1] https://specs.openstack.org/openstack/nova-specs/specs/pike/approved/resource-provider-traits.html
.. [2] https://blueprints.launchpad.net/nova/+spec/add-trait-support-in-allocation-candidates

History
=======

.. list-table:: Revisions
   :header-rows: 1

   * - Release Name
     - Description
   * - Queens
     - Introduced
