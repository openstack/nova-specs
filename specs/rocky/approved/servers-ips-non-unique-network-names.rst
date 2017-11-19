..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

============================================================
Support non-unique network names in Servers IPs API response
============================================================

https://blueprints.launchpad.net/nova/+spec/servers-ips-non-unique-network-names

Report correct server IP information when multiple networks with the same name
are used in VM. This spec proposes to group VM networks using their IDs rater
than names in Server IPs API resource.

Problem description
===================

Neutron allows multiple networks with the same name. Nova allows adding
multiple networks to a VM.

When two networks with the same name are added to a VM and Servers IPs API
request is made then incorrect information is returned. Response is the same
as if there would be a single network with multiple IP addresses.

.. code-block:: javascript

   // GET /servers/68c1b82f-adf2-4b71-a411-0b70da3c1748/ips

   {
     "addresses": {
       "testnet1": [
         {
           "OS-EXT-IPS-MAC:mac_addr": "fa:16:3e:65:83:12",
           "version": 4,
           "addr": "192.168.0.12",
           "OS-EXT-IPS:type": "fixed"
         },
         {
           "OS-EXT-IPS-MAC:mac_addr": "fa:16:3e:7c:67:72",
           "version": 4,
           "addr": "192.168.1.4",
           "OS-EXT-IPS:type": "fixed"
         }
       ]
     }
   }

Instead, the response should indicate that there are two networks with single
address each. Additionally network label shall be preserved.

.. code-block:: javascript

   // GET /servers/68c1b82f-adf2-4b71-a411-0b70da3c1748/ips

   {
      "addresses":{
         "b7388c79-b206-4ddf-9d75-95ec4488b906":{
            "name":"testnet1",
            "ips":[
               {
                  "OS-EXT-IPS-MAC:mac_addr":"fa:16:3e:65:83:12",
                  "version":4,
                  "addr":"192.168.0.12",
                  "OS-EXT-IPS:type":"fixed"
               }
            ]
         },
         "b69db569-85b3-4fd6-b053-11be7d23fbc6":{
            "name":"testnet1",
            "ips":[
               {
                  "OS-EXT-IPS-MAC:mac_addr":"fa:16:3e:7c:67:72",
                  "version":4,
                  "addr":"192.168.1.4",
                  "OS-EXT-IPS:type":"fixed"
               }
            ]
         }
      }
   }

Consequently request for specific network shall be altered from::

    /servers/{server_id}/ips/{network_label}

to::

    /servers/{server_id}/ips/{network_id}

Use Cases
---------

As an API user with a server attached to multiple networks with the same name,
I want to be able to uniquely identify with which networks the server IP
addresses are associated.

Proposed change
===============

This spec propose to fix this bug as microversion by changing response schema
and resource path.
The legacy API won't be fixed as the change affects API consumers.

Alternatives
------------

* Do not allow adding network with the same name as already existing ones
* Report server IPs as an array, not dict

Data model impact
-----------------

None

REST API impact
---------------

Two changes to API by new microversion:

Change resource path from::

    /servers/{server_id}/ips/{network_label}

to::

    /servers/{server_id}/ips/{network_id}

Change schema of ``/servers/{server_id}/ips`` resource to:

* group networks by IDs
* preserve network name in the network group

.. code-block:: javascript

   {
      "addresses":{
         "b7388c79-b206-4ddf-9d75-95ec4488b906":{
            "name":"testnet1",
            "ips":[
               {
                  "OS-EXT-IPS-MAC:mac_addr":"fa:16:3e:65:83:12",
                  "version":4,
                  "addr":"192.168.0.12",
                  "OS-EXT-IPS:type":"fixed"
               }
            ]
         }
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

None

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

Primary assignees:
    Jonghan Park <jhan12.park@samsung.com>
    Maciej Kucia <maciej@kucia.net>

Work Items
----------

* Fix the API by new microversion
* Reflect API changes in nova-client
* Reflect API changes in documentation

Dependencies
============

None

Testing
=======

Tests shall be updated to reflect API changes.

Documentation Impact
====================

Update the `api-ref`_ to reflect new API schema and paths.

References
==========

* https://bugs.launchpad.net/nova/+bug/1708316
* https://developer.openstack.org/api-ref/compute/#servers-ips-servers-ips

.. _api-ref: http://developer.openstack.org/api-ref/compute/

History
=======

.. list-table:: Revisions
   :header-rows: 1

   * - Release Name
     - Description
   * - Rocky
     - Introduced
