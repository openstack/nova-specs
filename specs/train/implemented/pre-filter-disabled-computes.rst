..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

============================
Pre-filter disabled computes
============================

https://blueprints.launchpad.net/nova/+spec/pre-filter-disabled-computes

This blueprint proposes to make nova report a trait to placement when a
compute service is disabled and a request filter in the scheduler which
will use that trait to filter out allocation candidates with that forbidden
trait.


Problem description
===================

In a large deployment with several thousand compute nodes, the
``[scheduler]/max_placement_results`` configuration option may be limited
such that placement returns allocation candidates which are mostly (or all)
disabled compute nodes, which can lead to a NoValidHost error during
scheduling.

Use Cases
---------

As an operator, I want to limit ``max_placement_results`` to improve scheduler
throughput but not suffer NoValidHost errors because placement only gives
back disabled computes.

As a developer, I want to pre-filter disabled computes in placement which
should be faster (in SQL) than the legacy ``ComputeFilter`` running over the
results in python. In other words, I want to ask placement better questions
to get back more targeted results.

As a user, I want to be able to create and resize servers without hitting
NoValidHost errors because the cloud is performing a rolling upgrade and has
disabled computes.

Proposed change
===============

Summary
-------

Nova will start reporting a ``COMPUTE_STATUS_DISABLED`` trait to placement
for any compute node resource provider managed by a disabled compute service
host. When the service is enabled, the trait will be removed.

A scheduler `request filter`_ will be added which will modify the RequestSpec
to filter out providers with the new trait using `forbidden trait`_ filtering
syntax.

.. _request filter: https://opendev.org/openstack/nova/src/tag/19.0.0/nova/scheduler/request_filter.py
.. _forbidden trait: https://docs.openstack.org/nova/latest/user/flavors.html#extra-specs-forbidden-traits

Compute changes
---------------

For the compute service there are two changes.

set_host_enabled
~~~~~~~~~~~~~~~~

The compute service already has a `set_host_enabled`_ method which is a
synchronous RPC call. Historically this was only implemented by the `xenapi
driver`_ for use with the (now deprecated) `Update Host Status API`_.

This blueprint proposes to use that compute method to generically add/remove
the ``COMPUTE_STATUS_DISABLED`` trait on the compute nodes managed by that
service (note that for ironic a compute service host can manage multiple
nodes). The trait will be managed on only the root compute node resource
provider in placement, not any nested providers.

The actual implementation will be part of the `ComputeVirtAPI`_ so that
the libvirt driver has access to it when it automatically disables or enables
the compute node based on events from the hypervisor. [1]_

update_provider_tree
~~~~~~~~~~~~~~~~~~~~

During the ``update_available_resource`` operation which is called during
service start and periodically, the `update_provider_tree`_ flow will sync
the ``COMPUTE_STATUS_DISABLED`` trait based on the current disabled status
of the service. This is useful to:

1. Sync the trait on older disabled computes during the upgrade.
2. Sync the trait in case the API<>compute interaction fails for some reason,
   like a dropped RPC call.

API changes
-----------

When the `os-services`_ API(s) are used to enable or disable a compute service,
the API will synchronously call the compute service via the
``set_host_enabled`` RPC method to reflect the trait on the
related compute node resource providers in placement appropriately. For
example, if compute service A is disabled, the trait will be added. When
compute service A is enabled, the trait will be removed.

See the `Upgrade impact`_ section for dealing with old computes during a
rolling upgrade.

Down computes
~~~~~~~~~~~~~

It is possible to disable a down compute service since currently that disable
operation is just updating the ``services.disabled`` value in the cell
database. With this change, the API will have to check if the compute service
is up using the `service group API`_. If the service is down, the API will not
call the ``set_host_enabled`` compute method and instead just update the
``services.disabled`` value in the DB as today and return. When the compute
service is restarted, the `update_provider_tree`_ flow will sync the trait.

Scheduler changes
-----------------

A request filter will be added which will modify the RequestSpec to forbid
providers with the ``COMPUTE_STATUS_DISABLED`` trait. The changes to the
RequestSpec will not be persisted.

There will *not* be a new configuration option for the request filter meaning
it will always be enabled.

.. note:: In addition to filtering based on the disabled status of a node,
          the ``ComputeFilter`` also performs an `is_up check`_ using the
          service group API. The result of the "is up" check depends on whether
          or not the service was `forced down`_ or has not "reported in" within
          some configurable interval meaning the service might be down. This
          blueprint is *not* going to try and report the up/down status of a
          compute service using the new trait since it gets fairly complicated
          and is more of an edge case for unexpected outages.

.. _set_host_enabled: https://opendev.org/openstack/nova/src/tag/19.0.0/nova/compute/rpcapi.py#L891
.. _xenapi driver: https://opendev.org/openstack/nova/src/tag/19.0.0/nova/virt/xenapi/host.py#L121
.. _Update Host Status API: https://developer.openstack.org/api-ref/compute/?expanded=#update-host-status
.. _ComputeVirtAPI: https://opendev.org/openstack/nova/src/tag/19.0.0/nova/compute/manager.py#L419
.. _update_provider_tree: https://docs.openstack.org/nova/latest/reference/update-provider-tree.html
.. _os-services: https://developer.openstack.org/api-ref/compute/#compute-services-os-services
.. _service group API: https://docs.openstack.org/nova/latest/admin/service-groups.html
.. _is_up check: https://opendev.org/openstack/nova/src/tag/19.0.0/nova/scheduler/filters/compute_filter.py#L44
.. _forced down: https://developer.openstack.org/api-ref/compute/#update-forced-down

Alternatives
------------

1. Rather than using a forbidden trait, we could hard-code a resource provider
   aggregate UUID in nova and add/remove compute node resource providers
   to/from that aggregate in placement as the service is disabled/enabled.

   * Pros: Aggregates may be more natural since they are a grouping of
     providers.

   * Cons: Using an aggregate would be harder to debug from an operational
     perspective since provider aggregates do not have any name or metadata
     so an operator might wonder why a certain provider is not a candidate
     for scheduling but is in an aggregate they did not create (or do not
     see in the nova host aggregates API). Using a trait per provider with
     a clear name like ``COMPUTE_STATUS_DISABLED`` should make it obvious
     to a human that the provider is not a scheduling candidate because it
     is disabled.

2. Rather than using a forbidden trait or aggregate, nova could set the
   reserved inventory on each provider equal to the total inventory for each
   resource class on that provider, like what the ironic driver does when a
   node is undergoing maintenance and should be taken out of scheduling
   consideration. [2]_

   * Pros: No new traits, can just follow the ironic driver pattern.

   * Cons: Ironic node resource providers are expected to have a single
     resource class in inventory so it is easier to manage changing the
     reserved value on just that one class, but for non-baremetal providers
     they are reporting at least three resource classes (VCPU, MEMORY_MB and
     DISK_GB) so it would be more complicated to set reserved = total on all
     of those classes. Furthermore, changing the inventory is not configurable
     like a request filter is.

   Long-term, we could consider changing the ironic driver node maintenance
   code to just set/unset the ``COMPUTE_STATUS_DISABLED`` trait.

3. Rather than the ``os-services`` API synchronously calling the
   ``set_host_enabled`` method on the compute service, the API could just
   toggle the trait on the affected providers directly.

   * Pros: No blocking calls from the API to the compute service when changing
     the disabled status of the service - although one could argue the blocking
     nature proposed in the spec is advantageous so the admin gets confirmation
     that the service is disabled and will be pre-filtered properly during
     scheduling.

   * Cons: Potential duplication of the code that manages the trait which could
     violate the principle of single responsibility.

4. Do nothing and instead focus efforts on optimizing the performance of the
   nova scheduler which is likely the root cause that large deployments need
   to severely limit ``max_placement_results`` [3]_. However, regardless of
   optimizing the scheduler (which is something we should do anyway), part of
   making scheduling faster in nova is dependent on nova asking placement
   more informed questions and placement providing a smaller set of allocation
   candidates, i.e. filter in SQL (placement) rather than in python (nova).

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

None. Operators can use the `osc-placement`_ CLI to view and manage provider
traits directly.

.. _osc-placement: https://docs.openstack.org/osc-placement/latest/index.html

Performance Impact
------------------

In one respect this should improve scheduler performance during an upgrade
or maintenance of a large cloud which has many disabled compute services
since placement would be returning fewer allocation candidates for the nova
scheduler to filter.

On the other hand, this would add overhead to the ``os-services`` API when
changing the disabled status on a compute service.

Other deployer impact
---------------------

None

Developer impact
----------------

None

Upgrade impact
--------------

There are a few upgrade considerations for this change.

1. The API will check the RPC API version of the target compute service and if
   it is old the ``set_host_enabled`` method will not be called. When the
   compute service is upgraded and restarted, the ``update_provider_tree`` call
   will sync the trait.

2. Existing disabled computes need to have the trait reported
   on upgrade which will happen via the ``update_available_resource`` flow
   (update_provider_tree) called on start of the compute after it is upgraded.


Implementation
==============

Assignee(s)
-----------

Primary assignee:
  Matt Riedemann (mriedem) <mriedem.os@gmail.com>

Other contributors:
  None

Work Items
----------

* Make the changes to the compute service:

  * The ``set_host_enabled`` method
  * The ``update_provider_tree`` flow
  * The libvirt driver to callback to add/remove the trait when it is notified
    of the hypervisor going down or up

* Plumb the ``os-services`` API to call the ``set_host_enabled`` compute
  service method when the disabled status changes on a compute service

* Add a request filter which will add a forbidden trait to the
  RequestSpec to filter out disabled compute node resource providers during
  the GET /allocation_candidates call to placement.


Dependencies
============

The ``COMPUTE_STATUS_DISABLED`` trait would need to be added to the
`os-traits`_ library.

.. _os-traits: https://docs.openstack.org/os-traits/latest/


Testing
=======

Unit and functional tests should be sufficient for this feature.


Documentation Impact
====================

The new scheduler request filter will be documented in the admin docs. [4]_

References
==========

Footnotes
---------

.. [1] https://opendev.org/openstack/nova/src/tag/19.0.0/nova/virt/libvirt/driver.py#L3802

.. [2] https://specs.openstack.org/openstack/nova-specs/specs/rocky/implemented/allow-reserved-equal-total-inventory.html

.. [3] https://bugs.launchpad.net/nova/+bug/1737465

.. [4] https://docs.openstack.org/nova/latest/admin/configuration/schedulers.html

Other
-----

* The original bug reported by CERN: https://bugs.launchpad.net/nova/+bug/1805984

* Initial proof of concept: https://review.opendev.org/654596/

* Train PTG mailing list mention: http://lists.openstack.org/pipermail/openstack-discuss/2019-May/005908.html


History
=======

.. list-table:: Revisions
   :header-rows: 1

   * - Release Name
     - Description
   * - Train
     - Introduced
