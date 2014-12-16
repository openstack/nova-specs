..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

===============================================
Distribute PCI Requests Across Multiple Devices
===============================================

https://blueprints.launchpad.net/nova/+spec/distribute-pci-allocation

PCI requests are provisioned in a list based fashion. In SR-IOV networking
devices, a set of candidate virtual functions can span multiple physical
functions and physical ports. Distributing single and multiple device requests
across multiple physical functions provides:

* Better load distribution across available links.

* Provides L2 redundancy when multiple devices are allocated on behalf of a
  single guest.


Problem description
===================

Simple queue based device selection for PCI SR-IOV devices does not distribute
load across physical connections nor does it permit guests to achieve L2
redundancy by requesting multiple SR-IOV based ports.

Use Cases
----------

On systems where there is a physical function per physical network and creating
an Openstack instance with multiple SR-IOV ports, spreading the port
allocation across candidate physical functions provides more even device and
link utilization as well as allowing guests to take advantage of L2 redundant
links for bonding, etc.

Proposed change
===============

The proposed change alters the PCI device request scheduling for PCI SR-IOV
to to distribute consumption of VFs evenly across available multiple physical
functions for the same associated label.

Distribution happens in best-effort fashion, so even if PCI request cannot
be supported in a distributed fashion, but still could be satisfied by
the current queue based allocation schema, a guest will be booted.

Alternatives
------------

There are no alternatives that directly satisfy distribution of requests for
more even utilization. Ensuring multiple SR-IOV device requests for a guest
span multiple physical links could employ additional port detail information
but would still require PCI request scheduling changes.

Link optimization could be improved by providing scheduling based on available
throughput, However, this does not satisfy the physical link redundancy use
case. Also, it would only work where throughput details are actually provided
by the underlying device.

Data model impact
-----------------

The current model should be sufficient as it contains the required
bookkeeping.

REST API impact
---------------

None.

Security impact
---------------

None.

Notifications impact
--------------------

None.

Other end user impact
---------------------

None.

Performance Impact
------------------

There is an increase in complexity in scheduling guest creation that may
increase the amount of time taken to schedule guests that are connected to
multiple PCI similar SR-IOV devices. It has no effect on other cases.

Other deployer impact
---------------------

None.

Developer impact
----------------

None.

Implementation
==============

Assignee(s)
-----------

Assignee:
 Roman Bogorodskiy <rbogorodskiy@mirantis.com>


Work Items
----------

* Alter PCI device selection logic to support distribution across multiple PCI
  roots (physical functions)
* Extend PCI request API to support multiple device requests.
* Modify scheduler code to employ the new API.

Dependencies
============

None.

Testing
=======

The changes to the selection logic are testable through unit testing, as is
the extension to the PCI request API.

Additionally, it's intended to cover this feature with functional tests
as well.

Documentation Impact
====================

None.

References
==========

None.
