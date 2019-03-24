..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

====================================
PowerVM Driver Integration - Phase 1
====================================

`<https://blueprints.launchpad.net/nova/+spec/powervm-nova-compute-driver>`_

The PowerVM driver has been developed out-of-tree, but with the intention to
provide an in-tree implementation.  Before it could be integrated in-tree, the
Nova core teams provided several requirements that have since been met.  This
blueprint is the first in a series that will work toward PowerVM driver
integration in-tree.


Problem description
===================

The PowerVM driver, which provides OpenStack enablement for AIX, IBM i and
Linux virtual machines running on a PowerVM hypervisor, is being proposed for
integration into the main Nova tree.  However, as the out-of-tree driver has
grown to contain a significant amount of function and maturity over the past
few OpenStack releases, the intention is to bring this driver in-tree.  The
work to drive towards full integration is expected to be driven over multiple
OpenStack releases.  This first blueprint is to provide minimal integration
into Nova for the Ocata release.

The PowerVM driver team has met the following requirements from the Nova core
team.

* CI running and publishing results against Nova and nova-powervm driver:
  Results are publicly available, as well as the configuration of the CI.  Per
  guidance from the Nova core team, the CI runs against all Nova change sets
  but is not currently voting on patches as it is not an in-tree driver.
  The `configuration for the CI`_ is also publicly available.

* External users beyond PowerVC:
  Companies are actively using the PowerVM driver to integrate into OpenStack
  clouds with Kolla and RDO.  The PowerVM driver team also has added PowerVM to
  the OpenStack-Ansible project and PowerVM is now a target platform for OSA.

* Show commitment to the driver:
  Our first supported release was Liberty and we continue to maintain, grow and
  extend the driver with each subsequent release, following the stable branch
  support model.  We are committed to developing the driver following the
  `OpenStack way`_, with open source code, open design/development, and an
  open community (IRC @ #openstack-powervm, etc).  The PowerVM driver fits
  the Nova compute driver design, and follows the community development
  direction.  We also ensure that the development team is actively
  participating in upstream development - attending IRC meetings, mid-cycles,
  and summits.

The out-of-tree driver will be maintained, supported and extended as the
in-tree driver is being integrated.  For this first phase, it is expected new
code will first be proposed to the out-of-tree driver and then proposed
in-tree. As the integration of the driver progresses further, that process
shifts to all code being proposed in-tree.  However, for any contribution
(either in-tree or out-of-tree), the primary contributors of this blueprint
will ensure the change is proposed to the other driver during this transition
period.

.. _`configuration for the CI`: https://github.com/powervm/powervm-ci
.. _`OpenStack way`: https://governance.openstack.org/reference/new-projects-requirements.html

Use Cases
---------

Phase 1 Use Cases:

* A user should be able to deploy a glance-based image with basic networking on
  a system with the PowerVM hypervisor. That image may be Linux (RHEL, SLES,
  Ubuntu, etc...), AIX or IBM i.

* The `PowerVM live migration object`_ should be integrated into core Nova.

.. _`PowerVM live migration object`: https://github.com/openstack/nova-powervm/blob/master/nova_powervm/objects/migrate_data.py

Proposed change
===============

The change proposed is to submit a series of patches building out enough basic
function to support deployment of a glance-based virtual machine on PowerVM.
This subset of the driver code (and associated unit tests) would support
features such as:

* Basic VM lifecycle tasks (launch, shutdown, reboot, snapshot, etc)
* Instance status
* VNC console
* Flat/VLAN networking using the Open vSwitch Neutron agent
* Config drive

The phase 1 of the driver is meant to get the net minimum of `mandatory` and
`choice` options from the `support matrix`_.

.. _`support matrix`: http://docs.openstack.org/developer/nova/support-matrix.html

The nova-powervm live migration object will also be integrated to reduce
friction that operators have expressed.  Integration of the object makes it
easier for existing operator deployments.

In subsequent releases we will work to bring further function into the Nova
tree, but we see this as a long-term journey.

Some of the specific functions that would come as part of future blueprints
that are not part of this one:

* Resize
* Live Migrate
* Cold Migrate
* Cinder Volume Support
* Shared Ethernet Support (PowerVM network technology)

There are additional functions (that are currently integrated in the
out-of-tree driver), but they will be proposed as part of subsequent
blueprints.

Alternatives
------------

1) Integrate the entire driver.  That would be too unwieldy to do in one
   release and would require too much core reviewer time.

2) Do not integrate the driver.  As there are users of the driver, and the Nova
   direction is to have drivers in-tree, this is not an option.

3) Officially support out-of-tree drivers via Nova.  Allow integration of
   driver objects that are required in-tree to be added for out-of-tree
   drivers (e.g. the live migration object).  This was discussed at one point
   but at the time was decided to not be ideal (as all the official drivers
   are in-tree).

Data model impact
-----------------

No core data model impact.  The live migration object for PowerVM would be
integrated.

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

None.  Integration has no performance effect on existing code paths.

Other deployer impact
---------------------

Deployers who wish to use the PowerVM driver will need to change the
``compute_driver`` in their conf to ``powervm``.  The in-tree PowerVM driver
will initially have a very limited set of functionality.  As noted above, they
can install the nova-powervm out-of-tree driver to gain the additional
functionality while the team works over multiple releases to integrate the
driver.

For this first integration, there will be no required configuration from the
deployer beyond setting the ``compute_driver`` type.  The driver will be
documented in the hypervisor support matrix (along with its capabilities
in-tree).

A new dependency on ``pypowervm`` will be introduced .  This is a third-party,
open-source library that allows its consumers to drive PowerVM virtualization.

The PowerVM live migration object will be integrated into Nova.  Even though it
uses features that won't yet be available in the integrated PowerVM driver, it
eases the burden on the deployers using the out-of-tree driver (during the
transition period) so that they do not have to install nova-powervm on the
controller node.  We have multiple deployers citing that this is a challenge to
their existing deployments.

Developer impact
----------------

There are no changes to the driver API.  The PowerVM driver will conform to the
existing Nova API.

Implementation
==============

Assignee(s)
-----------

Primary assignees:
  efried
  esberglu
  thorst

Other contributors:
  wangqinw
  adreznec

Work Items
----------

* Add the pypowervm dependency

* Create the powervm driver directory

* Add support for basic life cycle tasks (Create, Power On/Off, Delete)

* Add support for OVS-based networks

* Add the PowerVM live migration object to nova

* Add console support via VNC

* Increase the scope of the existing PowerVM CI to include the PowerVM driver
  in-tree.  Two jobs will need to be kicked off for each Nova change (one
  for out-of-tree, one for in-tree) during this transition period.


Dependencies
============

* `pypowervm`_ - third-party, open-source library that allows for control of
  the PowerVM platform.

* PowerVM with `NovaLink`_ - PowerVM is the hypervisor, and the NovaLink is a
  Linux based Virtualization Management VM.  The Novalink virtualization
  management VM is what allows the nova-compute process to run on the system
  itself.

.. _`pypowervm`: http://github.com/powervm/pypowervm
.. _`NovaLink`: http://www-01.ibm.com/common/ssi/cgi-bin/ssialias?subtype=ca&infotype=an&supplier=897&letternum=ENUS215-262


Testing
=======

All code paths run through the standard Tempest tests as part of our CI.  The
code will also include significant unit test.  This code will come from the
out-of-tree nova-powervm driver.  The CI infrastructure will also continue to
support the automated testing of the out-of-tree nova-powervm driver.

Voting will be enabled for the CI for the in-tree driver only.  Per our
discussions with the Nova core team, we will not enable voting for the
out-of-tree driver.  However, logs for both runs are publicly available, and we
have dedicated team members monitoring and supporting the CI.

No new tests are required.  The PowerVM driver is meant to conform to the
Nova model.

Outside testing will be done to validate performance and scale.  This has
already been done on the out-of-tree driver.  RefStack compliance will also be
validated, but we do not expect this first phase to pass as it does not have
all of the required support out of the box.


Documentation Impact
====================

We will work with the ID team to create new documents on the PowerVM driver.
A proposed update to the hypervisor driver matrix will be made as well.

References
==========

* nova-powervm:
    * Overview: Out-of-tree Nova driver for PowerVM
    * Source: `<https://git.openstack.org/openstack/nova-powervm/>`_
    * Bugs: `<https://bugs.launchpad.net/nova-powervm/>`_

* pypowervm
    * Overview: third-party, open-source module providing access to PowerVM
      hypervisor functionality.
    * Source: `<https://github.com/powervm/pypowervm/tree/develop>`_
    * Bugs: `<https://bugs.launchpad.net/pypowervm/>`_

* networking-powervm:
    * Overview: Neutron ML2 mechanism driver and plugin supporting PowerVM's
      Shared Ethernet Adapter and (as of newton) SR-IOV virtual NIC.
    * Source: `<https://git.openstack.org/openstack/networking-powervm/>`_
    * Bugs: `<https://bugs.launchpad.net/networking-powervm/>`_

* ceilometer-powervm:
    * Overview: Ceilometer collector for the PowerVM platform.  Captures I/O,
      CPU and memory statistics.
    * Source: `<https://git.openstack.org/openstack/ceilometer-powervm/>`_
    * Bugs: `<https://bugs.launchpad.net/ceilometer-powervm/>`_

* Continuous Integration:
    * Overview: The CI server's configuration
    * Tempest Configuration: `<https://github.com/powervm/powervm-ci/blob/master/tempest/tempest.conf>`_

History
=======

Historically speaking, there have been a couple other Power drivers.  The first
PowerVM driver was built on PowerVM and only worked with a component called
IVM.  The challenge with this was that it required the nova-compute to run on
a separate server and SSH in to issue commands.  It also did not integrate
well with other OpenStack components.

There was also the PowerVC OpenStack driver.  This sat on top of PowerVC and
was a clustered management model.  Due to the push away from clustered
management, this was not the approved management model for OpenStack Nova
Compute.  It was never pulled in-tree.

This model is different, with core changes to the PowerVM hypervisor.  It has
been shipping in the field for a long period of time, and has products built on
top of it.  It also matches the development model of OpenStack Nova and has
dedicated developers who have been working on it for multiple years.

Lastly, Power systems also natively run Linux.  For those wishing to use KVM
on Power, the standard libvirt driver is also available.  However, that support
is limited to Linux based client virtual machines.

A rough timeline is provided below.

* November 2013: PowerVM IVM driver removed due to lack of CI and development.
  Also did not fit the direction of Nova core team to have the Nova compute
  process running on the system itself.

* October 2014: `First commit`_ for new PowerVM driver built on NovaLink.

* May 2015: Socialized the NovaLink based PowerVM driver at the summit.
  NovaLink changes the hypervisor itself to match the OpenStack model.  All
  OpenStack code was developed from the start as open source.

* October 2015: Liberty based out-of-tree nova-powervm driver released.

  All developed openly.  Support for:
    * Lifecycle operations
    * Spawn from glance
    * Cinder FC support
    * Nova with networking-powervm agent
    * Live Migration
    * AIX and Linux VMs
    * DevStack
    * TaskFlow in its core to support graceful rollbacks of failed operations

* January 2016: Continuous Integration environment live.

* April 2016: nova-powervm driver updated for Mitaka release.

  All nova-powervm development done openly during the release.  Initial
  third-party contributions made.

  Added new capabilities:
    * Cold Migration / Rebuild / Resize
    * Scalability testing
    * Basic VNC Console
    * IBM i VMs
    * Scale & Resiliency testing

* July 2016: CI running against all Nova patch sets.  Not voting (due to
  Nova core team guidance) but logs still published to log server.

* October 2016: nova-powervm driver updated for Newton release.  Updated for:
    * SR-IOV via PowerVM vNIC
    * Linux Bridge / OVS
    * Enhancements to VNC console
    * Integration with OpenStack Ansible (outside nova-powervm)

.. _`First commit`: https://github.com/openstack/nova-powervm/commit/095e1c183baf4f9083d6b0d363818be21f64f992

.. list-table:: Revisions
   :header-rows: 1

   * - Release Name
     - Description
   * - Ocata
     - Introduced
