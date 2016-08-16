..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

================
Get Me a Network
================

https://blueprints.launchpad.net/nova/+spec/get-me-a-network

Neutron added the ``auto-allocated-topology`` API in Mitaka [1]_. Nova intends
on using this API to automatically allocate a private network for a project
when creating server instance if no specific network is provided in the create
request and none are available to the project. This should also bring some
feature parity for the server create flow between Neutron and the VlanManager
in nova-network. There is still some deployer setup for networking in both
cases, but after that the networking service handles automatically setting up
the network topology for the project.


Problem description
===================

With nova-network, users typically don't specify anything for networking when
creating a simple instance. With Neutron, the project needs to have access to
a network and subnet in Neutron before it can get networking setup for an
instance in Nova.

The point of this change is to reduce the complexity for users to simply boot
an instance and be able to ssh into it without having to first setup
networks/subnets/routers in Neutron and then specify a nic when booting the
instance.

Use Cases
---------

As an end user, I want to create an instance in Nova and have networking
automatically allocated for my project so I can ssh into the instance once it's
active.

Proposed change
===============

Nova will add a microversion to the API which requires a specific nic value
when creating an instance.

How create server requests work today with Neutron
--------------------------------------------------

Currently a user can create an instance and specify the following networking
values with Neutron as the network API in Nova:

#. Request a specific fixed IP.
#. Request a specific port (or ports).
#. Request a specific network (or duplicate networks as of Juno [2]_).
#. Request a specific fixed IP and network (Nova will create a port in that
   network and use the fixed IP address).
#. Not providing anything on the create request.

You cannot request a fixed IP and a port together because the port already has
a fixed IP associated with it. When requesting a specific port, the network
that the port is in is implied in the create request.

In the last case (nothing is requested), Nova will attempt to lookup an
available network to use by searching for:

#. A private network for the project.
#. A public (shared=True) network.

If this search results in more than one network, then it results in an
ambiguous network error.

There is also existing behavior in Nova where you can create an instance with
no networking when the user does not provide a specific network to use and the
project does not have access to a network in Neutron. This is not an error
since you can later attach a network with the os-attach-interfaces API.

How create server requests will work with auto-allocation
---------------------------------------------------------

The **networks** object in the create server request will now be either a list
or an enum with the following values:

1. auto:

  * This means auto-allocate the network for me if one is not available to the
    project. For nova-network this is the default and existing behavior with
    the VlanManager. For Neutron this means using the
    ``auto-allocated-topology`` API.
  * The 'auto' value cannot be used when specifying a port uuid because a port
    implies a network that the project would already have access to.

  .. note:: Specifying 'auto' means Nova will do it's best to auto-allocate
            the network for the instance. This is not a guarantee that it will
            work since there is initial setup required from the cloud operator
            to enable this functionality (which is also true of nova-network).
            See `Other deployer impact`_ for details.

2. none:

  * This means do not even attempt to setup networking. The compute manager
    will avoid network API calls when creating the server instance. Any
    networking needed for the instance will have to be attached later.

Internally the 'auto' or 'none' value will be stored in the
nova.objects.network_request.NetworkRequest.network_id field.

**Error Conditions**

* If nothing is specified on the request for networks, a 400 will be returned.
* Specifying 'auto' with any other network values (ports, 'none', 'auto' or a
  specific network uuid) results in a 400 response.
* Specifying 'none' with any other network values (ports, 'auto' or a specific
  network uuid) results in a 400 response.
* If 'auto' is specified and nova-network fails to provide networking, fail the
  instance build request (which may trigger a reschedule to another compute
  node).
* If 'auto' is specified, and Nova can determine during the lifecycle of the
  API request that it cannot honor auto-allocating the network, a 400 is
  returned. If auto-allocation fails after the API request has returned, the
  instance is sent to ERROR state.
* Another failure scenario would be that Neutron is new enough and is setup
  to support auto-allocated-topology, but the deployment still has compute
  nodes that are not running the allocation code for creating the network
  resources automatically. Because of this, we will have to restrict the
  ability to use the new microversion with 'auto' or 'none' values for network
  uuid to when all of the compute services are running the version that adds
  that support.

  If 'auto' or 'none' is requested but the minimum compute service version is
  not high enough, the API will act as if networks were not requested. This
  means:

    * A request of 'auto' changing to None: the instance will get networking
      if there is a network available to the project, which is how it works
      today. If there are no networks available, then the instance will not
      have a network.
    * A request of 'none' changing to None: this is basically the same as the
      None case above - there is no way to explicitly request that no networks
      are setup today. This may come as a surprise to anyone requesting 'none'
      and then they get networking, but this is considered an edge case. We
      could fail the request but since we require that something is requested
      for networking in this microversion, the only recourse the user has is to
      specify a lower microversion with no networks but they may still end up
      with networking so it's no better.

  Once all of the computes are upgraded to a Newton version that supports
  auto-allocation from the compute node, then the request will be honored, i.e.
  we will have a chance to call the ``auto-allocated-topology`` API in Neutron.

Compute API changes
-------------------

The compute API calls the network API to validate the request. There will need
to be changes for the network API validation code to handle the 'auto' and
'none' cases for the network uuid.

In the case of 'none', the validation is simply a no-op since the compute
manager will not allocate networks when building the instance.

In the case of 'auto' and the Neutron API, if the project has no available
network to use, then validate that:

* The ``auto-allocated-topology`` extension is available in the Neutron API.
  Note that the ``auto-allocated-topology`` extension is not optional in
  Neutron so as long as the version of Neutron is new enough to have the API,
  the extension will be available and enabled.
* The ``auto-allocated-topology`` Neutron API passes with the *dry-run* option
  which checks that there is a default public external network and default
  subnet pool to use. If that setup is not ready, the API returns a 409 error
  which Nova will raise back to the user as a 400 error.

In the case of 'auto' and nova-network, the validation is a no-op since we will
not know if networking will be provided until we get to the compute node to
build the instance and allocate the network.

We will also have to check that when 'auto' or 'none' is requested that the
minimum compute service version in the deployment supports auto-allocation.
This check could be removed in Ocata when all of the computes should be at
at least running Newton code.

Network API changes
-------------------

The nova.objects.NetworkRequestList that is passed to the network API's
``allocate_for_instance`` method should contain enough information for the
network API to handle the 'auto' and 'none' cases.

The nova.objects.NetworkRequest.network_id field is a nullable String.
Therefore if the network_id is None, it's the pre-microversion case before
**Get Me a Network**. Otherwise the network_id would have a specific network
uuid, 'auto' or 'none' where 'none' means do not allocate a network.

The NetworkRequest/NetworkRequestList object will likely have some helper
methods for easily determining if the request is for the special 'auto' or
'none' cases.

**nova-network**

The 'auto' case for the nova-network API will be such that the network_id
in the (single-entry) NetworkRequestList will be set to None before it's
passed over RPC to the network manager. This maintains the existing behavior in
the manager when a specific network is not requested when creating the
instance.

**Neutron**

The 'auto' case for Neutron will mean that if there are no available networks
for the project, the ``auto-allocated-topology`` API will be called to create
one. Note that the *port-security-enabled* attribute on the network will be
the default value, which is based on whether or not the 'Port Security'
extension is enabled.

.. note:: There will be a potential for races on the compute node when
          auto-allocating the network in Neutron, especially when creating
          multiple instances with a single server creat request. This is a
          one-time operation per project so the first server create for a
          project that requests auto-allocation will create the network. If
          concurrent requests for the same project are made, Neutron has a
          rollback mechanism in place based on a unique constraint for the
          project_id in the ``auto_allocated_topologies`` table. So a second
          concurrent request should fail and be rolled back, but the API will
          return the network that was already created for that project. In
          other words, the provisioning call is idempotent and in case of
          concurrent requests the first one committing the request wins. Nova
          is not required to implement any retry mechanism.

Alternatives
------------

Two alternatives have been discussed in the
`microversion thread in the openstack-dev ML`_ and an
`operator feedback thread`_:

#. If no network info is provided at boot and none are available, don't provide
   a network (existing behavior). If the user wants a network auto-allocated,
   they have to specify ``--nic net-id=auto``.

   In this case the user has to opt into auto-allocating the network.

#. If no network info is provided at boot and none are available, Nova will
   attempt to auto-allocate the network from Neutron. If the user
   specifically does not want networking on instance create (for whatever
   reason), they have to opt into that behavior by specifying
   ``--nic net-id=none``.

   This is closer in behavior to how booting an instance works with
   nova-network, but it is a change in the default behavior for the Neutron
   case, and that is a cause for concern for any users that have written tools
   to expect that default behavior.

Ultimately it was decided that it is best to require API users to be explicit
in the request with what they want (auto/none/uuid). And to make the user
experience better in the CLI, the CLI will default to 'auto' when nothing is
specified (and the server supports the microversion).

Data model impact
-----------------

None

REST API impact
---------------

* A microversion will be added for creating a new server which requires a
  specific value for the network.

  * Method type: POST

  * Normal http response code: 202

  * Expected error http response code(s): 400, 403

  * URL for the resource

    * http://host:8774/v2.1/project_id/servers

  * JSON schema definition for the request body data if allowed

    * The server create API schema will be more restrictive with the
      **networks** object which must be a list or enum with value 'auto' or
      'none'.

    ::

        'type': 'object',
        'properties': {
            'server': {
                'type': 'object',
                'properties': {
                    'name': parameter_types.name,
                    'imageRef': parameter_types.image_ref,
                    'flavorRef': parameter_types.flavor_ref,
                    'adminPass': parameter_types.admin_password,
                    'metadata': parameter_types.metadata,
                    'networks': {
                        'oneOf': [
                            {'type': 'array',
                             'items': {
                                'type': 'object',
                                 'properties': {
                                    'fixed_ip': parameter_types.ip_address,
                                    'port': {
                                        'oneOf': [{'type': 'string', 'format': 'uuid'},
                                                  {'type': 'null'}]
                                    },
                                    'uuid': {'type': 'string', 'format': 'uuid'},
                                },
                                'additionalProperties': False,
                            },
                           },
                           {'type': 'string', 'enum': ['none', 'auto']},
                        ]
                    }
                },
                'required': ['name', 'flavorRef', 'networks'],
                'additionalProperties': False,
            },
        },
        'required': ['server'],
        'additionalProperties': False,

    .. note:: The requested network uuid is not currently required to be a
      strict uuid because of some legacy behavior in the original Neutron v1
      API which didn't enforce network IDs to be uuids and would allow IDs
      with a *br-* prefix. With the proposed schema change, a requested network
      uuid must be a strict uuid value, the *br-* prefix will no longer be
      supported and will result in an error if specified.

  * JSON schema definition for the response body data if any

    * This does not change from how the server create API works today.

**Examples**

* Booting a server with a specific network uuid:

::

    REQ: curl -g -i -X POST \
    http://localhost:8774/v2.1/812d057b80bf42fdb7db62d68f3c6983/servers \
    -H "User-Agent: python-novaclient" -H "Content-Type: application/json" \
    -H "Accept: application/json" -H "X-OpenStack-Nova-API-Version: 2.26" \
    -H "X-Auth-Token: {SHA1}0ecb2c6e137a5bd778b5561fd9dc48a0919f85a5" \
    -d '{"server": {"name": "net-uuid-test", \
    "imageRef": "883db132-0312-411c-b546-5cad477864c6", "flavorRef": "1", \
    "max_count": 1, "min_count": 1, \
    "networks": [{"uuid": "c92eed77-c1c0-498f-8729-c0f4c21796e5"}]}}'

* Booting a server with the 'auto' network ID:

::

    REQ: curl -g -i -X POST \
    http://localhost:8774/v2.1/812d057b80bf42fdb7db62d68f3c6983/servers \
    -H "User-Agent: python-novaclient" -H "Content-Type: application/json" \
    -H "Accept: application/json" -H "X-OpenStack-Nova-API-Version: 2.26" \
    -H "X-Auth-Token: {SHA1}0ecb2c6e137a5bd778b5561fd9dc48a0919f85a5" \
    -d '{"server": {"name": "net-auto-test", \
    "imageRef": "883db132-0312-411c-b546-5cad477864c6", "flavorRef": "1", \
    "max_count": 1, "min_count": 1, "networks": "auto"}}'

* Booting a server with the 'none' network.

::

    REQ: curl -g -i -X POST \
    http://localhost:8774/v2.1/812d057b80bf42fdb7db62d68f3c6983/servers \
    -H "User-Agent: python-novaclient" -H "Content-Type: application/json" \
    -H "Accept: application/json" -H "X-OpenStack-Nova-API-Version: 2.26" \
    -H "X-Auth-Token: {SHA1}0ecb2c6e137a5bd778b5561fd9dc48a0919f85a5" \
    -d '{"server": {"name": "net-none-test", \
    "imageRef": "883db132-0312-411c-b546-5cad477864c6", "flavorRef": "1", \
    "max_count": 1, "min_count": 1, "networks": "none"}}'


Security impact
---------------

None; there is nothing new about this that a user could not already do, this
just adds some convenient orchestration behind the covers so the user does not
have to setup networking in Neutron before they get to create a server instance
in Nova.

Notifications impact
--------------------

None

Other end user impact
---------------------

The Nova REST API will require that a **networks** value is specified.

However, the CLI will default to 'auto' if no nics are requested in the
``boot`` command and the server can support the new microversion (and the user
is not specifying a lower microversion).

Performance Impact
------------------

Anytime Nova is calling Neutron there is additional overhead. There will be
two additional checks in the compute API for the network request validation
in the case that 'auto' is specified and there are no available existing
networks for the project:

1. That the ``auto-allocated-topology`` extension is available. The extensions
   are already cached in nova.network.neutronv2.api.API so this should be
   minimal overhead.
2. That the ``auto-allocated-topology`` API passes the *dry-run* validation
   check. This is a one-time cost per tenant since after the first time a
   network is auto-allocated by Neutron for the tenant, subsequent checks for
   available networks will find the previously allocated network and we won't
   need to check the ``auto-allocated-topology`` API for that tenant, unless
   the tenant network was deleted for some reason.


.. note:: Nova could offset the cost of doing this validation with Neutron by
          caching positive results using something like oslo.cache with an
          expiration timer (maybe re-validate every hour). "Positive" results
          in this case means only cache the result when the validation passes
          so we don't hit a case where validation fails, we cache that result,
          the admin fixes the problem, then the next request fails on the
          cached result even though things should be passing (and then the user
          has to wait for the cached value to expire).

Other deployer impact
---------------------

For the automatic network allocation to work with Neutron, the following must
happen:

* The ``auto-allocated-topology`` extension must be enabled in the Neutron API.
* Ensure the public external network is the default external network.
* The deployment must contain a default subnet pool: one ipv4 pool, or one ipv6
  pool, or one of each. The ``subnet_allocation`` extension is required for
  this.

See the `Networking Guide`_ for more details.

There is a devstack change to enable this also which can be used as a
reference. [3]_

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

* REST API changes in Nova for the microversion and auto/none/uuid logic.
* API changes to check that the minimum compute service version in the
  deployment is at least the version that adds the auto-allocation logic to
  the compute service, which includes the network API. This check can be
  removed in Ocata.
* Updates in the compute API to not call network_api.validate_networks if
  NetworkRequest.network_id == 'none'.
* Updates to nova.network.neutronv2.api.API.validate_networks method for the
  'auto' case when no networks are requested and none are available. Also
  potentially caching the results of the validation with Neutron.
* Updates to the compute manager to not call allocate_for_instance if
  network_id is 'none'. This is simpler to do in one spot in the compute
  manager than in both allocate_for_instance methods in each network API,
  especially when we have to cast to the network manager in the case of
  nova-network.
* Updates to nova.network.api.API.allocate_for_instance to fail if no network
  info is allocated and NetworkRequest.network_id == 'auto'.
* Updates to nova.network.neutronv2.api.API.allocate_for_instance to
  auto-allocate a network if none are specified and none are available for the
  project.
* Updates to python-novaclient to handle the new microversion and if no nics
  are requested and the microversion will be satisfied, default to pass 'auto'
  to the Nova REST API.
* Unit tests for all changes.
* Functional tests for the REST API microversion changes.
* Tempest tests for the full end-to-end scenario with Nova / Neutron.

The Nova changes will be made in the following order so we can test the HEAD of
the branch with the Tempest changes:

#. Network API changes.
#. Compute API/manager changes.
#. REST API changes. This is what the Tempest change will depend on. If this is
   not passing tests, then something is wrong in the stack of changes and we
   cannot land any of them until the REST API changes are passing tests.


Dependencies
============

* The Neutron API changes defined in the get-me-a-network spec. [1]_ This was
  implemented in Mitaka.
* Devstack changes for Tempest testing. [3]_ This was implemented in Mitaka.
* The python-neutronclient python API changes for auto-allocated-topology. [4]_
  This was implemented in Mitaka and available in the 4.1.0 release of
  python-neutronclient.


Testing
=======

Unit tests
----------

Unit tests for anything and everything.

Functional tests in Nova
------------------------

Will add tests for the WSGI / microversion changes and negative scenarios.

Negative tests include:

* Specifying 'auto' or 'none' and a specific network_id/fixed_ip/port-uuid.
* Not specifying anything for network after the microversion.
* Specifying 'auto' or 'none' before the microversion (v2.1).

Tempest tests
-------------

* Microversion testing after the microversion using the 'auto' value.
* Testing with 'auto' and 'none' for nova-network and Neutron.

  * nova-network + auto: should work as it does today in the gate
  * nova-network + none: verify that no networking is allocated (this could
    also be tested with a functional test in Nova, but it should work the
    same regardless of which networking service is being used so it might be
    fine in Tempest too).
  * neutron + auto: should allocate a network for the project when booting
    an instance. This can only work when the ``auto-allocated-topology``
    extension is enabled in Neutron. It also requires the default public
    network and subnet pool setup so this will require a feature toggle in
    Tempest (devstack enables this already so it will work in the gate jobs).

    * Should also test that a second boot with the same project using 'auto'
      doesn't auto-allocate a new unique network, it should re-use the same one
      from the first request.
    * We should also test booting multiple instances from the same project
      using 'auto' and make sure it's atomic.


Documentation Impact
====================

* API: http://developer.openstack.org/api-ref/compute/#create-server
* CLI: http://docs.openstack.org/cli-reference/nova.html#nova-boot

References
==========

.. [1] http://specs.openstack.org/openstack/neutron-specs/specs/mitaka/get-me-a-network.html
.. [2] https://blueprints.launchpad.net/nova/+spec/multiple-if-1-net
.. [3] https://review.openstack.org/#/c/282559/
.. [4] https://review.openstack.org/#/c/272842/

.. _microversion thread in the openstack-dev ML: http://lists.openstack.org/pipermail/openstack-dev/2016-February/086437.html
.. _operator feedback thread: http://lists.openstack.org/pipermail/openstack-operators/2016-February/009637.html
.. _Networking Guide: http://docs.openstack.org/networking-guide/intro-os-networking-features.html


History
=======

.. list-table:: Revisions
   :header-rows: 1

   * - Release Name
     - Description
   * - Newton
     - Introduced
   * - Newton
     - Amended for auto/none as enum `design change`_.

.. _design change: http://lists.openstack.org/pipermail/openstack-dev/2016-August/101499.html
