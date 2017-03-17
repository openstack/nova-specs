..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

==========================================
PCI Pass-through Whitelist Regex
==========================================

https://blueprints.launchpad.net/nova/+spec/pci-passthrough-whitelist-regex

Enhance PCI pass-through whitelist to support regular expression for address
attributes.

Problem description
===================

Current PCI pass-through whitelist address entry is defined as:
["address": "[[[[<domain>]:]<bus>]:][<slot>][.[<function>]]",
where the address uses the same syntax as it's in lspci or
aggregated declaration of PCI devices by using '*'. Therefore there
is no way to exclude specific VF(s) from the PCI pass-through whitelist
address.

Use Cases
----------

Deployer may want to exclude specific VF(s) to be used for other purposes.
For instance VF can be used to connect compute node to storage node
by running iSER (iSCSI Extensions for RDMA) transport.


Proposed change
===============

Enhance PCI pass-through whitelist to support regular expression syntax for
address attributes.
A new syntax will be introduced for the address key:
"address":{ "domain": <domain>, "bus": <bus>, "slot": <slot>, \
"function": <function> }
The traditional glob style will still be supported:
"address": "<domain>:<bus>:<slot>.<function>"


Example for the regular expression syntax:

This allows allocation of VFs whose functions are from 2 upwards:
pci_passthrough_whitelist= \
{"address":{"domain": ".*", "bus": "02", "slot": "01", "function": "[2-7]"}, \
"physical_network":"net1"}

This allows allocation of VFs whose functions are from 2 downwards:
pci_passthrough_whitelist= \
{"address":{"domain": ".*", "bus": "02", "slot": "01", "function": "[0-2]"}, \
"physical_network":"net1"}

This allows allocation of VFs whose slots are between 1 and 2:
pci_passthrough_whitelist= \
{"address":{"domain": ".*", "bus": "02", "slot": "0[1-2]", "function": ".*"}, \
"physical_network":"net1"}

Alternatives
------------

* Instead of whitelist regular expression we could add multiple PCI
  pass-through whitelist entries per host. These entries include all
  the VFs that can be used. This is already supported.

* Instead of whitelist regular expression we could add PCI pass-through
  blacklist to sit alongside the whitelist to exclude specific PCI addresses.

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

None

Developer impact
----------------

None

Implementation
==============

Assignee(s)
-----------

Primary assignee:
moshele (moshele@mellanox.com)

Work Items
----------

* Add regular expression syntax support to PciAddress in devspec.py.

Dependencies
============

None

Testing
=======

* Unit tests will be added.
* Mellanox third party CI will be updated to test this feature.
  https://wiki.openstack.org/wiki/ThirdPartySystems/Mellanox_CI


Documentation Impact
====================
Added regular expression syntax to pci_passthrough_whitelist entry
as documented above.

References
==========

[1] https://review.openstack.org/#/c/99043/
[2] https://wiki.openstack.org/wiki/SR-IOV-Passthrough-For-Networking
