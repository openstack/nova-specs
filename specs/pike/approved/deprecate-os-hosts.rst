..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

==========================
Deprecate the os-hosts API
==========================

`<https://blueprints.launchpad.net/nova/+spec/deprecate-os-hosts>`_

Much of the ``os-hosts`` API is duplicated with the ``os-services`` and
``os-hypervisors`` APIs. Other parts are not implemented for all backends, or
even a good idea for Nova to have in the compute API. Other parts are not even
implemented for any backend anywhere. This spec proposes to deprecate the API
altogether.

Problem description
===================

The ``os-hosts`` and ``os-services`` APIs are very similar, and they work on
the same resources (the `services` records in the nova database). Specifically
``PUT /os-hosts/{host_name}`` compared to ``PUT /os-services/disable`` and
``PUT /os-services/enable``.

Both APIs allow you to list services and show details for a specific host
(compute node).

The ``os-hosts`` and ``os-hypervisors`` APIs are also similar in that they
work on the same resources (the `compute_nodes` records in the nova database).
Specifically ``GET /os-hosts`` and ``GET /os-hosts/{host_name}`` compared to
``GET /os-hypervisors`` and ``GET /os-hypervisors/{hypervisor_id}``.

Both APIs allow you to enable and disable a service so instances will not be
scheduled to that service (compute host).

There are some additional action APIs that are specific to the ``os-hosts``
API:

1. Putting the service (host) into maintenance mode. This is only implemented
   by the XenServer virt driver and despite the description in the support
   matrix [1]_ it has been reported that it does not actually evacuate
   all of the guests from the host, it just sets a flag in the Xen management
   console, and is therefore pretty useless. Regardless, we have other APIs
   that allow you to do the same thing which are supported across all virt
   drivers, which would be disabling a service and then migrating the instances
   off that host.

2. Reboot host. This is only supported by the XenServer and Hyper-v drivers.
   This is also arguably something that does not need to live in the compute
   API. The backing drivers do no orchestration of dealing with guests in the
   nova database when performing a reboot of the host. The compute service for
   that host may be temporarily disabled by the service group health check
   which would take it out of scheduling decisions, and the guests would be
   down, but the periodic task which checks for unexpectedly stopped instances
   runs in the nova-compute service, which might be dead now so the nova API
   would show the instances as running when in fact they are actually stopped.

3. Shutdown host. Same as #2 for reboot host.

4. Start host. This is literally not supported by any in-tree virt drivers. The
   only drivers that implement the `host_power_action` method are XenServer and
   Hyper-v and they do not support the `startup` action. Since this is an RPC
   call from nova-api to nova-compute, you will at least get a 501 error
   response indicating it is not supported or implemented (even though 501 is
   the wrong response for something like this).

Use Cases
---------

As an admin, I want to use a single, consistent API for managing services in my
Nova deployment (os-services).

As an admin, I want to use a single, consistent API for managing compute nodes
in my Nova deployment (os-hypervisors).

As a developer, I do not want to support duplicate APIs or things that should
live outside of Nova, like code that reboots or stops an entire compute host or
hypervisor. This is especially annoying in a multi-cell cells v2 world where
we have to make sure there is a unique identifier in the API to target a unique
resource in any given cell (see [2]_ for details).

Proposed change
===============

In a microversion, deprecate all methods in the ``os-hosts`` API controller
such that requests at that microversion or later will result in a 404 NotFound
error.

Alternatives
------------

None

Data model impact
-----------------

None

REST API impact
---------------

With a new microversion, any requests at that microversion or later to the
``os-hosts`` API will result in a 404 NotFound response.

These are the specific APIs:

* ``GET /os-hosts`` - list hosts
* ``GET /os-hosts/{host_name}`` - show host details
* ``PUT /os-hosts/{host_name}`` - update host status
* ``GET /os-hosts/{host_name}/reboot`` - reboot host
* ``GET /os-hosts/{host_name}/shutdown`` - shutdown host
* ``GET /os-hosts/{host_name}/startup`` - start host

Also, yes, those GETs on the power action APIs are not a mistake, they are
actually implemented as GETs.


Security impact
---------------

None

Notifications impact
--------------------

None

Other end user impact
---------------------

The following CLIs and their backing API bindings in python-novaclient will be
deprecated and capped at the new microversion:

* ``nova host-describe`` - superseded by ``nova hypervisor-show``
* ``nova host-list`` - superseded by ``nova hypervisor-list``
* ``nova host-update`` - superseded by ``nova service-enable/disable``
* ``nova host-action`` - no alternative within Nova by design

Performance Impact
------------------

None

Other deployer impact
---------------------

Deployers that were relying on the ``os-hosts`` API for scripts will need to
cap at the microversion or change to use ``os-services`` or ``os-hypervisors``.
If any Xen or Hyper-v admins were using the power action API, they will need
to use something native to those hypervisors. Note when asking about usage of
the API in the openstack-operators mailing list [3]_ no one said they were
using this.

Developer impact
----------------

None


Implementation
==============

Assignee(s)
-----------

Primary assignee:
  Matt Riedemann (mriedem)

Other contributors:
  None

Work Items
----------

* Add the new microversion to deprecate the ``os-hosts`` API methods.
* Cap and deprecate the related CLIs and APIs in python-novaclient.
* Cap, replace or remove any usage of the ``os-hosts`` API in Tempest.


Dependencies
============

None


Testing
=======

Unit tests and in-tree functional tests as normal.

There are some tests in Tempest which rely on the ``os-hosts`` API either
directly for testing the API or indirectly for listing hosts for other test
setup, like with aggregates or live migration testing. The host list and show
operations can be replaced with the ``os-hypervisors`` or ``os-services`` APIs.
The enable/disable/reboot/shutdown/start APIs in ``os-hosts`` are only used
in Tempest negative tests and should arguably be moved out of Tempest and into
the Nova unit tests (which might already exist).


Documentation Impact
====================

The compute API reference documentation for the ``os-hosts`` API will be
updated to mention that the API is documented at the new microversion. We could
also mention the limitations with some of the API, like the power actions only
being implemented by some virt drivers, that they are not tested, and that the
startup action is not implemented at all. Basically, do not use those ever.

References
==========

.. [1] https://docs.openstack.org/developer/nova/support-matrix.html#operation_maintenance_mode

.. [2] https://specs.openstack.org/openstack/nova-specs/specs/pike/approved/service-hyper-uuid-in-api.html

.. [3] http://lists.openstack.org/pipermail/openstack-operators/2017-April/013095.html

History
=======

.. list-table:: Revisions
   :header-rows: 1

   * - Release Name
     - Description
   * - Pike
     - Introduced
