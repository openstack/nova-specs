..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.
 http://creativecommons.org/licenses/by/3.0/legalcode

===========================================
New nova API call to mark nova-compute down
===========================================

https://blueprints.launchpad.net/nova/+spec/mark-host-down

New API call is needed to change the state of nova-compute service down
immediately. This allows usage of evacuate API without a delay. Also as
external system calling the API will make sure no VMs left running, there
will be no possibility to break shared storage or use same IPs again. API
usage applies mainly for cases where there is single host mapped to
nova-compute. Cases like in Ironic or vSphere would be out of scope.

Problem description
===================

Nova-compute state change for failed or unreachable host is slow and does
not reliably state host is down or not. Evacuation cannot happen fast and
as VMs might still be running, it might lead to reusing same IPs and to data
corruption in case of shared storage. Also there can be an impact on cloud
stability due to ability to schedule VMs on failed host.

Use Cases
----------

As a user I want to fast evacuate VMs in case nova-compute down.

As a user I want to trust VMs will be scheduled to a healthy compute node.

As a user I want to trust no VMs are left running in case nova-compute is
reported down. This can be the case if external system can mark nova-compute
down when notice fault, so it can be trusted that also the corresponding
VMs are really down.

As a deployer I want to deploy external fault monitoring system that can
detect different problems that can be translated as host fault to be informed
to OpenStack and make sure that host is fenced (powered down). Monitoring
system could monitor interfaces, links, services, memory, CPU, HW, hypervisor,
OpenStack services,... and make actions accordingly.

Project Priority
-----------------

Liberty priorities have not yet been defined.

Proposed change
===============

Introducing new services API extensions for setting the power state to up or
down of the nova-compute.

As future work there could be other BP made related to this:

* New notification of service state change.

Related to instances running on host there could also be BPs made:

* There could be an API to set 'power_state: shutdown' for all VMs related to
  a single host.
* Currently there is an API to reset VM state one by one. There could be an
  API to have the same for all VMs related to a single host.

Alternatives
------------

There is no attractive alternatives to detect all different host faults than
to have a external tool to detect different host faults. For this kind of tool
to exist there needs to be new API in Nova to report fault. Currently there
must have been some kind of workarounds implemented as cannot trust or get the
states from OpenStack fast enough.

Data model impact
-----------------

Nova DB service table will have a new Boolean column ``forced_down`` with false
as default value. Database servicegroup driver ``is_up`` method needs to be
updated to use this to determine service state is down in case value is true.
Otherwise current timestamp based usage is expected. Only when ``forced_down``
flag will be set back to false will nova-compute be allowed to come up and
have the state reported up.

REST API impact
---------------

New compute API to change nova-compute ``forced_down`` flag value to true or
false:

  request::

      PUT /v2.1/{tenant_id}/os-services/force-down
      {
          "binary": "nova-compute",
          "host": "host1",
          "forced_down": true
      }

  response::

      200 OK
      {
          "service": {
              "host": "host1",
              "binary": "nova-compute",
              "forced_down": true
          }
      }

  request::

      PUT /v2.1/{tenant_id}/os-services/force-down
      {
          "binary": "nova-compute",
          "host": "host1",
          "forced_down": false
      }

  response::

      200 OK
      {
          "service": {
              "host": "host1",
              "binary": "nova-compute",
              "forced_down": false
          }
      }

Service schema will have new optional parameter:

``forced_down``: parameter_types.boolean

This will be in response messages to forced_down requests.

Besides new call, response for list of services will also contain information
about state of forced_down field.

Security impact
---------------

Configurable by policy, defaulting to admin role.

Notifications impact
--------------------

None

Other end user impact
---------------------

None

Performance Impact
------------------

None

Other deployer impact
---------------------

Deployer can make use of any external system to detect host fault and report it
to OpenStack.

Developer impact
----------------

None

Implementation
==============

Assignee(s)
-----------

Primary assignee:   Tomi Juvonen
Other contributors: Ryota Mibu, Roman Dobosz

Work Items
----------

* Test cases.
* REST API and Service changes.
  Implementation: https://review.openstack.org/#/c/184086/
* CLI API changes.
* Documentation.

Dependencies
============

None.

Testing
=======

Unit and functional test cases needs to be added.

Documentation Impact
====================

New API needs to be documented:

* Compute API extensions documentation.
  http://developer.openstack.org/api-ref-compute-v2.1.html
* nova.compute.api documentation.
  http://docs.openstack.org/developer/nova/api/nova.compute.api.html

References
==========
* OPNFV Doctor project: https://wiki.opnfv.org/doctor
* OpenStack Instance HA Proposal:
  http://blog.russellbryant.net/2014/10/15/openstack-instance-ha-proposal/
* The Different Facets of OpenStack HA:
  http://blog.russellbryant.net/2015/03/10/the-different-facets-of-openstack-ha/
