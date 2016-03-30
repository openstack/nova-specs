..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

==========================================
VMware Limits, Shares and Reservations
==========================================

https://blueprints.launchpad.net/nova/+spec/vmware-limits-mitaka

VMware Virtual Center provides options to specify limits, reservations and
shares for CPU, memory, disks and network adapters.

In the Juno cycle support for CPU limits, reservation and shares was added.
This blueprint proposes a way of supporting memory, disk and network
limits, reservations and shares.

For limits the utlization will not exceed the limit. Reservations will be
guaranteed for the instance. Shares are used to determine relative allocation
between resource consumers. In general, a consumer with more shares gets
proportionally more of the resource, subject to certain other constraints.

Problem description
===================

The VMware driver is only able to support CPU limits. Providing admins the
ability to provide limits, reservation and shares for memory, disks and
network adapters will be a very useful tool for providing QoS to tenants.

Use Cases
----------

* This will enable a cloud provider to provide SLA's to customers

* It will allow tenants to be guaranteed performance


Proposed change
===============

Due to the different models for different drivers and the API's in which
the backends expose we are unable to leverage the same existings flavor
extra specs.

For example for devices libvirt makes use of: 'hw_rng:rate_bytes',
'hw_rng:rate_period'.

In addition to this there are the following disk I/O options are:

'disk_read_bytes_sec', 'disk_read_iops_sec', 'disk_write_bytes_sec',
'disk_write_iops_sec', 'disk_total_bytes_sec', and
'disk_total_iops_sec'.

For bandwidth limitations there is the 'rxtx_factor'. This will not enable
us to provide the limits, reservations and shares for vifs. This is used in
some bases to pass the information through to Neutron so that the backend
network can do the limitations. The following extra_specs can be configured
for bandwidth I/O for vifs:

'vif_inbound_average', 'vif_inbound_burst', 'vif_inbound_peak',
'vif_outbound_average', 'vif_outbound_burst' and 'vif_outbound_peak'.

None of the above of possible for the VMware driver due to VC API's. The
following additions below are proposed:

Limits, reservations and shares will be exposed for the following:

* memory

* disks

* network adapters

The flavor extra specs for quotas has been extended to support:

* quota:memory_limit - The memory utilization of a virtual machine will not
  exceed this limit, even if there are available resources. This is
  typically used to ensure a consistent performance of virtual machines
  independent of available resources. Units are MB.

* quota:memory_reservation - guaranteed minimum reservation (MB)

* quota:memory_shares_level - the allocation level. This can be 'custom',
  'high' 'normal' or 'low'.

* quota:memory_shares_share - in the event that 'custom' is used, this is
  the number of shares.

* quota:disk_io_limit - The I/O utilization of a virtual machine will not
  exceed this limit. The unit is number of I/O per second.

* quota:disk_io_reservation - Reservation control is used to provide guaranteed
  allocation in terms of IOPS

* quota:disk_io_shares_level - the allocation level. This can be 'custom',
  'high' 'normal' or 'low'.

* quota:disk_io_shares_share - in the event that 'custom' is used, this is
  the number of shares.

* quota:vif_limit - The bandwidth limit for the virtual network adapter.
  The utilization of the virtual network adapter will not exceed this limit,
  even if there are available resources. Units in Mbits/sec.

* quota:vif_reservation - Amount of network bandwidth that is guaranteed to
  the virtual network adapter. If utilization is less than reservation, the
  resource can be used by other virtual network adapters. Reservation is not
  allowed to exceed the value of limit if limit is set. Units in Mbits/sec.

* quota:vif_shares_level - the allocation level. This can be 'custom',
  'high' 'normal' or 'low'.

* quota:vif_shares_share - in the event that 'custom' is used, this is the
  number of shares.

Alternatives
------------

The alternative is to create an abstract user concept that could help hide
the details and of the difference from end users, and isolate the differences
to just the admin users.

This is really out of the scope of what is proposed and will take a huge
cross driver effort. This will not only be relevant for flavors but maybe for
images too.

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

Preventing instances from exhausting storage resources can have a significant
performance impact.

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
  garyk

Work Items
----------

* common objects for limits, reservation and shares

* memory support

* disk support

* vif support

Dependencies
============

None

Testing
=======

This will be tested by the VMware CI. We will add tests to validate this.

Documentation Impact
====================

This should be documented in the VMware section.

References
==========

The vCenter API's can be see the following links:

* Disk IO: http://goo.gl/uepivS

* Memory: http://goo.gl/6sHwIA

* Network Adapters: http://goo.gl/c2amhq

History
=======

None
