..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

====================
XenAPI vCPU Topology
====================

https://blueprints.launchpad.net/nova/+spec/xenapi-vcpu-topology

The proposal is to add support for vCPU topology for XenAPI.  It will utilize
the work done on the virt-driver-vcpu-toplogy blueprint.  Most of this
blueprint has been copied from the virt-driver-vcpu-topology blueprint as
they align well but differ slightly on implementations per hypervisor.

Problem description
===================

See Virt Driver VCPU Topology spec referenced at the end of blueprint.

Proposed change
===============

See Virt Driver VCPU Topology spec referenced at the end of blueprint.

For XenServer implementation the following configurations will be used:

* hw:cpu_sockets=NN - preferred number of sockets to expose to the guest
* hw:cpu_cores=NN - preferred number of cores to expose to the guest
* hw:cpu_max_sockets=NN - maximum number of sockets to expose to the guest
* hw:cpu_max_cores=NN - maximum number of cores to expose to the guest

At the image level the exact same set of parameters will be permitted,
with the exception that image properties will use underscores throughout
instead of an initial colon.

* hw_cpu_sockets=NN - preferred number of sockets to expose to the guest
* hw_cpu_cores=NN - preferred number of cores to expose to the guest
* hw_cpu_max_sockets=NN - maximum number of sockets to expose to the guest
* hw_cpu_max_cores=NN - maximum number of cores to expose to the guest

Note that XenServer does not have a specific setting for number of threads
so setting threads will not function on XenServer currently.

Alternatives
------------

None, will utilize existing work done in virt-driver-vcpu-topology blueprint

Data model impact
-----------------

No impact.

The new properties will use the existing flavour extra specs and image
property storage models.

REST API impact
---------------

No impact.

The new properties will use the existing flavour extra specs and image
property API facilities.

Security impact
---------------

The choice of sockets vs cores can have an impact on host resource utilization
when NUMA is involved, since over use of cores will prevent a guest being
split across multiple NUMA nodes. This feature addresses this by allowing the
flavour administrator to define hard caps, and ensuring the flavour will
always take priority over the image settings.

Notifications impact
--------------------

No impact.

There is no need for this feature to integrate with notifications.

Other end user impact
---------------------

The user will gain the ability to control aspects of the vCPU topology used
by their guest. They will achieve this by setting image properties in glance.

Performance Impact
------------------

The cores vs sockets vs threads decision does not involve any scheduler
interaction, since this design is not attempting to match host topology
to guest topology. A later blueprint on CPU pinning will make it possible
todo such host to guest topology matching, and its performance impact
will be considered there.

Other deployer impact
---------------------

The flavour extra specs will gain new parameters in extra specs which a
cloud administrator can choose to use. If none are set then the default
behaviour is unchanged from previous releases.

Developer impact
----------------

Implementation will add support for XenAPI drivers.

Implementation
==============

Assignee(s)
-----------

Primary assignees:
  antonym
  johngarbutt

Work Items
----------

* Add XenAPI driver support for choosing a CPU topology solution based on
  the given hw_cpu_* parameters.

Dependencies
============

No external dependencies

Testing
=======

Testing of this feature will be covered by the XenServer CI.

Documentation Impact
====================

The new flavour extra specs and image properties will need to be documented.
Guidance should be given to cloud administrators on how to make most
effective use of the new features. Guidance should be given to the end user
on how to use the new features to address their use cases.

References
==========

* Virt Driver VCPU Topology:
  https://blueprints.launchpad.net/nova/+spec/virt-driver-vcpu-topology

* Information on cores-per-socket in XenServer:
  https://support.citrix.com/article/CTX126524
