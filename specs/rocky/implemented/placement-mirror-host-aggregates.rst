..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

========================================
Mirror nova host aggregates in placement
========================================

https://blueprints.launchpad.net/nova/+spec/placement-mirror-host-aggregates

This spec proposes to ensure that the placement service has a placement
aggregate record for each nova host aggregate.

Problem description
===================

Nova host aggregates are useful for grouping collections of ``nova-compute``
service workers together. Certain scheduler filters such as the
``AggregateMultiTenancyIsolationFilter`` `filter`_ look at metadata stored
against a nova host aggregate when evaluating whether a hypervisor host meets
certain filtering criteria.

.. _filter: https://github.com/openstack/nova/blob/stable/queens/nova/scheduler/filters/aggregate_multitenancy_isolation.py

In order to `replace`_ some of these filters with similar filter parameters to
the ``GET /allocation_candidates`` placement REST API, we first need to ensure
that nova host aggregates that tie collections of ``nova-compute`` service
workers together are represented in the placement API as **placement
aggregates** and associated with the **resource provider** records that
correspond to the compute node that the ``nova-compute`` service manages.

.. _replace: https://blueprints.launchpad.net/nova/+spec/alloc-candidates-member-of

Use Cases
---------

As a deployer I want to be able to leverage placement aggregates for my normal
host-aggregate groupings and thus I want nova to keep the changes I make
mirrored to placement for me.

Proposed change
===============

We propose to modify the implementation of the Compute API to call to the
placement service (via the scheduler reportclient) when a "host" member is
added or removed from a nova host aggregate.

Similarly, when a nova host aggregate is deleted, there will be a call to the
placement service to remove any resource provider to placement aggregate
associations for the nova host aggregate in question.

We will *not* be communicating with the placement service for either the
creation or update of a nova host aggregate, since the placement service does
not need to create a record for an aggregate until such time as a resource
provider is associated with it.

A new data migration command ``sync_placement_aggregates`` will be added to
synchronize existing nova host aggregate records using the ``nova-manage``
tool.

.. note::

    If there is a failure in nova-api communicating with the placement service,
    we will log a warning but not return an error to the end user. The
    nova-manage command will allow reconciling aggregate information at a later
    time.

Alternatives
------------

We could have adapted the ``nova-compute`` service workers to do this syncing
behaviour, but that would have required an upcall from the computes to the nova
api layer.

We could have had an external agent do the mirroring/syncing behaviour.

We could use a periodic task in the nova-scheduler service instead of a
nova-manage command.

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

There will be a slight negative impact to the ``add_host`` and ``remove_host``
operations for the Compute API since it will now need to communicate with the
placement service.

Other deployer impact
---------------------

The nova-api service's nova.conf file will now need to contain placement
service authentication credentials in order for the nova-api service to
communicate with placement. We will make the lack of placement auth credentials
a warning in Rocky and required in Stein.

In addition, the operator will want to run the ``nova-manage
sync_placement_aggregates`` command periodically to ensure nova and placement
have reconciled views of aggregate information.

Developer impact
----------------

None.

Upgrade impact
--------------

The nova-api service will now depend on being configured to authenticate with
the placement service, similar to the nova-compute and nova-conductor services.
We will make this a soft failure (warning in logs) in Rocky and a hard failure
in Stein.

Implementation
==============

Assignee(s)
-----------

Primary assignee:
  jaypipes

Work Items
----------

* Add initialization check to nova-api to auth with placement. Make this a
  non-hard failure for Rocky and a note about failing hard in Stein
* Add methods to the scheduler reportclient for adding an aggregate association
  to a resource provider **by name**, since the os-aggregates Compute API uses
  a non-UUID host name parameter for identifying the nova-compute service
  worker
* Modify the ``nova.compute.api.AggregateAPI.add_host_to_aggregate()`` and
  ``remove_host_from_aggregate()`` methods to call out to the reportclient to
  add or remove a resource provider to aggregate association by provider name
* Create new ``sync_placement_aggregates`` command in the ``nova-manage`` tool

Dependencies
============

None.

Testing
=======

Normal testing as well as full functional tests of the new ``nova-manage
sync_placement_aggregates`` command.

Documentation Impact
====================

A release note describing the mirroring process, requirement of the nova-api's
nova.conf to contain placement credentials and inclusion of the
``sync_placement_aggregates`` command in ``nova-manage`` should be done. In
addition, the `placement API reference`_ should be updated to describe how the
nova host aggregates are mirrored to placement.

.. _placement API reference: https://developer.openstack.org/api-ref/placement/#resource-provider-aggregates

References
==========

* Enables these blueprints:

 * `Placement aggregate allocation ratios`_
 * `Placement filter requests`_

.. _Placement aggregate allocation ratios: https://blueprints.launchpad.net/nova/+spec/placement-aggregate-allocation-ratios
.. _Placement filter requests: https://blueprints.launchpad.net/nova/+spec/placement-req-filter
