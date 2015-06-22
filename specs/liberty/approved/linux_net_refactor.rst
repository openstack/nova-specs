..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

==========================================
nova.network.linux_net refactor
==========================================

https://blueprints.launchpad.net/nova/+spec/linux-net-refactor

The nova.network.linux_net module that is responsible for a number
of networking aspects of Nova is quite large and not very flexible
in terms of code maintainance and portability, so it could have a refactor.

In addition to this, improving flexibility of the linux_net.py module
will be a huge step forward towards FreeBSD host support, see the mailing
list discussion for details [1].

Problem description
===================

Currently, nova.network.linux_net is responsible for a number of different
things:

* Network interface management (the code to manipulate bridges,
  adding/removing interfaces etc)
* Firewall/Iptables management
* dnsmasq management

The linux_net.py file is almost 2k lines long, that's not critically large,
but could be smaller.

Some parts of it is flexible and allows overriding classes, for example
linuxnet_interface_driver. Some parts are not, for example IptablesManager.
Even for classes that allow overriding, there are consumers that use it
directly, for example virt.libvirt.vif uses LinuxBridgeInterfaceDriver
directly.

Also, there are some relatively similar blocks that do the same thing and
could be grouped into functions, for example, LinuxBridgeInterfaceDriver and
NeutronLinuxBridgeInterfaceDriver use almost identical code for bridge
creation.

It would be good to improve code maintainability, readability and portability
by refactoring the linux_net.py module.

Use Cases
----------

The only type of audience that would benefit from this change is developers
who work with linux_net.py and ones who are looking into extending Nova
with new mechanisms for interface management, firewalling and related.

Project Priority
-----------------

None

Proposed change
===============

The proposed appoach would be:

Currently the usage of linux_net in libvirt.vif looks this way:

 * The following methods are used:
   - create_tap_dev()
   - create_ovs_vif_port()
   - create_ivs_vif_port()
   - device_exists()
   - delete_net_dev()

 * Usage of linux_net.LinuxBridgeInterfaceDriver methods:
   - ensure_vlan_bridge()
   - ensure_bridge()


One could notice this interface is pretty complex and actually
it is responsible for two things at the same time:

 * Providing a Nova network API logic
 * Providing helpers for OS-level network device management

In order to make it more portable the proposal is to split out
the OS-level helpers into its own entity and allow custom
implementations for specific platform.

For example, it would look this way::


        """
        nova.network.netdev module
        """

        def get_driver():
            "Method returning platfrom specific implementation"
            if our_os == "Linux":
                return LinuxNetDevDriver
            else
                # not implemented

        # network device helpers
        def create_bridge(brname):
            return get_driver().create_bridge(brname)

        # other methods go here

        """
        nova.network.netdev.driver
        """

        class NetDevDriver(object):
            """A class that defines an interface for
            OS-level network device manipulation"""

            def create_bridge(self, brname):
                raise NotImplementedError

            # other methods go here


        """
        nova.netowrk.netdev.linux
        """

        class LinuxNetDevDriver(NetDevDriver):
            """A class that implements NetDevDriver
            interface for Linux"""

            def create_bridge(self, brname):
                # Linux impl goes here

            # other methods


The plan is:

 - Move out helper functions from linux_net to netdev
 - Convert consumers of these helper functions from linux_net
   to use the new netdev helpers
 - Drop the old implementation of helpers from linux_net
 - Move out Iptables related classes to its own module firewall
   and allow to override with actual class to be used so it was
   possible to use other firewall packages
 - Move out dnsmasq related code to its own module dhcp

Alternatives
------------

None

Data model impact
-----------------

None

REST API impact
---------------

None

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

As the new option will be introduced that allows to specify
the firewall class to use, deployers will be able to integrate
third party firewalling packages. As this option will default
to IptablesManager, there would be no changes to current deployments.

Developer impact
----------------

Developers will have a more readable, maintainable and extendible linux_net.py

Implementation
==============

Assignee(s)
-----------

Primary assignee:
  novel

Work Items
----------

* Refactor the interface management code
* Split out the firewalling code
* Split out the dnsmasq management code

Dependencies
============

None

Testing
=======

Unit tests will be updated accordingly.

Documentation Impact
====================

None

References
==========

[1]: http://lists.openstack.org/pipermail/openstack-dev/2015-June/066342.html

History
=======

.. list-table:: Revisions
   :header-rows: 1

   * - Release Name
     - Description
   * - Liberty
     - Introduced
