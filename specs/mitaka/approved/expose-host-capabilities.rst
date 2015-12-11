..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

========================
Expose host capabilities
========================

https://blueprints.launchpad.net/nova/+spec/expose-host-capabilities

Ensuring proper scheduling can be a difficult task, especially when the
instances require several host features or capabilities. This would require the
administrators to know what features are available for a certain hypervisor
version and / or creating quite a few host aggregates, which can become
tedious.

Problem description
===================

Currently, the nova scheduler is not aware of all the host capabilities or
features the compute nodes might have. For example, certain features require a
minimum hypervisor version. The only way to handle this would be to set filters
(e.g. image property ``requires_hypervisor_version``) in order to ensure proper
scheduling. This is less than ideal, as it requires the administrators to know
which feature requires what hypervisor version. [1]

On top of this, there are some features that are not available without proper
configuration. Choosing to deploy an instance with such a feature on such a
node would fail. For example, Hyper-V Shielded VMs cannot be created on a
host that does not have the Host Guardian Service enabled and it is not
Guarded [2]. Or, Hyper-V vTPM feature does not exist in Windows 10 at all, but
it exists in Windows / Hyper-V Server 2016 and they share the same hypervisor
version (10.0).

Plus, the users might not be aware of each and every hypervisor specific
capability that they could have at their disposal. For example, Secure Boot
VMs for Windows guests are available starting with Windows / Hyper-V Server
2012 R2, while the newer versions offer this feature for both Windows and Linux
guests. This sort of capability can easily be reported by the compute nodes,
instead of having the look for this information online.

Finally, in heterogenous deployments (different hypervisors, different
hypervisor versions, different hardware), there could be N total host
capabilities, each compute node having a subset from those N capabilities.
Instances could require any combination of those N capabilities; creating a
host aggregate for each combination of capabilities in order to ensure proper
scheduling is unfeasible. Ideally, the scheduler could do feature-matching
instead.

Use Cases
----------

With this feature, most of the hypervisor specific features and other host
capabilities will be reported by the compute nodes. Hypervisor features will be
discovered automatically, meaning that users will not have to search for
information in order to find out what features are available to them.

In heterogenous deployments, instances requiring a certain subset of the
available host capabilities will be easier to deploy, as they won't require
a specific host aggregate that contains those capabilities.

Proposed change
===============

There are two types of host capabilities:

* **Hypervisor version related capabilities**: newer hypervisor versions can
  offer new features that can be added to the instances. (e.g.: secure boot,
  generation 2 VMs, etc.)

* **Undiscoverable capabilities**: cannot be determined easily or at all by
  the nova-compute service, mostly hardware related capabilites (e.g.: SSD,
  SR-IOV, fibre channel, etc.)

The method ``get_hypervisor_capabilities`` must be added to virt.ComputeDriver.
The driver will have to implement this method and return a ``HostCapabilities``
object containing the "hypervisor version related capabilities" mention in the
`Use Cases` section.

As for the "undiscoverable capabilities", a config option in the group
``host_capabilities`` can be defined for each capability.

All configured and reported capabilities must already exist as a field in the
HostCapabilities object. Any unknown capability detected will generate a
warning and will be ignored.

As for the capabilities present in the ``HostCapabilities`` model, they will
mirror the properties that can be in the image metadata or flavor extra specs,
in order to easily match requested features to host capabilites.

For example, the host could have the capability for instance secure boot. The
``HostCapabilities.os_secure_boot`` field will be set to True. In order to
request the instance secure boot feature, users will have to define the image
property ``os_secure_boot`` or flavor extra spec ``os:secure_boot`` as
``required`` [3].

A new filter will be implemented which will match the instance features
requested with the host capabilities as previously described. It will only
take into account fields defined in the ``HostCapabilities``. If a field in the
``HostCapabilities`` instance has not been set, that capability will be
considered as not present.

The host capabilities can be expressed as follows:

1. **Boolean**. For most cases, a host capability is simply a boolean: it is
present or not. In this case, an instance requiring a certain capability can
easily be matched with hosts which has that capability present or set to True.
For example, the instance's image metadata contains the property``os_vtpm``
set to ``required``. If the ``HostCapabilities`` instance ``os_vtpm`` field is
set to True, then that host is appropriate for that instance.

2. **Set of values**. In other cases, a host capability is expressed as a set
with different values. For example, the ``hw_machine_type`` capability [4],
which can have multiple values. In the Hyper-V's case, the mentioned field is
used to whether a VM is generation 1 or 2. Windows Hyper-V / Server 2012 R2 or
newer will report the values ['hyperv-gen1', 'hyperv-gen2'] for this
capability. For an instance with image metadata containing the property
``hw_machine_type`` set to ``hyperv-gen2``, a host will be considered
appropriate if the requested capability value exists in the
``HostCapabilities.hw_machine_type`` set.

Instances can also require multiple values from the same capabilities set
by expressing image properties / flavor extra spec values as lists (e.g.: image
property ``os_foo=bar1,bar2``).

3. **Ordered set of values**. In the case of host capabilities expressed as
ordered sets (e.g.: set element `i` is an enhanced version of element `i - 1`),
users can use logical operators to indicate what subset of a capability is
required by the instance. For example, If an instance requires the capability
``os_foo`` to be newer / greater or equal to ``bar1``, he will define the image
property as ``os_foo=>=bar1``.

Alternatives
------------

* Image property ``requires_hypervisor_version``: it requires administrators to
  know which feature requires what hypervisor version, plus there are features
  that cannot be determined by version alone.

* Host aggregates, grouping hosts by capabilities. This can become quite
  difficult when trying to deploy instances requiring multiple capabilities.

Data model impact
-----------------

The Text column ``host_capabilities`` will be added to the ``compute_node``
database table. This column will contain all the HostCapabilities objects,
reported by the compute nodes, serialized as a JSON blob. A database schema
migration is necessary in order to add the column.

New ``HostCapabilities`` object will be added, containing all the capabilities
currently acceptable by Nova. If any of the object's fields is not set, then
that capability will be considered as not present.

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

Drivers will have to implement the new ``get_host_capabilities`` method. It
should return an instance of ``HostCapabilities``.

In order for a new capability to be accepted in ``HostCapabilities``, a version
increment for will be necessary. If the capability's type is `undiscoverable`,
it will have to be added to the config option group ``host_capabilities``.

Implementation
==============

Assignee(s)
-----------

Primary assignee:
  Claudiu Belu <cbelu@cloudbasesolutions.com>

Work Items
----------

* ``host_capabilities`` column in ``compute_nodes`` table.
* ``HostCapabilities`` object model.
* ``host_capabilities`` config option group.
* add ``host_capabilities`` attribute in HostState.
* ``nova.virt.driver.ComputeDriver.get_host_capabilities`` method.
* drivers' ``get_host_capabilities`` implementation.
* new scheduler filter.

Dependencies
============

None

Testing
=======

* Unit tests.
* Jenkins.

Documentation Impact
====================

The new scheduler filter and the host capabilities that can be scheduled using
the new filter will have to be documented.
The new config option group ``host_capabilities`` will have to be documented.
The new nova API microversion will have to be documented.
The deployer impact will have to be documented.

References
==========

[1] #openstack-nova IRC discussion:
  http://eavesdrop.openstack.org/irclogs/%23openstack-nova/%23openstack-nova.2015-09-08.log.html#t2015-09-08T15:30:04

[2] Hyper-V vTPM / shielded VMs spec:
  https://review.openstack.org/#/c/195068/

[3] Hyper-V UEFI Secure Boot spec:
  https://review.openstack.org/#/c/190997/

[4] Hyper-V generation 2 VMs spec:
  https://review.openstack.org/#/c/103945/

History
=======
