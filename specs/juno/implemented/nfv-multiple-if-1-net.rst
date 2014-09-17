..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

====================================================================
Support multiple interfaces from one VM attached to the same network
====================================================================

https://blueprints.launchpad.net/nova/+spec/multiple-if-1-net

Permit VMs to attach multiple interfaces to one network to facilitate use
of common NFV network function VMs that require this form of attachment.

Problem description
===================

At present, Nova only permits a single VIF from each VM to be attached
to a given Neutron network.  If you attempt to attach multiple VIFs to
the same network, an error is issued, meaning that the second network
is not found from the list of networks remaining after the first
network is not used.

NFV functions occasionally require multiple interfaces to be attached
to a single network from the same VM, for reasons described below in
the 'use cases' section.  When this is required, the VNF generally
cannot be used under Openstack.

VNFs are often large, complex pieces of code, and may be supplied by third
parties.  For various reasons, it is not uncommon that it is necessary to
feed traffic out of an interface and into another interface (when the VNF
implements multiple functions and the functions cannot be chained internally)
or to feed traffic from e.g. the internet into multiple interfaces to run
them through separate processing functions internally.

The limitation can be seen as one of the VNF.  Clearly, the VNF could be
changed to put multiple addresses or functions on a single port (to fix the
incoming traffic issue) or to connect functions internally (to fix the
passthrough problem.

The problem with this solution is that the timescale for getting such a fix
is often prohibitive.  VNFs are large, complex pieces of code, and often the
supplier of the VNF is not the same organisation as that trying to use
the VNF within Openstack, necessitating a feature change request which may
well not be possible within reasonable timescales.

We propose changing the code within Nova to remove this limitation.

Proposed change
===============

We propose removing the limitation, which exists in Nova (Neutron has no such
limitation), allowing any number of VIFs to be attached to the same network.

The ordering in the nova 'boot' command or POST should be respected, so if
multiple interfaces are in use on the same network they are attached to the VM
in the order in which they are provided, as with other NICs.

API changes
-----------

When the attempt is made to attach multiple interfaces to a single
network, Nova will, instead of returning the error, attach multiple
interfaces to the same network and return a normal success code to the
'nova boot' attempt.

('nova interface-attach' already permits a second attachment to the same
network and needs no change.)

Alternatives
------------

It may be possible to work around this limitation by using multiple
ports on the same network and attach the VM to the ports, rather than
the same network twice.  This has not been tested.  On the other hand,
this indicates that the limitation is highly artificial and should, in
any case, be removed.  (In any case we should confirm this is possible
after the change and fix it if not.)

It is possible to boot the VM and use 'nova interface-attach' to get
multiple interfaces on the same network, but this requires the VM to support
PCI hotplug.

Data model impact
-----------------

None.

REST API impact
---------------

When the attempt is made to attach multiple interfaces to a single
network, Nova will, instead of returning the error, attach all
interfaces to the same network and return a normal success code to the
'nova boot' attempt.

Security impact
---------------

It is now going to be possible to bridge multiple interfaces together
within a VM and cause a broadcast storm.  It was always possible to
flood a Neutron network from a VM; this makes it easier.  It doesn't
make a security issue in and of itself but it certainly does make it a
little more straightforward to trigger one that arguably already
exists.

Notifications impact
--------------------

None.

Other end user impact
---------------------

None.  An end user using API calls that currently succeed will see no change
in behaviour in those APIs.  This only changes a case where an API currently
fails.

Performance Impact
------------------

None.

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

Primary assignee:
  ijw-ubuntu

Work Items
----------

* Change the Nova code, per the existing abandoned patch in
  https://review.openstack.org/#/c/26370 - which requires porting
  forward from the code in question to the current trunk.

* Add unit tests, which are missing from the abandoned patch.

Dependencies
============

None.

Testing
=======

Independently of this spec, tests should be added to Tempest:

* minimally, to ensure that traffic can be passed between the two
  interfaces on a VM created in this fashion

* optionally, traffic flow should be tested from another VM or
  external packet supplier to either of the interfaces.

Testing should be conducted with both the nova boot and nova
interface-attach methods.

Documentation Impact
====================

The change should be documented. No documentation exists for the
current behaviour.  Documentation exists for nova-network multinic
saying that VIFs are attached to separate networks but this is specific
to nova-network.

References
==========

* https://review.openstack.org/#/c/26370
* https://bugs.launchpad.net/nova/+bug/1166110
