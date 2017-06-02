..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

============================================================
Enable passthrough of SR-IOV physical functions to instances
============================================================

https://blueprints.launchpad.net/nova/+spec/sriov-physical-function-passthrough

Nova has supported passthrough of PCI devices with its libvirt driver for a
few releases already, during which time the code has seen some stabilization
and a few minor feature additions.

In the case of SR-IOV enabled cards, it is possible to treat any port on the
card either as a number of virtual devices (called VFs - virtual functions) or
as a full device (PF - physical function).

Nova's current handling exposes only virtual functions as resources that can
be requested by instances - and this is the most common use case by far.
However with the rise of the requirements to virtualize network applications,
it can be necessary to give instances full control over the port and not just a
single virtual function.

OpenStack is seen as one of the central bits of technology for the NFV
use-cases, and a lot of the work has already gone into making OpenStack and
Nova NFV enabled, so we want to make sure that we close these small remaining
gaps.


Problem description
===================

Currently it is not possible to pass through a physical function to an
OpenStack instance, but some NFV applications need to have full control of the
port, while others are happy with using a VF of an SR-IOV enabled card. It is
beneficial to be able to do so with the same set of cards, as pre-provisioning
resources on the granularity smaller than compute hosts is cumbersome
to manage and goes against the goal of Nova to provide on demand
resources. We want to be able to give certain instances unlimited access to the
port by assigning the PF to it, but revert back to using VFs when the PF is not
being used, so as to ensure on-demand provisioning of available resources. This
may not be possible with every SR-IOV card and their respective Linux drivers,
in which case certain ports will need to be pre-provisioned as either PFs or
VFs by administratior ahead of time.

This in turn means that Nova would have to keep track of which VFs belong to
particular PFs and make sure that this is reflected in the way resources are
tracked (so even a single VF being used means the related PF is unavailable and
vice versa, if a PF is being used, all of it's VFs are marked as used).

PCI device management code in Nova currently filters out any
device that is a physical function (this is currently hard-coded). In
addition, modeling of PCI device resources in Nova currently assumes flat
hierarchy and resource tracking logic does not understand the relationship
between different PCI devices that can be exposed to Nova.


Use Cases
----------

Certain NFV workloads may need to have the full control of the physical device,
in order to use some of the functionality not available to VFs, to bypass some
limitations certian cards impose on VFs, or to exclusively use the full
bandwidth of the port. However, due to the dynamic nature of the elastic cloud,
and the promise of Nova to deliver resources on demand, we do not wish to have
to pre-provision certain SR-IOV cards to be used as PFs as this defeats the
promise of the infrastructure management tool that allows for quick
re-purposing of resources that Nova brings.

Modern SR-IOV enabled cards along with their drivers usually allow for such
reconfiguration to be done on the fly, so once the passthrough of the PF is no
longer needed on a specific host (either the instance using it got moved or
deleted), the PF is bound back to it's Linux driver, thus enabling the use of
VFs provided that initialization steps (if any are needed) are done upon
handing the device back. It is not possible to
guarantee that this always works however, due to the vast range of equipment
and drivers available on the market, so we want to make sure that there is a
way to tell Nova that a card is in certain configuration and cannot be assumed
to be reconfigurable.

Additional use cases (that will require further work) will be enabled by having
the Nova data model usefully express the relationship between PF and its VFs.
Some of them have been proposed as separate specs (see [1]_ and [2]_).


Proposed change
===============

Two problems we need to solve are:

 1) How to enable requesting a full physical device. This means extending the
    InstancePCIRequest data model to be able to hold this information. Since
    the whitelist parsing logic that builds up the Spec objects probes the
    system and has the information about whether a device is a PF or not, it is
    enough to add a physical_function field to the PCI alias schema and the
    PCIRequest object.

 2) Enable scheduling and resource tracking based on the request that can now
    be for the whole device. This means extending the data model for PCIDevices
    to hold information about relationship between physical and virtual
    functions (this relationship is already recorded but not in a suitable
    format), and also extending the
    way we expose the aggregate data about PCI devices to the resource tracker
    (a.k.a. the PCIDeviceStats class) to be able to present PFs and their
    counts, and to make sure to track the corresponding VFs that become
    unavailable once the PF is claimed/used.

In addition to the above, we will want to make sure that whitelist syntax can
support passing throught PFs. This will require very few changes it turns out.
Currently if a whitelist entry
specifies an address or a devname of a PF, the matching code will make sure
any of the VFs match. This behavior, combined with allowing a device that is a
PF to be tracked by nova (by removing the hard-coded check that skips any PFs)
should be sufficient to allow most of the flexibility administrators need.
As it is not sufficient for a device to be whitelisted to be requestable by
users (it needs to either have an alias that is specified on the flavor),
simply defaulting to whitelisting PFs along with all of their VFs if a PF
address is whitelisted gives us the flexibility we need, while keeping
backwards compatibility.

As is the case with the current implementation, there is some initial
configuration that will be needed on hosts that have PCI devices that can be
passed through. In addition to the standard setup needed to enable SR-IOV and
configure the cards, and
whitelist configuration setup that Nova requires, administrators may also need
to add an automated way (such as udev rules) to re-enable VFs, since
depending on the driver and the card used, any existing
configuration may be lost once a VM is given full control of the port, and the
device is unbound from the host driver.

In order for PFs to work as Neutron ports, some additional work that is outside
of scope of this blueprint will be needed. We aim to make internal Nova changes
that are needed the focus here and defer on the integration work to a future
(possibly cross-project) blueprint. For the libvirt driver, this means that,
since there will be no Neutron support
at first, the only way to assign such a device would be using the <hostdev>
element, and no support for <interface> is in scope for this blueprint.

Alternatives
------------

There are no real alternatives that cover all of the use cases. An alternative
that would cover only the requirement for bandwidth would be to allow for
reserving of all VFs of a single PF by a single instance while using only a
single VF, effectively reserving the bandwidth. In addition to not being a
solution for all the applications, it also does not reduce the complexity of
the change much as the relationship between VFs still needs to be modeled in
Nova.

Data model impact
-----------------

Even though there is a way currently to figure out the PF a single VF belongs
to (through the use of `extra_info` free-form field) it may be necessary to add
a more "query friendly" relationship, that will allow us to answer the question
"given a PCI device record that is a PF, which VF records does it contain".

It is likely to be implemented as a foreign key relationship to the same table,
and objects support will be added, but the actual implementation discussion is
better suited for the actual code proposal review.

It will also be necessary to be able to know relations between individual PFs
and VFs in the aggregate view of the PCI device data used in scheduling, so
changes to the way PciDeviceStats holds aggregate
data. This will also result in changes to the filtering/claiming logic, the
extent of which may impact decisions about the data model so this is
best discussed on actual implementation changes.

REST API impact
---------------

There are no API changes required. PCI devices are requested through flavor
extra-specs by specifying an alias of a device specification. Currently,
device specifications and their aliases are part of the Nova deployment
configuration, and thus are deployment specific.

Security impact
---------------

None

Notifications impact
--------------------

None

Other end user impact
---------------------

None - non-admin users will continue to use only things exposed to them via
flavor extra-specs, which they cannot modify in any way.

Performance Impact
------------------

Scheduling of instances requiring PCI passthrough devices will be doing more
work and on a bit more data than currently in the case of PF requests. It is
unlikely that this will have any noticeable performance impact however.

Other deployer impact
---------------------

PCI alias syntax for enabling the PCI devices will become more feature-full, in
order to account for specifically requesting a PF.

Developer impact
----------------

None


Implementation
==============

Assignee(s)
-----------

Primary assignee:
  Nikola Đipanov <ndipanov@redhat.com>

Other contributors:
  Vladik Romanovsky <vromanso@redhat.com>

Work Items
----------

* Re-work the DB models and corresponding objects to have explicit relationship
  between the PF entry and it's corresponding VFs. Update the claiming
  logic inside the PCI manager class so that claiming/assigning the PF claims
  all of it's VFs and vice versa.

* Change the PCIDeviceStats class to expose PFs in it's pools, and change the
  claiming/consuming logic to claim appropriate amounts of VFs when a PF is
  consumed or claimed. Once this work item is complete, all of the scheduling
  and resource tracking logic will be aware of the PF constraint.

* Add support for specifying the PF requirement through the pci_alias
  configuration options, so that it can be requested through flavor
  extra-specs.


Dependencies
============

None


Testing
=======

Changes proposed here only extend existing functionality, so they will require
updating the current test suite to make sure new functionality is covered.
It is expected that the tests currently in place are to prevent any regression
to the existing functionality. No new test suites are required to be added for
this functionality, only new test cases.

Documentation Impact
====================

Documentation for the PCI passthrough features in Nova will need to be updated
to reflect the above changes - that is to say - no impact out of the ordinary.

References
==========

.. [1] https://review.openstack.org/#/c/182242/
.. [2] https://review.openstack.org/#/c/142094/

History
=======

Optional section for Mitaka intended to be used each time the spec
is updated to describe new design, API or any database schema
updated. Useful to let reader understand what's happened along the
time.

.. list-table:: Revisions
   :header-rows: 1

   * - Release Name
     - Description
   * - Mitaka
     - Introduced
