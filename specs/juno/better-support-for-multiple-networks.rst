..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

====================================================
Better Support for Multiple Networks in nova-network
====================================================

https://blueprints.launchpad.net/nova/+spec/better-support-for-multiple-networks

Since nova-network is staying around, it needs a few updates for multiple
networks. There are various settings that are automatically determined or set
via flags, that should be explicitly set per network. This spec is about adding
a few options to the networks table and converting the network manager and
linux_net code to support multiple networks.

Problem description
===================

Currently it is impossible to have multiple networks with different mtu
settings or to have some networks that share ips or have external gateways and
others that do not. If you have a single network it is possible to specify a
different (external) gateway for that network by adding a custom dnsmasq.conf,
but this breaks down when you have multiple networks.

Proposed change
===============

This change proposes adding four fields to the networks table:

 * mtu
 * dhcp_server
 * enable_dhcp
 * share_address

Each of the new fields will be used in place of existing config options or
automatic value interpretation. The defaults for these options will mean there
is no difference to users if they are not specified.

It will also modify network create to allow these fields to be modified. An api
extension will be added so one can determine if extra network fields are
available.

Alternatives
------------

Supporting this functionality without changing the data model would require
some pretty complex config options. For example mtu could be a list of network
names and mtus, but this is extremely unweildy.

Data model impact
-----------------

This adds four new fields to the network model. The fallback for these fields
will use the existing config options and defaults. These config options will be
marked deprecated but will still work by default.

The four new fields will be added to the object model, and they will be cut out
for older versions.

REST API impact
---------------

The current network create api allows extra values to be passed in and they are
silently ignored. In order to provide information about whether the new fields
are supported, a dummy api extension will be created and the extra fields will
only be accepted/returned if the api extension is enabled.

The json for a network create call would currently look like::

    {
        "network": {
            "label": "new net 111",
            "cidr": "10.20.105.0/24",
            ...
        }
    }

With the new fields it would support::

    {
        "network": {
            "label": "new net 111",
            "cidr": "10.20.105.0/24"
            "mtu": 9000,
            "enable_dhcp": "true",
            "dhcp_server": "10.20.105.2",
            "share_address": true,
            ...
        }
    }

These fields will also be returned in the show command::

    {
        "network": {
            "bridge": "br100",
            "bridge_interface": "eth0",
            "broadcast": "10.0.0.7",
            "cidr": "10.0.0.0/29",
            "cidr_v6": null,
            "created_at": "2011-08-15T06:19:19.387525",
            "deleted": false,
            "deleted_at": null,
            "dhcp_start": "10.0.0.3",
            "dns1": null,
            "dns2": null,
            "gateway": "10.0.0.1",
            "gateway_v6": null,
            "host": "nsokolov-desktop",
            "id": "20c8acc0-f747-4d71-a389-46d078ebf047",
            "injected": false,
            "label": "mynet_0",
            "multi_host": false,
            "netmask": "255.255.255.248",
            "netmask_v6": null,
            "priority": null,
            "project_id": "1234",
            "rxtx_base": null,
            "updated_at": "2011-08-16T09:26:13.048257",
            "vlan": 100,
            "vpn_private_address": "10.0.0.2",
            "vpn_public_address": "127.0.0.1",
            "vpn_public_port": 1000,
            "mtu": 9000,
            "dhcp_server": "10.20.105.2",
            "enable_dhcp": true,
            "share_address": true
        }
    }

Security impact
---------------

This change doesn't have any security impact.

Notifications impact
--------------------

This change doesn't impact notifications.

Other end user impact
---------------------

This change will also include a modification to python-novaclient network
create to allow users to create networks specifying the additional fields.

Performance Impact
------------------

The performance impact of this change is negligible.

Other deployer impact
---------------------

Deployers should start using the network fields in place of the config options,
but there is no requirement for them to move right away.

Developer impact
----------------

This change should not affect developers.

Implementation
==============

Assignee(s)
-----------

Primary assignee:
  vishvananda

Other contributors:
  None

Work Items
----------

Nova code addtions
Python-novaclient code addtions
Tempest test additions

Dependencies
============

There are no new dependencies for this feature.


Testing
=======

There are currently no tempest tests for the create network call. A test for
create network including the new fields  will be added.  The internal
modifications will be covered by unit tests.


Documentation Impact
====================

The new additions to the network create call need to be documented.

References
==========

None
