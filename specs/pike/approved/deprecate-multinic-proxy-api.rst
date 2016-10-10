..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

======================================================================
Deprecate multinic, os-virtual-interfaces, and floating IP action APIs
======================================================================

https://blueprints.launchpad.net/nova/+spec/deprecate-multinic-proxy-api

The proxies APIs were deprecated in the `Deprecate API Proxies`_ spec
which resulted in the 2.36 microversion. But the `multinic`,
`os-virtual-interfaces`, `addFloatingIP` and `removeFloatingIP` APIs were
missed in that change. This spec aims to describe the deprecation for them.

Problem description
===================

**multinic**

The neutron implementation of Nova `multinic` API (under
`nova.network.neutronv2.api`) is allocating one new fixed IP address to the
instance's existed interface in the specific network. The user only can input
the network id which is used by existed interface, then the implementation is
going to allocate one fixed IP address from existed subnets in that network.
If there is only one subnet in the network, the new fixed IP address is just
allocated from that subnet. If there are multiple subnets in the network, it
always allocates fixed IP address from the subnet which is the first subnet
item of the response from Neutron list subnets API. There isn't clear use-case
for this semantics. Also, this behavior is just proxy API for the Neutron API.
The user can do the same thing with Neutron API as below::

    # To list all subnets in the specific network
    neutron subnet-list --network-id NETWORK_ID
    # Update the port includes the existed subnet and fixedIP and the new subnet
    neutron port-update --fixed-ip subnet-id=EXISTED_SUBNET_ID,ip_address=EXISTED_IP_ADDRESS --fixed-ip subnet-id=NEW_SUBNET_ID

In the API response of `GET /servers/{uuid}` and `GET /servers/{uuid}/ips`,
there is Fixed IP address info. Due to Neutron will send out `network-changed`
event when the port updated, that info also won't be stale when the user
adds new fixedIP to the instance through Neutron API directly.

**os-virtual-interfaces**

The ``os-virtual-interfaces`` API has a single
``GET /servers/{server_id}/os-virtual-interfaces`` method to list virtual
interfaces for a server. This API is only implemented with nova-network and
results in a 400 error when using Neutron. nova-network has been deprecated
since the 14.0.0 Newton release and though not a proxy to an external service,
we deprecated several network resource APIs with the 2.36 microversion and this
falls under that same category for deprecation.

**addFloatingIP, removeFloatingIP**

The `floatingip actions` API is used to associate a floating IP with the port
interface of an instance. The API supports both nova-network and neutron
backends.
Since nova-network is deprecated, we do not need this API anymore. For neutron,
the API implementation is a kind of proxy of the neutron API.

To associate a floating IP with an instance by `addFloatingIP` API, the end
user needs to do as below::

    neutron floatingip-create EXT_NET_ID
    nova floating-ip-associate FLOATING_IP_ID [--fixed-address FIXED_ADDRESS]

With neutron, the end user needs to do as below::

    neutron floatingip-create EXT_NET_ID
    neutron floatingip-associate FLOATING_IP_ID VM_PORT_ID

    or

    neutron floatingip-create EXT_NET_ID VM_PORT_ID

The instance's floating IP info is also exposed in the Nova API. You can get
an instance's floating IP info from the `addresses` attribute of
`GET /servers/{uuid}` and `GET /servers/{uuid}/ips` APIs. Those instance
floating IP info is read from the instance network cache. If user associate
floating to the instance's interface with Neutron API directly, Neutron will
send `network-changed` event to Nova, then Nova will update specific
instance's network info cache. This is obviously not atomic or fail-safe, and
in the future we may rework the `addresses` field in the server representation
but that is out of scope for this spec.

Use Cases
---------

* As a user, I want to add multiple fixed and/or floating IPs to my server
  instance and do it in a consistent and predictable way.
* As a deployer, I don't want to support broken compute APIs that are poor
  proxies to the networking service.

Proposed change
===============

In a single microversion, deprecate the `multinic`, `os-virtual-interfaces`,
`addFloatingIP` and `removeFloatingIP` APIs.

Requests to these APIs at the deprecation microversion or later will result in
a 404 NotFound response.

Alternatives
------------

Keep these proxies forever. This will increase the cost of the maintenance of
Nova and slow down our ability to adapt to new features and requirements.

Data model impact
-----------------

None

REST API impact
---------------

The following requests with the microversion or later will result in a 404
error response::

  POST /servers/{server_id}/action
  {
    "addFixedIp": {
        "networkId": 1
    }
  }

  POST /servers/{server_id}/action
  {
    "removeFixedIp":{
        "address": "10.0.0.4"
    }
  }

  GET /servers/{server_id}/os-virtual-interfaces

  POST /servers/{server_id}/action
  {
    "addFloatingIp" : {
        "address": "10.10.10.10",
        "fixed_address": "192.168.0.3"
    }
  }

  POST /servers/{server_id}/action
  {
    "removeFloatingIp": {
        "address": "172.16.10.7"
    }
  }

Security impact
---------------

None

Notifications impact
--------------------

None

Other end user impact
---------------------

The python API binding and CLI in python-novaclient for the following commands
will be deprecated and capped under the new microversion:

* ``nova add-fixed-ip``
* ``nova remove-fixed-ip``
* ``nova virtual-interface-list``
* ``nova floating-ip-associate``
* ``nova floating-ip-disassociate``

If the user wants to use these CLIs or APIs, they should request with a version
that is less than the new microversion.

Performance Impact
------------------

None

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

Primary assignee:
   Alex Xu <hejie.xu@intel.com>

Other contributors:
   Matt Riedemann <mriedem.os@gmail.com>

Work Items
----------

The following are all done under a single new microversion:

* Deprecate the `multinic`, `os-virtual-interfaces`, `addFloatingIP` and
  `removeFloatingIP` APIs.
* Deprecate and cap the CLIs and APIs listed in the `Other end user impact`_
  section.

Dependencies
============

None

Testing
=======

There will be in tree functional testing that these APIs do the right thing
after this microversion and return 404s.

For Tempest, the following tests will need to be capped at the new
microversion:

* ``test_add_remove_fixed_ip``
* ``test_associate_disassociate_floating_ip``
* ``test_associate_already_associated_floating_ip``
* ``test_rescued_vm_associate_dissociate_floating_ip``
* ``test_server_basic_ops``
* ``test_minimum_basic_scenario``
* ``test_list_virtual_interfaces``

There may be more tests that need to change in Tempest based on the new
microversion, like negative tests related to the above positive tests. Also,
some of the changes in the scenario tests may have duplicate coverage and could
be consolidated.

Documentation Impact
====================

Update the compute `api-ref`_ documentation to note the deprecation of the
``multinic``, ``os-virtual-interfaces``, ``addFloatingIP`` and
``removeFloatingIP`` APIs.

References
==========

.. _Deprecate API Proxies: ../../newton/implemented/deprecate-api-proxies.html
.. _api-ref: http://developer.openstack.org/api-ref/compute/

History
=======

.. list-table:: Revisions
   :header-rows: 1

   * - Release Name
     - Description
   * - Pike
     - Introduced
