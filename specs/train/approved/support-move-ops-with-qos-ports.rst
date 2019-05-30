..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

=========================================================
Server move operations with ports having resource request
=========================================================

https://blueprints.launchpad.net/nova/+spec/support-move-ops-with-qos-ports

Problem description
===================

Since `microversion 2.72`_ nova supports creating servers with neutron ports
having resource request. However moving such servers is not possible due to
missing resource handling implementation in nova.

Use Cases
---------

The owner or the admin needs to be able to resize, migrate, live-migrate,
evacuate and unshelve after shelve offload servers having ports with resource
request.

Servers could be created before Stein with SRIOV ports having QoS minimum
bandwidth policy rule and for them the resource allocation is not enforced in
placement during scheduling. After this spec is implemented the admin will be
able to migrate such servers and the migration will heal the missing port
allocations in placement.

Proposed change
===============

The implementation of the `bandwidth resource provider spec`_ introduced the
``requested_resources`` field in the ``RequestSpec`` versioned object. During
server create this field is populated based on the resource request of the
neutron ports. The nova scheduler generates the allocation candidate query
including the request groups from the ``requested_resources`` field as well.

However this field is not persisted to the database intentionally as the port
resource request is owned and persisted by neutron. So during any operation
that creates a new allocation of an existing server the port resource
request needs to be queried from neutron and the ``requested_resources`` needs
to be populated in the ``RequestSpec`` before the new allocation candidate
query is sent to placement.

After the new allocation is created in placement the ``allocation`` key in the
``binding:profile`` of the neutron port needs to be updated to point to the
new resource provider providing the resources for the port. To figure out
which resource provider fulfills which port's resource request in a given
allocation the already introduced mapping code can be reused.

These move operations are the following:

* resize
* migrate
* live-migrate
* evacuate
* unshelve after the server is shelve offloaded

The generic steps are:

* the server move request reaches the conductor
* the conductor calls query the ports from neutron that are bound to the
  server
* the conductor updates the ``RequestSpec.requested_resources`` field based
  on the resource request of the ports
* the conductor requests select_destination from the scheduler
* the scheduler sends the allocation_candidate query to Placement based on
  ``RequestSpec.requested_resources``, then selects and allocates a candidate
* the conductor updates the port - resource provider mapping in the
  ``RequestSpec`` based on the ``Selection`` object returned from the scheduler
* the conductor requests the move operation from the compute based on the
  ``Selection`` object.
* the target compute updates the port binding in neutron. The ``allocation``
  key in the ``binding:profile`` is also updated based on the mapping in the
  ``RequestSpec`` object.

During resize and migrate the compute manager's ``finish_resize`` call does the
port binding update. But the ``RequestSpec`` is not passed to this call. So
here the RPC API needs to be extended with a new ``request_spec`` parameter.
The ``finish_resize`` is called from source host's ``resize_instance`` call
which does not get the ``RequestSpec`` either so this RPC call also needs to
be extended. Fortunately the ``prep_resize`` call on the destination host
already gets the ``RequestSpec`` so it can call ``resize_instance`` with the
extra parameter.

During confirm resize (and migrate) the source allocation is deleted as today,
no extra step is needed.

During revert resize (and migrate) the allocation is deleted on the
destination host and the source host allocation moved back from the
migration_uuid as consumer to the instance_uuid. No extra step is needed here.
However the port needs to be bound again to the source host and during that
binding the ``allocation`` key of the ``binding:profile`` need to be reverted
too. This means that the mapping needs to be re-calculated based on the
reverted allocation and data from placement. Alternatively we could store the
old mapping in the MigrationContext or start using the multi port binding API
and keep old mapping in the old binding. These alternatives both give extra
complexity to the solution.

During resize to same host the allocations are doubled in placement today. This
will be true for the port related allocation as well.

During evacuate the compute manager's ``rebuild_instance`` call does the port
binding update. This call has a ``request_spec`` parameter so this
RPC API does not need to be extended.

During unshelve of a shelve offloaded instance the compute manager's
``unshelve_instance`` call does the port binding update and here the RPC API
needs to be extended with a new ``request_spec`` parameter.

During live-migrate nova uses the multiple bindings API of neutron to manage
the bindings on the source and the target host in parallel. The conductor
creates the new, inactive binding on the destination host in neutron and it
will add the ``allocation`` key in the new binding according to the
``RequestSpec``. When the live-migrate finishes the source port binding is
deleted along with the source host allocation. If the live-migration is
rolled back the source host binding still have the proper ``allocation`` key
set.

The multiple bindings neutron API extension cannot be turned off so if it is
not present nova can fail the live-migrate operation if ports have resource
request.

Currently these move operations are rejected by nova if the server has ports
attached with resource request. After the above proposed change is implemented
these operations will be allowed. The way we will signal that nova is capable
of supporting these operations is described in the `REST API impact`_ section.

Alternatives
------------

For alternatives of the REST API change see the `REST API impact`_ section.

An alternative implementation could rely on the multiple port binding api of
neutron for all the move operations. In that solution the ``RequestSpec``
object would not need to be passed down to the nova-compute in each move
operations as the inactive binding can be created with the necessary
allocation information in the conductor. However this solution would still
result in nova-compute impact to active the bindings during move instead of
creating a new binding as today.

Data model impact
-----------------

None

REST API impact
---------------

There are two different approaches to signal that nova can handle the move
operations for these servers:

* Introduce a new microversion. If the move operations are requested with an
  older microversion for these servers then the request is rejected in the same
  way as today. If the move operation is requested with the new (or newer)
  microversion the request is accepted and handled properly.

* Consider the missing support for these operations as bugs. Implement the
  above proposed changes as bugfixes without any new microversion. After the
  implementation is done requesting such move operations with any microversion
  is accepted and handled properly.

For background about these options see the `ML thread`_ . On the Train PTG we
`agreed to the bugfix approach`_.


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

As the solution requires RPC changes the move operations can only be supported
after both the source and the destination host are upgraded. So the conductor
needs to ensure that the service version of both compute is high enough. This
can be done similarly to `how conductor checks the service version during live
migration`_. However if the conductor is configured with
``[upgrade_levels]compute=auto`` (e.g. rolling upgrade) then even if both the
source and the destination computes are new enough but there are older computes
in the system then the older RPC version will be used and the ``RequestSpec``
will be stripped from the calls. Therefore an additional check is needed. The
nova-compute needs to check if the instance has ports that would require
mapping and if the ``RequestSpec`` is not provided in the call then fail the
operation.

The support for move operations makes it possible to heal missing or
inconsistent port allocation as during the move the requested resources are
re-calculated and the new allocation created accordingly in placement. This
will complement `the port allocation healing capabilities`_ of the
``nova-manage placement heal_allocations`` CLI that has multiple limitation in
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

Work Items
----------

* Add the RequestSpec to the compute RPC calls in a single step.
* Implement support for each move operation as a separate task.

Dependencies
============

None

Testing
=======

Each move operation will have a functional test asserting that the proper
allocation exists after the move, old allocations are removed, and the port
binding in neutron refers to the appropriate resource provider.

Documentation Impact
====================

The API guide `Using ports with resource request`_ will be updated accordingly.
Also the neutron admin guide `Quality of Service Guaranteed Minimum Bandwidth`_
needs to be updated.

References
==========

* The `bandwidth resource provider spec`_ describing the support for creating
  such servers.
* The documentation of `microversion 2.72`_ introducing the support for
  creating such servers.
* The nova API guide for the existing feature:
  `Using ports with resource request`_
* The neutron admin guide for this feature
  `Quality of Service Guaranteed Minimum Bandwidth`_
* `ML thread`_ about the possible options for the API impact.


.. _`bandwidth resource provider spec`: https://specs.openstack.org/openstack/nova-specs/specs/stein/implemented/bandwidth-resource-provider.html
.. _`microversion 2.72`: https://docs.openstack.org/nova/latest/reference/api-microversion-history.html#maximum-in-stein
.. _`Using ports with resource request`: https://docs.openstack.org/nova/latest/admin/port_with_resource_request.html
.. _`Quality of Service Guaranteed Minimum Bandwidth`: https://docs.openstack.org/neutron/latest/admin/config-qos-min-bw.html
.. _`ML thread`: http://lists.openstack.org/pipermail/openstack-discuss/2019-January/001881.html
.. _`the port allocation healing capabilities`: https://review.openstack.org/#/c/637955
.. _`how conductor checks the service version during live migration`: https://github.com/openstack/nova/blob/e25d59078e61fe9f925dbef53dfe88e575d34dab/nova/conductor/tasks/live_migrate.py#L281-L282
.. _`agreed to the bugfix approach`: http://lists.openstack.org/pipermail/openstack-discuss/2019-May/005807.html


History
=======


.. list-table:: Revisions
   :header-rows: 1

   * - Release Name
     - Description
   * - Train
     - Introduced
