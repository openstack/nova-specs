..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

==================================================
API: Proxy neutron configuration to guest instance
==================================================

https://blueprints.launchpad.net/nova/+spec/metadata-service-network-info

Improve the networking info given in both config drive and the metadata
service to instances.

Problem description
===================

Use Cases
---------
Currently, cloud-init takes the Debian-style interfaces file that is
generated from a template and has to convert it to an interfaces file for
other OSs such as RHEL or Windows. This becomes more and more challenging as
network configurations get more complex.

Ironic is working with baremetal hardware. Their network configs might
require more complex network configurations such as multiple VLANs over bonded
interfaces. Translating network templates to multiple OS's then becomes much
more challenging than today. These aren't supported in Neutron as of today,
but there are multiple proposed changes to add support. Using a flexible
design will allow new network configurations much more easily.

Alternate Use Cases:
Consider a VM with the first interface configured by DHCP, and all other
interfaces on private networks where the interfaces are statically configured,
but you are not using config drive, just the metadata service, and not
cheating by doing file injection, presenting the data in a guest agnostic
format.

Setting up static routes without declaring a global route in the interfaces
template.

For Future Expansion:
Future use cases would be using this format to create bonded interfaces,
either of physical or virtual interfaces. Many hypervisors are deployed on
hardware with bonded interfaces, so it is sensible for Ironic/TripleO
to require bonds. To create these bonds today, assumptions have to be made
about the interface names that are being bonded, which can change depending
on the OS. With this change, the bonds can be described generically and
implemented in a consistent way for the OS.

Project Priority
----------------
None, but this combined with Neutron support for bonding, will increase the
fault tolerance of Ironic nodes. In the case of Triple O, that would also
increase the fault tolerance of the hardware running Nova in the overcloud.

Proposed change
===============

* Create a versioned network_data (like user_data and vendor_data already in
  the metadata service and configdrive) providing more detailed network info
* A flexible JSON schema to deal with complex network layouts,
  and which can be extended easily as Neutron supports more configurations
* Information comes from current network_info for instance
* Some things like bonds won't be supported until Neutron supports them
* We only really need concrete info: mac address, fixed IP address, subnet,
  gateway, host routes, neutron port-id, neutron network-id, neutron subnet-id
* Links should be split out separate from network information to make tiered
  structures like bonds more easily implemented
* VIFs will be supported as a Link
* Physical links will be supported when the neutron-external-attachment-points
  blueprint is completed. [1]
* VLANs will be supported as another type of Link
* Add a "services" section for network services that aren't related to a
  particular network or interface. The primary use will be DNS servers.
* In the future, bonds can be supported as another type of Link, pointing at
  multiple other Links

Alternatives
------------

* Neutron could create the network_data.json and have Nova simply download
  the file and add it to the metadata service and configdrive.

Data model impact
-----------------

None

REST API impact
---------------

Sample API for getting network information from metadata service

GET: http://169.254.169.254/openstack/$VERSION/metadata/network_data.json

JSON Response::

    {
    "links": [
        { // Example of VIF
            "id": "interface2", // Generic, generated ID
            "type": "vif", // Can be 'vif', 'phy' or (future) 'bond'
            "ethernet_mac_address": "a0:36:9f:2c:e8:70", // MAC from Neutron
            "vif_id": "E1C90E9F-EAFC-4E2D-8EC9-58B91CEBB53D",
            "mtu": 1500 // MTU for links
        },
        { // Example of physical NICs
            "id": "interface0",
            "type": "phy",
            "ethernet_mac_address": "a0:36:9f:2c:e8:80",
            "mtu": 9000
        },
        {
            "id": "interface1",
            "type": "phy",
            "ethernet_mac_address": "a0:36:9f:2c:e8:81",
            "mtu": 9000
        },
        { // Bonding two NICs together (future support)
            "id": "bond0",
            "type": "bond",
            "bond_links": [
                "interface0",
                "interface1"
            ],
            "ethernet_mac_address": "a0:36:9f:2c:e8:82",
            "bond_mode": "802.1ad",
            "bond_xmit_hash_policy": "layer3+4",
            "bond_miimon": 100

        },
        { // Overlaying a VLAN on a bond (future support)
            "id": "vlan0",
            "type": "vlan",
            "vlan_link": "bond0",
            "vlan_id": 101,
            "vlan_mac_address": "a0:36:9f:2c:e8:80",
            "neutron_port_id": "E1C90E9F-EAFC-4E2D-8EC9-58B91CEBB53F"
        },
    ],
    "networks": [
        { // Standard VM VIF networking
            "id": "private-ipv4",
            "type": "ipv4",
            "link": "interface0",
            "ip_address": "10.184.0.244",
            "netmask": "255.255.240.0",
            "routes": [
                {
                    "network": "10.0.0.0",
                    "netmask": "255.0.0.0",
                    "gateway": "11.0.0.1"
                },
                {
                    "network": "0.0.0.0",
                    "netmask": "0.0.0.0",
                    "gateway": "23.253.157.1"
                }
            ],
            "neutron_network_id": "DA5BB487-5193-4A65-A3DF-4A0055A8C0D7"
        },
        { // IPv6
            "id": "private-ipv4",
            "type": "ipv6",
            "link": "interface0",
            // supports condensed IPv6 with CIDR netmask
            "ip_address": "2001:cdba::3257:9652/24",
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
            ],
            "neutron_network_id": "DA5BB487-5193-4A65-A3DF-4A0055A8C0D8"
        },
        { // One IP on a VLAN over a bond of two physical NICs (future support)
            "id": "publicnet-ipv4",
            "type": "ipv4",
            "link": "vlan0",
            "ip_address": "23.253.157.244",
            "netmask": "255.255.255.0",
            "dns_nameservers": [
                "69.20.0.164",
                "69.20.0.196"
            ],
            "routes": [
                {
                    "network": "0.0.0.0",
                    "netmask": "0.0.0.0",
                    "gateway": "23.253.157.1"
                }
            ],
            "neutron_network_id": "62611D6F-66CB-4270-8B1F-503EF0DD4736"
        }
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
    ]
    }


The same JSON will be stored in the configdrive under
openstack/$VERSION/network_data.json

Security impact
---------------

The JSON data could give more insight into the network than would be
available otherwise to a guest instance. In a locked down environment,
a user may be able see more network details in the metadata service than they
could otherwise discover. An example could be a hardened SELinux VM. A
security note should be documented.

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

The intention is that this network metadata can be used by cloud-init and
other in-instance agents to configure the network in more advanced ways. It
is possible that, depending on the agent's implementation,
the network config could change slightly compared to configs generated prior
to this new metadata. An example is network interfaces being named slightly
differently than the OS would name them. This will be highly dependent on
changes to agents like cloud-init.

Developer impact
----------------

None

Implementation
==============

Assignee(s)
-----------

Primary assignee:
  JoshNang

Other contributors:
  claxton
  JayF

Work Items
----------

* Get basic networking info from neutron into Metadata Service
  (list of: mac, IP, subnet, gateway, neutron-port-id, host-routes)
* Add above information into ConfigDrive as "network_data"

Dependencies
============

None

Testing
=======

Unit and functional tests will be added to check if network data is returned.

Documentation Impact
====================

Changes to the Metadata Service api to ask and return network data.

References
==========

[1] https://blueprints.launchpad.net/neutron/+spec/neutron-external-attachment-points

[2] https://etherpad.openstack.org/p/IcehouseNovaMetadataService

