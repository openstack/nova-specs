..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

=================================================
Multiple Fixed-IPs support in network information
=================================================

https://blueprints.launchpad.net/nova/+spec/multiple-fixed-ips-network-information

Introduce support for multiple fixed-ips in network information found
in metadata service. Network information currently only considers
the first fixed-ip even if instance has more than one fixed-ip per port.

Problem description
===================

`Previous work`_ introduced network information concept which removes
the need for in-guest agent such as cloud-init to parse a Debian like
network configuration file (``/etc/network/interfaces``) on
non-Debian platforms.

New network information work unfortunately inherited the limitation of
the previous network template system and hasn't been updated to account
for ports with multiple fixed IPs. The network information found in
metadata service and configuration drive will only have the first fixed IP of
the first subnet present. This means it is not possible for an instance
to have multiple fixed IPs and have them configured at boot time
or after instance is rebuilt.

A End User can assign multiple fixed IPs to a Neutron port. Those fixed IPs
can be part of the same subnet or from different subnets.

When creating an instance, Nova will only consider the first fixed IP
of the first subnet when building the network information found in the
metadata service and configuration drive.

A End User have to manually configure the other fixed IPs after
the instance is created. This means additional work from the End User before
the instance is fully configured and ready for use.

If he rebuilds the instance, he will lose his additional fixed IPs
configuration and will need to manually configure them after rebuild
is completed.

A End User can assign additional fixed IPs to a Neutron port after
the instance creation. Due to the static nature of the configuration drive,
he will have to manually configure them in his instance. This is a known
limitation of the configuration drive and won't be addressed in this spec.

Use Cases
---------

As a user, I want my server with multiple fixed IPs to be configurable on boot
or rebuild of the guest without manual intervention.

As a user, when I attach a new port to my server instance, I want
the metadata API service to make that port's fixed IP information
available to my guest for configuration.

Proposed change
===============

This change proposes adding all fixed IPs to network information found in
metadata service and configuration drive. Current network information format
does not allow for multiple fixed IPs, it will require changes.

There is no plan to add support for multiple fixed IPs to
the legacy network template unless there is a need and common agreement that
it would be easily feasible.

Alternatives
------------

There is no known alternative.

Data model impact
-----------------

* There is no impact on the ``network_info`` field found in
  the ``InstanceInfoCache`` object. It already supports multiple subnets and
  fixed IPs per subnet.

REST API impact
---------------

* The network_data.json format needs to be changed to include
  all the subnets and fixed IPs found in the network.
  This will require the introduction of a new metadata version.

* The old ip_address and netmask fields found in network_data.json need
  to be preserved for backward compatible reasons. This means those fields
  will continue to contain information of the first IP address.

Sample API for getting network information from metadata service

GET: http://169.254.169.254/openstack/$VERSION/metadata/network_data.json

JSON Response::

    {
        "links": [
            {
                "id": "interface0",
                "type": "vif",
                "ethernet_mac_address": "a0:36:9f:2c:e8:70",
                "vif_id": "e1c90e9f-eafc-4e2d-8ec9-58b91cebb53d",
                "mtu": 1500
            },
        ],
        "networks": [
            {
                "id": "network0",
                "type": "ipv4",
                "link": "interface0",
                "network_id": "da5bb487-5193-4a65-a3df-4a0055a8c0d7",
                "ip_address": "10.184.0.244",
                "netmask": "255.255.240.0",
                "ip_addresses": [
                  "10.184.0.244/20",
                  "10.184.0.245/20"
                ],
                "services": [
                    {
                        "type": "dns",
                        "address": "8.8.8.8"
                    },
                    {
                        "type": "dns",
                        "address": "8.8.4.4"
                    }
                ],
                "routes": [
                    {
                        "network": "192.168.0.0",
                        "netmask": "255.255.0.0",
                        "gateway": "10.184.0.1"
                    },
                    {
                        "network": "0.0.0.0",
                        "netmask": "0.0.0.0",
                        "gateway": "10.184.0.1"
                    }
                ],
            },
            {
                "id": "network1",
                "type": "ipv6",
                "link": "interface0",
                "network_id": "da5bb487-5193-4a65-a3df-4a0055a8c0d8",
                "ip_address": "2001:db8::3257:9652",
                "netmask": "ffff:ffff:ffff:ffff::",
                "ip_addresses": [
                  "2001:db8::3257:9652/24"
                ],
                "services": [
                    {
                        "type": "dns",
                        "address": "1:2:3:4::"
                    },
                    {
                        "type": "dns",
                        "address": "2:3:4:5::"
                    }
                ],
                "routes": [
                    {
                        "network": "::",
                        "netmask": "::",
                        "gateway": "fd00::1"
                    },
                    {
                        "network": "::",
                        "netmask": "ffff:ffff:ffff::",
                        "gateway": "fd00::1:1"
                    },
                ]
            },
        ],
        "services": [
            {
                "type": "dns",
                "address": "8.8.8.8"
            },
            {
                "type": "dns",
                "address": "8.8.4.4"
            },
            {
                "type": "dns",
                "address": "1:2:3:4::"
            },
            {
                "type": "dns",
                "address": "2:3:4:5::"
            }
        ]
    }



Security impact
---------------

None

Notifications impact
--------------------

None

Other end user impact
---------------------

This change will require in-guest agent such as cloud-init to read and
parse the new metadata version to benefit from it.
Older in-guest agent versions will continue to read from the previous
metadata version.

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
  mgagne

Work Items
----------

1. Implement new network_data.json format


Dependencies
============

None


Testing
=======

Unit and functional tests will be added as required.


Documentation Impact
====================

* There is no official reference for the network data format.
  This spec is the best reference at the moment.


References
==========

.. _previous work: https://specs.openstack.org/openstack/nova-specs/specs/liberty/implemented/metadata-service-network-info.html



History
=======

.. list-table:: Revisions
   :header-rows: 1

   * - Release Name
     - Description
   * - Ocata
     - Introduced
   * - Pike
     - Re-proposed
   * - Rocky
     - Re-proposed
