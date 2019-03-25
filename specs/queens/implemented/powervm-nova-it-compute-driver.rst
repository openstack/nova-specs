..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

==========================================
PowerVM Driver Integration - Queens
==========================================

`<https://blueprints.launchpad.net/nova/+spec/powervm-nova-it-compute-driver>`_

The PowerVM driver provides OpenStack enablement for AIX, IBM i and Linux
virtual machines running on a PowerVM hypervisor. It has been developed
out-of-tree, but with the intention to provide an in-tree implementation.
Before it could be integrated in-tree, the Nova core teams provided several
requirements that have since been met. The integration process began in Pike
and a limited subset of functionality was implemented in-tree. This blueprint
will expand on that beginning by integrating additional PowerVM driver
functionality for Queens.

Problem description
===================

The out-of-tree driver has grown to contain a significant amount of function
and maturity over the past few OpenStack releases. The work to drive towards
full integration is expected to continue over multiple OpenStack releases. The
first blueprint provided integration of the PowerVMLiveMigrateData object into
Nova for the Ocata release, and laid out plans to incorporate minimal compute
driver functionality incrementally. During Pike some of the basic driver
functionality was introduced which is detailed below in the history section.
This blueprint continues that work.

The out-of-tree driver will be maintained, supported and extended as the
in-tree driver is being integrated.  In general for this phase, it is expected
that new code will first be proposed to the out-of-tree driver and then
proposed in-tree. As the integration of the driver progresses further, that
process shifts to all code being proposed in-tree.  However, for any
contribution (either in-tree or out-of-tree), the primary contributors of this
blueprint will ensure the change is proposed to the other driver during this
transition period.

Use Cases
---------
* A user should be able to deploy a glance-based image with either `Shared
  Ethernet Adapter`_ (SEA) or Open vSwitch (OVS) networking on a system with
  the PowerVM hypervisor.

* A user should be able to boot using config drive

* A user should be able to attach and detach `vSCSI`_ cinder volumes

.. _`Shared Ethernet Adapter`: https://www.ibm.com/support/knowledgecenter/en/POWER8/p8hb1/p8hb1_vios_concepts_network_sea.htm

.. _`vSCSI`: https://www.ibm.com/support/knowledgecenter/en/8284-21A/p8hat/p8hat_virtualscsi.htm

Proposed change
===============

The proposed change is to submit a series of patches to build on the basic
functionality implemented in Pike. The new subset of driver code would support
the following features.

* Config drive
* SEA-based networking
* OVS-based networking
* vSCSI cinder volume attach/detach

This does not bring the entirety of the PowerVM out-of-tree driver in-tree.
There are other features that will not be implemented in-tree this release.
Implementing the PowerVM driver in-tree is a long-term process that will
continue through multiple OpenStack releases.

Alternatives
------------

None. The multi-release goal of integrating the PowerVM driver began in Pike,
and other than abandoning this effort there is no alternative. Implementing the
rest of the driver this release is too vast of a task and would take too much
core reviewer time.

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

None. Integration has no performance effect on existing code paths.

Other deployer impact
---------------------

Deployers who wish to use the PowerVM driver will need to change the
``compute_driver`` in their conf to ``powervm.driver.PowerVMDriver``. The
in-tree PowerVM driver implemented a very limited set of functionality in Pike.
Deployers can install the nova-powervm out-of-tree driver to gain the
additional functionality while the team works over multiple releases to
integrate the driver.

The driver will be documented in the hypervisor support matrix (along with its
capabilities in-tree) and any additional configuration options will be
documented.

A new dependency on ``pypowervm`` was introduced in Ocata.  This is a
third-party, open-source library that allows its consumers to drive PowerVM
virtualization. The pypowervm version requirement will be updated as needed
throughout the Queens release.

Developer impact
----------------

There are no changes to the driver API. The PowerVM driver will conform to the
existing Nova API.

Upgrade impact
--------------

None

Implementation
==============

Assignee(s)
-----------

Primary assignees:
  efried
  esberglu
  edmondsw

Other contributors:
  thorst

Work Items
----------

* Add config drive support

* Add support for OVS-based networks

* Add support for SEA-based networks

* Add vSCSI cinder volume support

* Update PowerVM CI to stay up to date with new in-tree functionality as it is
  implemented.

Dependencies
============

* `pypowervm`_ - third-party, open-source library that allows for control of
  the PowerVM platform.

* PowerVM with `NovaLink`_ - PowerVM is the hypervisor, and the NovaLink is a
  Linux based Virtualization Management VM. The Novalink virtualization
  management VM is what allows the nova-compute process to run on the system
  itself.

.. _`pypowervm`: http://github.com/powervm/pypowervm
.. _`NovaLink`: https://www.ibm.com/support/knowledgecenter/en/POWER8/p8eig/p8eig_kickoff.html

Testing
=======

All code paths run through the standard Tempest tests as part of our CI. The
code will also include significant unit test. This code will come from the
out-of-tree nova-powervm driver. The CI infrastructure will also continue to
support the automated testing of the out-of-tree nova-powervm driver.

PowerVM CI will post run results for both the out-of-tree and in-tree driver
for all nova changesets. All logs will be publicly available. Non-gating votes
will be provided by PowerVM CI. We have dedicated team members monitoring and
supporting the CI.

No new tests are required. The PowerVM driver is meant to conform to the
Nova model.

Documentation Impact
====================

We will continue to work with the ID team to update and create new documents
for the PowerVM driver. The hypervisor support matrix will be updated as new
functionality is implemented.

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
    * CI Configuration: `<https://github.com/powervm/powervm-ci/tree/master>`_

History
=======

Historically speaking, there have been a couple of other Power drivers.  The
first PowerVM driver was built on PowerVM and only worked with a component
called IVM.  The challenge with this was that it required the nova-compute to
run on a separate server and SSH in to issue commands.  It also did not
integrate well with other OpenStack components.

There was also the PowerVC OpenStack driver.  This sat on top of PowerVC and
was a clustered management model.  Due to the push away from clustered
management, this was not the approved management model for OpenStack Nova
Compute.  It was never pulled in-tree.

This model is different, with core changes to the PowerVM hypervisor.  It has
been shipping in the field for a long period of time, and has products built on
top of it.  It also matches the development model of OpenStack Nova and has
dedicated developers who have been working on it for multiple years.

Lastly, Power systems also natively run Linux.  For those wishing to use KVM on
Power, the standard libvirt driver is also available.  However, that support is
limited to Linux based client virtual machines.

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

* October 2016: `First in-tree change set`_ proposed for compute driver
  spawn/destroy.

* November 2016: PowerVMLiveMigrateData object introduced in-tree (Ocata).

* January 2017: pypowervm dependency introduced in requirements project
  (Ocata).

* August 2017: Pike Release - `Phase 1`_ implemented including
    * Full flavor spawn and destroy
    * Power on/off and reboot
    * VNC console support
    * PowerVM Shared Storage Pool ephemeral disk support

.. _`First commit`: https://github.com/openstack/nova-powervm/commit/095e1c183baf4f9083d6b0d363818be21f64f992

.. _`First in-tree change set`: https://review.openstack.org/#/c/391288/

.. _`Phase 1`: https://blueprints.launchpad.net/nova/+spec/powervm-nova-compute-driver

.. list-table:: Revisions
   :header-rows: 1

   * - Release Name
     - Description
   * - Ocata
     - Introduced
   * - Pike
     - Phase 1 implemented
   * - Queens
     - Phase 2 proposed
