..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

==========================================
Get valid server state
==========================================

https://blueprints.launchpad.net/nova/+spec/get-valid-server-state

When a compute service fails, the power states of the hosted VMs are not
updated. A normal user querying his or her VMs does not get any indication
about the failure. Also there is no indication about maintenance.

Problem description
===================

VM query do not give needed information to the user about a compute host that
is failed/unreachable, nova-compute service that is failed/stopped or
nova-compute service that is explicitly marked as failed or disabled. The user
should get the information about nova-compute state when querying his or her
VMs to get better understanding about the situation.

Use Cases
---------

As a user I want to be able to have accurate VM state information even when the
compute service fails or host is down, so I can do quick actions for my VMs.
Mostly the failure information is critical to a user having HA type of VMs that
needs to make a quick switch over for service. Other thing is for user or admin
to do something for the VMs on the host. Action might be case and deployment
specific, as some admin actions can be automated for external service and some
left to user. Normally user can just do just delete or create for a VM.

As a user I want to get information about maintenance, so I can do actions for
my VMs. As user get information about host being in maintenance (service=
disabled), user knows to plan what to do for his or her VMs as host may be
rebooted soon.

Proposed change
===============

A new ``host_status`` field will be added to the ``/servers/{server_id}`` and
``/servers/detail`` endpoints. ``host_status`` will be ``UP`` if nova-compute's
state is up, ``EXTERNALLY_DEFINED_TO_BE_DOWN`` if nova-compute is forced_down,
``UNKNOWN`` if nova-compute last_seen_up is not up-to-date and  ``MAINTENANCE``
if nova-compute's state disabled. Needed information can be retriewed by host
API and servicegroup API if new policy allows. forced_down flag handling is
described in this spec:
http://specs.openstack.org/openstack/nova-specs/specs/liberty/implemented/mark-host-down.html

A new policy element will be added to control access to ``host_status``. This
can be used both to prevent this host-based data being disclosed as well as to
eliminate the performance impact of this feature.


Alternatives
------------

When returning the VM power_state, check the service status for the host. If
the service is ``forced_down``, return ``UNKNOWN`` instead. This would be an
API-only change, it is NOT proposed that we update the DB value to
``UNKNOWN``. This means we retain a record of the VM power state independent
of the service state, which may be interesting in case the host lost network
rather than power. Community feedback indicated that as the power_state is only
true for a point in time anyway, technically the state is always ``UNKNOWN``.

``os-services/force-down`` could mark all VMs managed by the affected service
as ``UNKNOWN`` in db. This would sometimes be wrong as a VM can be up even if
its host is unreachable. This would make also a need to remove this state data
in case VM evacuated to another compute node.

A possible extension is a host ``NEEDS_MAINTENANCE`` state, which would show
that maintenance is required soon. This would allow users who monitor this info
to prepare their VMs for downtime and enter maintenance at a time convenient
for them.

An extension could be added for filtering ``/servers`` and ``/servers/detail``
endpoints response message by ``host_status``.

Data model impact
-----------------

None

REST API impact
---------------

GET ``/v2.1/{tenant_id}/servers/{server_id}`` and ``/v2.1/{tenant_id}/servers/
detail`` will return ``host_status`` field if "os_compute_api:servers:show:
host_status" policy is defined for the user. This will require a microversion.

Case where nova-compute enabled and reporting normally::

    GET /v2.1/{tenant_id}/servers/{server_id}

    200 OK
    {
      "server": {
        "host_status": "UP",
        ...
      }
    }

Case where nova-compute enabled, but not reporting normally::

    GET /v2.1/{tenant_id}/servers/{server_id}

    200 OK
    {
      "server": {
        "host_status": "UNKNOWN",
        ...
      }
    }

Case where nova-compute enabled, but forced_down::

    GET /v2.1/{tenant_id}/servers/{server_id}

    200 OK
    {
      "server": {
        "host_status": "EXTERNALLY_DEFINED_TO_BE_DOWN",
        ...
      }
    }

Case where nova-compute disabled::

    GET /v2.1/{tenant_id}/servers/{server_id}

    200 OK
    {
      "server": {
        "host_status": "MAINTENANCE",
        ...
      }
    }

This may be presented by python-novaclient as::

  +-------+------+--------+------------+-------------+----------+-------------+
  | ID    | Name | Status | Task State | Power State | Networks | Host Status |
  +-------+------+--------+------------+-------------+----------+-------------+
  | 9a... | vm1  | ACTIVE | -          | RUNNING     | xnet=... | UP          |
  +-------+------+--------+------------+-------------+----------+-------------+

New policy element to be added to allow assigning permission to see
host_status:

::

  "os_compute_api:servers:show:host_status": "is_admin:True or
  user_id:%(user_id)s"


Security impact
---------------

Normal users may be able to correlate host states across multiple VMs to draw
conclusions about the cloud topology. This can be prevented by not granting the
policy.

Notifications impact
--------------------

None

Other end user impact
---------------------

None

Performance Impact
------------------

An additional database query will be required to look up the service when a
server detail request is received.

Other deployer impact
---------------------

None

Developer impact
----------------

None

Implementation
==============

Assignee(s)
-----------

Primary assignee:   Tomi Juvonen
Other contributors: None

Work Items
----------

* Expose host_status as detailed.
* Update python-novaclient.

Dependencies
============

None

Testing
=======

Unit and functional test cases needs to be added.

Documentation Impact
====================

API change needs to be documented:

* Compute API extensions documentation.
  http://developer.openstack.org/api-ref-compute-v2.1.html

References
==========

* https://blueprints.launchpad.net/nova/+spec/mark-host-down
* OPNFV Doctor project: https://wiki.opnfv.org/doctor
