..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

============================
Add a virt driver for Ironic
============================

https://blueprints.launchpad.net/nova/+spec/add-ironic-driver

This specification proposes to add a virt driver to enable Nova to deploy
images to bare metal resources by using the OpenStack Bare Metal Provisioning
Service ("Ironic").

Problem description
===================

The community has split out the functionality of provisioning bare metal
servers into a separate program, which includes the ironic and
python-ironicclient projects. The original intent of the
nova.virt.baremetal driver was two-fold:

- to provide physical machines more suitable to HPC-style workloads,
  eg where virtualization overhead is too high;
- to be an experimental proof-of-concept for enabling the TripleO project.

In order to address scalability and architectural concerns affecting both
use-cases, this driver was split out into a separate OpenStack Program,
and developed over the last year as such.

Proposed change
===============

This proposal aims to enable Nova to use Ironic to perform the same functions
which it is currently able to perform via the nova.virt.baremetal driver.
This abstracts the details of physical hardware within Ironic, such that the
user interacts with Nova in the same way when deploying instances to virtual or
physical machines. The hardware-specific details are only exposed to the cloud
operators.

Specifically, this will:

* add the nova.virt.ironic driver, which will use the python-ironicclient
  library to interact with Ironic's REST API for the purpose of provisioning
  physical machines.

* add new IronicHostManager class, similar to BaremetalHostManager, which
  fills the same purpose but is specific to Ironic. Namely, this provides
  several customizations to Nova's HostManager, tailoring it to consuming
  discrete and non-subdivisible physical resources.

* add exact-match scheduler filters, to facilitate users who wish to match
  nova flavor to hardware specifications exactly. The best matching possible
  today is greater-than-or-equal, which is often undesirable (eg. because
  a machine with 128GB of RAM could be selected to fulfil a request for an
  instance with 16GB of RAM).

This driver will initially implement a subset of the Nova virt driver API
sufficient to support the same functionality that the nova.virt.baremetal
driver supported. Over time, additional functionality will be added, as
appropriate and possible for physical hardware. It is expected that some
operations may never be added to this driver, eg when the operation is not
possible where there is no local hypervisor.

This driver will expose the complete resources of the ironic service it is
connected to. Therefor, running multiple nova-compute processes within a
single cell or region will not be possible, and HA for the nova-compute
service must be achieved externally, eg. via pacemaker+corosync. Scale-out
may be achieved by running multiple ironic clusters, with a single n-cpu
connected to each ironic end-point. This is not optimal, and is a result
of a current limitation within Nova. See the Alternatives section below
for a summary of the discussion which has occurred around this limitation.

Alternatives
------------

One alternative would be for users to directly interact with Ironic's API,
circumventing Nova when deploying instances to bare metal. This would require
Ironic to duplicate a significant amount of functionality present in Nova, and
violate the abstraction layer. Note that giving end-users direct access to
Ironic's API may present security concerns for some operators; see the
Security Impact section below for a discussion of this.

Instead of creating a new IronicHostManager class, the existing
BaremetalHostManager class could be refactored to support both drivers.

Instead of adding exact-match scheduler filters, we could create a new
scheduler that is specifically geared towards non-divisible resources.
However, this approach is sufficient for many use cases, and does not prevent
the later creation of another scheduler.

An alternative was proposed which would allow multiple nova-compute processes
to proxy for the same Ironic service end-point at the same time. This could be
done by setting the same 'host' property on each nova-compute service, such
that they expose the same set of resources.  Therefor, certain operations would
need to be skipped when starting the nova-compute process (eg, so it doesn't
trample over an ongoing operation on another compute host). This would be
accomplished by creating a new ClusteredComputeManager class (subclassed from
ComputeManager) which would override init_host() to avoid the call to
InstanceList.get_by_host(), self._destroy_evacuated_instances() and
self._init_instance(). This proposal was denied due to architectural concerns
within Nova, specifically around @utils.synchronize(instance['uuid']) calls,
and event callbacks that could be routed to a host other than the one waiting
for the callback.

Instead of overriding ComputeManager.init_host(), a significant rewrite of
Nova's internal resource model could be undertaken -- eg, to remove the (host,
hypervisor_hostname) tuple from all places within the code and make the
nova-conductor process handle resource locking for clustered hypervisors, such
as Ironic.  This would be a significant undertaking, and while merited, it was
agreed that this work would not block the Ironic driver.


Data model impact
-----------------

Adding the nova.virt.ironic driver will not impact the db model.

Some additional extra_specs may be leveraged in faciliating better scheduling
in the future. There is precedent in the way that the nova.virt.baremetal
driver leverages extra_specs:baremetal:cpu_arch. Ironic may extend this to
support additional hardware metadata in the future.

REST API impact
---------------

The nova.virt.ironic driver will not add any REST API extensions or require
changes to any of Nova's APIs.

Security impact
---------------

Allowing Nova to provision physical hardware has significant security
implications. The nova.virt.baremetal driver required direct access to the OOB
management (IPMI) network of the hardware it managed. A compromise of
nova-compute would expose that hardware's management interface.

In a properly-secured OpenStack deployment, security will be improved by moving
this functionality out of nova-compute and into ironic-conductor, because there
is a strict API between the two services.

The ironic-api should not be reachable or discoverable by end-users, and only
the ironic-conductor service should have access to the hardware management
interface.  The user of Nova who requests an instance on bare metal will thus
have no direct access to the services managing that bare metal host. Should
nova-compute be compromised, the malicious user would still need to gain access
to the ironic-conductor host before having any access to the hardware
management interface.

Considering how often IPMI is not properly secured, and that in many cases it
can not be secured, the OOB management network should be as isolated from users
as possible.

Notifications impact
--------------------

None

Other end user impact
---------------------

None

Performance Impact
------------------

No impact on Nova itself.

The performance profile of the nova.virt.ironic driver will be different than
other virt drivers due to the nature of managing physical machines. For
example, power cycling bare metal often takes more than five minutes as the
hardware must complete a POST cycle. Thus, a deploy may be expected to take a
minimum of ten minutes, though depending on the hardware, it may be more or
less.

Other deployer impact
---------------------

Deploying Nova with the nova.virt.ironic driver will be considerably different
to deploying Nova with other virt drivers, and also different from the
nova.virt.baremetal driver. Main areas of difference are:

* different system libraries will be required. No local hypervisor needs be
  installed, and none of the system libraries to enable baremetal need to be
  installed on the compute host itself.

* the OpenStack Ironic services must be properly set up and discoverable
  via Keystone in order for the nova.virt.ironic driver to function properly.

* Nova must be supplied with admin credentials capable of interacting
  with Ironic.

An upgrade path from the nova.virt.baremetal driver to the nova.virt.ironic
driver will be provided. The details of that are proposed in another document:

  https://blueprints.launchpad.net/nova/+spec/deprecate-baremetal-driver

Developer impact
----------------

None

Implementation
==============

Assignee(s)
-----------


Primary assignee:
  devananda

Other contributors:
  lucasagomes
  nobodycam

Work Items
----------

* Merge auxiliary components: HostManager and exact-match scheduler filters

* Delete auxiliary components from Ironic's tree

* Split the nova.virt.ironic driver into a series of patches, the sum of
  which will pass unit and functional tests.

* Delete driver from Ironic's tree after it has merged in Nova.


Dependencies
============

None

Testing
=======

There is already tempest testing being done upstream against changes in
ironic, nova, devstack, and tempest. However, it is non-voting today.
The following paragraph describes how it works.

Devstack creates a "mock" bare metal node, enrolls it with Ironic, and
configures Nova appropriately to use the nova.virt.ironic driver. A tempest
scenario test is then run against that devstack instance, which allows tempest
to test functionality appropriate for this driver. Certain tests may be
excluded when the functionality does not apply to bare metal (eg,
live migrate). The current test is fairly simple: validate the boot process,
network connectivity of the instance, and validate destroy. Additional tests
have been proposed for more coverage, eg. "rebuild --preserve-ephemeral".

Testing of functionality not exposed via the nova virt driver interface is done
directly in Tempest via the Ironic API (eg, management operations) and is
mentioned here only for completeness.

Documentation Impact
====================

Documentation should be added to Nova stating the existence of the new driver,
and should include links to the Ironic project's developer and deployer
documentation.

References
==========

Current code, in Ironic's git tree::
  http://git.openstack.org/cgit/openstack/ironic/tree/ironic/nova

Devstack support for testing this driver::
  http://git.openstack.org/cgit/openstack-dev/devstack/tree/lib/ironic
  http://git.openstack.org/cgit/openstack-dev/devstack/tree/tools/ironic

Tempest test which deploys using the nova.virt.ironic driver::
  http://git.openstack.org/cgit/openstack/tempest/tree/tempest/scenario/test_baremetal_basic_ops.py

Juno summit etherpad discussing this::
  https://etherpad.openstack.org/p/juno-nova-deprecating-baremetal

Some best practices for IPMI sanity::
  http://fish2.com/ipmi/bp.pdf

Discussions of IPMI vulnerabilities::
  http://fish2.com/ipmi/itrain.pdf
  http://fish2.com/ipmi/river.pdf
