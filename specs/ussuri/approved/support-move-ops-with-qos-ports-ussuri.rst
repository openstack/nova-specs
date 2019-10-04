..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

=========================================================
Server move operations with ports having resource request
=========================================================

https://blueprints.launchpad.net/nova/+spec/support-move-ops-with-qos-ports-ussuri

Problem description
===================

Since `microversion 2.72`_ nova supports creating servers with neutron ports
having resource request. Since the Train release nova also supports cold
migrating and resizing such servers. However other move operations i.e. live
migration, evacuation and unshelve after shelve offload are still not
possible due to missing resource handling implementation in nova.

Use Cases
---------

The admin needs to be able to request the same life-cycle operations
for these servers as for any other servers.

Proposed change
===============

To support live-migrate, evacuate and unshelve we will follow the
implementation pattern that is described in the `Train spec`_ and then
implemented for cold migrate and resize during the Train release.

During the Train implementation the `compute RPC API`_ methods were extended
with the necessary RequestSpec parameter for every move operation. So no
further RPC change is expected during the implementation of this spec.

During evacuate and unshelve operations the compute manager is responsible to
update the port binding in neutron. These code paths will be extended to also
update the allocation key in the port binding according to the allocation on
the target host.

During live-migrate nova uses the multiple bindings API of neutron to manage
the bindings on the source and the target host in parallel. The conductor
creates the new, inactive binding on the destination host in neutron and it
will add the ``allocation`` key in the new binding according to the
``RequestSpec``. When the live-migrate finishes the source port binding is
deleted along with the source host allocation. If the live-migration is
rolled back the source host binding still has the proper ``allocation`` key
set.

From the not-yet-supported move operations only live-migration has a reschedule
loop. It is handled in the ``LiveMigrationTask`` in the super conductor.
During reschedule the allocation key of the port binding of the neutron ports
needs to be updated according to the new allocation on the newly selected
target host.

The multiple bindings neutron API extension cannot be turned off so if it is
not present nova can fail the live-migrate operation if ports have resource
request.

Currently these move operations are rejected by nova if the server has ports
attached with resource request. After the above proposed change is implemented
these operations will be allowed. The way we will signal that nova is capable
of supporting these operations is described in the `REST API impact`_ section.

Alternatives
------------

None

Data model impact
-----------------

None

REST API impact
---------------
At the Train PTG we `agreed`_ to implement the support for the move operations
as bugfixes without any new microversion. After the implementation is done the
code that currently rejects the move operations are removed from the API and
nova will accept and support these operations with any microversion.

This is what we did with cold migrate and resize in Train and will follow that
pattern in Ussuri.

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

During move operations the conductor needs to query neutron to get the
resource request of the ports that are attached to the server. Also, after the
scheduling the request group - resource provider mapping needs to be
recalculated and the binding:profile of the ports needs to be updated in
neutron.

Other deployer impact
---------------------

None

Developer impact
----------------
None

Upgrade impact
--------------

As the solution depends on a minimum RPC version and as it requires compute
manager changes the move operations can only be supported after both the
source and the destination host are upgraded. So the conductor needs to ensure
that the service version of both computes is high enough. However if the
conductor is configured with ``[upgrade_levels]compute=auto``
(e.g. rolling upgrade) or the compute RPC is manually pinned then even if both
the source and the destination computes are new enough the destination compute
may still not get the necessary information to perform the port binding update.
Therefore an additional check is needed based on the actual RPC version used
towards the destination compute. These checks will be similar to the ones that
were implemented for `cold migration`_.

The support for move operations makes it possible to heal missing or
inconsistent port allocations as during the move the requested resources are
re-calculated and the new allocation created accordingly in placement. This
will complement `the port allocation healing capabilities`_ of the
``nova-manage placement heal_allocations`` CLI that has multiple limitations in
this regard.

In general the operators having incomplete port allocations are recommended to
try to heal that with the ``heal_allocations`` CLI in place if possible to
minimize the number for server move operations required.

Implementation
==============

Assignee(s)
-----------


Primary assignee:
  balazs-gibizer

Other contributors:
  None

Core Liaison
------------

Core liaison:
  mriedem

Work Items
----------

For each move operation:

* Before scheduling, gather the requested resource from neutron and update
  the RequestSpec accordingly
* After the scheduler selected the destination of the move operation calculate
  the resource provider - request group mapping and update the neutron port
  binding according to the destination allocation. This happens on the compute
  side for evacuate and unshelve but happens still in the conductor for live
  migration.
* If there are SRIOV interfaces involved update the InstancePciRequest to drive
  the PCI resource claim on the destination compute to consume VFs from the
  same PF as the port resources are allocated from.

For live migration the reschedule also needs to be handled in the super
conductor.


Dependencies
============

None

Testing
=======

Each move operation will have a functional test asserting that the proper
allocation exists after the move, old allocations are removed, and the port
binding in neutron refers to the appropriate resource provider.

For live migration reschedule also needs to be covered with functional tests.

When the source compute is recovered the compute manager cleans up the
evacuated instances. We need test coverage to make sure that the bandwidth
allocation is cleaned up from the source host but the neutron port binding is
not changed as it is expected to already point to the target host allocation.

Documentation Impact
====================

The API guide `Using ports with resource request`_ will be updated accordingly.
Also the Limitations section of the neutron admin guide
`Quality of Service Guaranteed Minimum Bandwidth`_ needs to be updated.

References
==========

.. _`bandwidth resource provider spec`: https://specs.openstack.org/openstack/nova-specs/specs/stein/implemented/bandwidth-resource-provider.html
.. _`Train spec`: https://specs.openstack.org/openstack/nova-specs/specs/train/approved/support-move-ops-with-qos-ports.html
.. _`microversion 2.72`: https://docs.openstack.org/nova/latest/reference/api-microversion-history.html#maximum-in-stein
.. _`Using ports with resource request`: https://docs.openstack.org/nova/latest/admin/port_with_resource_request.html
.. _`Quality of Service Guaranteed Minimum Bandwidth`: https://docs.openstack.org/neutron/latest/admin/config-qos-min-bw.html
.. _`ML thread`: http://lists.openstack.org/pipermail/openstack-discuss/2019-January/001881.html
.. _`the port allocation healing capabilities`: https://review.openstack.org/#/c/637955
.. _`agreed`: http://lists.openstack.org/pipermail/openstack-discuss/2019-May/005807.html
.. _`cold migration`: https://github.com/openstack/nova/blob/4d034b79eb4483848fa8346149d0387af4eeaa2a/nova/conductor/tasks/migrate.py#L383
.. _`compute RPC API`: https://github.com/openstack/nova/blob/4d034b79eb4483848fa8346149d0387af4eeaa2a/nova/compute/rpcapi.py#L367

History
=======

.. list-table:: Revisions
   :header-rows: 1

   * - Release Name
     - Description
   * - Train
     - Introduced
   * - Ussuri
     - Updated to show the remaining scope for Ussuri.
