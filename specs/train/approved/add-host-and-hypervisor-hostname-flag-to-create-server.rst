..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

======================================================
Add host and hypervisor hostname flag to create server
======================================================

https://blueprints.launchpad.net/nova/+spec/add-host-and-hypervisor-hostname-flag-to-create-server

When admin users specify the `forced_host/forced_node`_ to create servers,
nova will bypass the scheduler filters. This spec proposes to add two new
params ``host`` and ``hypervisor_hostname`` as specified host and/or node to
create servers without bypassing the scheduler filters in a new REST API
microversion.


Problem description
===================

When admin users specify the `forced_host/forced_node`_ to create servers,
nova will bypass the scheduler filters.

* Without scheduler filters, failure instances may waste effort trying to boot
  when failure is inevitable because of network provider, PCI device, NUMA
  topology, etc.
* We could be trying to claim resources on the host that aren't available,
  and/or unintentionally over-subscribing the host because without running
  the filters we don't pass down any limits for the resource claim.

Use Cases
---------

This change adds the following use case to the system:

* An admin wants to request that a server is created on a specified compute
  host and/or node and have the request validated by the scheduler filters
  rather than forced.

Proposed change
===============

* Add ``host`` and ``hypervisor_hostname`` to the REST API ``POST /servers``.
* Add a new policy ``os_compute_api:servers:create:requested_destination`` to
  limit ``host`` and ``hypervisor_hostname`` only for admin.
* Translate ``host`` and ``hypervisor_hostname`` to a
  RequestSpec.requested_destination which still goes through the scheduler
  filters.

.. note::

  We still leave the old mechanism ``az:host:node`` in this new microversion
  so users have the option of either forcing the target during server creates
  or requesting the target.

Alternatives
------------

There is a filter named `JsonFilter`_ which is not used by default. This
filter allows simple JSON-based grammar for selecting hosts. If we want to
specify the host named "openstack-node", we can add the params like this:
``--hint query='["=","$host","openstack-node"]'``.

In addition to the warnings in the documentation for this filter, if it is
configurable, it may not be present in all clouds and thus can not be
guaranteed for interoperability.

There is a filter named `AggregateInstanceExtraSpecsFilter`_ which is not used
by default. This filter checks that the aggregate metadata satisfies any extra
specifications associated with the instance type (that have no scope or are
scoped with ``aggregate_instance_extra_specs``). If we want to specify the
host named "openstack-node", we can create a aggregate named "test-ag01"
include host "openstack-node". Then we set metadata for this aggregate with
``host=openstack-node``. At last, we create a flavor and set metadata for
this flavor with ``aggregate_instance_extra_specs:host=openstack-node``. So
when we choose the flavor to create instances, all will be on the host
"openstack-node".

In this case, creating an aggregate and flavor pinned to that aggregate for
every host/node in a large cloud is not manageable and would also potentially
leak deployment details about the cloud, and also confuse users when we have
so many availability zones to model those aggregates. It's just not a
realistic option for this use case in a large cloud.

.. _JsonFilter: https://docs.openstack.org/nova/latest/admin/configuration/schedulers.html#jsonfilter
.. _AggregateInstanceExtraSpecsFilter: https://docs.openstack.org/nova/latest/admin/configuration/schedulers.html#aggregateinstanceextraspecsfilter

Data model impact
-----------------

None

REST API impact
---------------

In a new microversion add the ``host`` and ``hypervisor_hostname`` flag
to the API, both of them are optional:

* POST /servers

::

    {
        "server": {
            ...
            "host": "openstack-node",
            "hypervisor_hostname": "openstack-node"
        }
    }

Only show new parameters' JSON schema definition for body data of ``server``:

::

  'host': parameter_types.hostname
  'hypervisor_hostname': parameter_types.hostname

Depending on whether/how the ``host`` and ``hypervisor_hostname`` is set,
the actions are as followed:

- If ``host`` is supplied in the request body, at first Compute API will check
  whether we can fetch a compute node for this ``host`` from DB. If not, an
  ``HTTP 400 Bad Request`` will be returned to users.

- If ``hypervisor_hostname`` is supplied in the request body, at first
  Compute API will check whether we can fetch a compute node for this
  ``hypervisor_hostname`` from DB. If not, an ``HTTP 400 Bad Request`` will
  be returned to users.

- If both ``host`` and ``hypervisor_hostname`` are supplied in the request
  body, at first Compute API will check whether we can fetch a compute node
  for ``host`` and ``hypervisor_hostname`` from DB. If not, an
  ``HTTP 400 Bad Request`` will be returned to users.

.. note::

  The new (``host`` and/or ``hypervisor_hostname``) and the old
  (``az:host:node``) mechanisms are mutually exclusive. If both are specified
  in the same request, the API will return an HTTP 400 Bad Request.

Security impact
---------------

None

Notifications impact
--------------------

None

Other end user impact
---------------------

Update python-novaclient and python-openstackclient to support the new
microversion.

Performance Impact
------------------

None

Other deployer impact
---------------------

None

Developer impact
----------------

None

Upgrade impact
--------------

None


Implementation
==============

Assignee(s)
-----------


Primary assignee:
  Boxiang Zhu (zhu.boxiang@99cloud.net)

Work Items
----------

* Add new microversion for this change.


Dependencies
============

None


Testing
=======

* Functional and unit test will be provided.
* Some scenarios (Create a server on a requested host and/or node and then
  move it - live migrate, evacuate, cold migrate and unshelve - to make sure
  it moves to another host and isn't restricted to the original requested
  destination) will be provided.

Documentation Impact
====================

* The API document should be changed to introduce this new feature.

References
==========

.. _forced_host/forced_node: https://docs.openstack.org/nova/latest/admin/availability-zones.html

* Train PTG etherpad: https://etherpad.openstack.org/p/nova-ptg-train


History
=======

.. list-table:: Revisions
   :header-rows: 1

   * - Release Name
     - Description
   * - Train
     - Introduced
