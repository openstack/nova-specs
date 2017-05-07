..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

==================
 Add z/VM Support
==================

Add z/VM support in nova tree.

z/VM provides a highly secure and scalable enterprise cloud infrastructure
and an environment for efficiently running multiple diverse critical
applications on IBM z Systems and IBM LinuxONE with support for more
virtual servers than any other platform in a single footprint.
These z/VM virtual servers can run Linux, z/OS and more.
The detailed information can be found at http://www.vm.ibm.com/

Problem description
===================

z/VM

The z/VM driver team has met the following requirements
from the Nova core team by refer to previous virt driver integration.

* CI running and publishing results against Nova and nova-zvm driver:
  Results are publicly available, as well as the configuration of the CI.
  Per guidance from the Nova core team, the CI runs against all Nova change
  sets but is not currently voting on patches as it is not an in-tree driver.
  The `CI test logs`_ is also publicly available.

* External users beyond z/VM itself:
  Companies are actively using the z/VM driver to integrate into OpenStack
  clouds like SuSE; Canonical and RHEL are under discussion.
  Currently `Openmainframe project`_ is the major technical community and open
  project for mainframe enablement including openstack other open source
  projects.

* Show commitment to the driver:
  Our first supported release was Icehouse and we continue to maintain,
  extend the driver with each subsequent release, following the stable branch
  support model.  We are committed to developing the driver following the
  `OpenStack way`_, with open source code, open design/development, and an
  open community.  The z/VM driver fits the Nova compute driver design,
  and follows the community development direction.
  We also ensure that the development team is actively
  participating in upstream development - attending IRC meetings, mid-cycles,
  and summits.

.. _`CI test logs`:   http://extbasicopstackcilog01.podc.sl.edst.ibm.com/test_logs/
.. _`OpenStack way`: https://governance.openstack.org/reference/new-projects-requirements.html
.. _`Openmainframe project`: http://openmainframeproject.org/

Use Cases
---------

* A user should be able to deploy a glance-based image with basic networking on
  a system with the z/VM hypervisor. That image may be Linux (RHEL, SLES,
  Ubuntu, etc...).

Proposed change
===============

The change proposed is to submit a series of patches building out enough basic
function to support deployment of a glance-based virtual machine on z/VM.
This subset of the driver code (and associated unit tests) would support
features such as:

* Basic VM lifecycle tasks (spawn, shutdown, reboot, snapshot, etc)
* Instance status
* console output
* Flat/VLAN networking using the z/VM neutron agent
* Config drive

This phase of the driver is meant to get the net minimum of `mandatory` and
`choice` options from the `support matrix`_.

.. _`support matrix`: http://docs.openstack.org/developer/nova/support-matrix.html

We see this as a long-term journey.  We will continue to work to bring further
functionality into the Nova tree over subsequent releases.

Some of the specific functions supported in out-of-tree driver now
that would come as part of future blueprints that are not part of this one:

* Resize
* Live Migrate
* Cold Migrate
* Cinder Volume Support

Alternatives
------------

1) Integrate the entire driver.  That would be too unwieldy to do in one
   release and would require too much core reviewer time.

2) Do not integrate the driver.  As there are users of the driver, and the Nova
   direction is to have drivers in-tree, this is not an option.

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

Deployers who wish to use the z/VM driver will need to change the
``compute_driver`` in their conf to ``zvm.zVMDriver``.  The in-tree
z/VM driver will initially have a very limited set of functionality.  As
noted above, they can install the nova-zvm out-of-tree driver to gain the
additional functionality while the team works over multiple releases to
integrate the driver.

For this first integration, there will be no required configuration from the
deployer beyond setting the ``compute_driver`` type.  The driver will be
documented in the hypervisor support matrix (along with its capabilities
in-tree).

Developer impact
----------------

None

Implementation
==============

Assignee(s)
-----------

Primary assignee:
  jichenjc
  rhuang
  ychuang

Other contributors:

Work Items
----------

* Add support for basic life cycle tasks (Create, Power On/Off, Delete)

* Add console output

* Increase the scope of the existing z/VM CI to include the z/VM driver
  in-tree.  Two jobs will need to be kicked off for each Nova change (one
  for out-of-tree, one for in-tree) during this transition period.

Dependencies
============

None

Testing
=======

All code paths run through the standard Tempest tests as part of our CI.  The
code will also include significant unit test.  This code will come from the
out-of-tree nova-zvm driver.  The CI infrastructure will also continue to
support the automated testing of the out-of-tree nova-zvm driver.

Documentation Impact
====================

As there is no ID team now, we will primary work on following documents
and other doc that related to virt driver as well:

https://docs.openstack.org/nova/latest/admin/arch.html#hypervisors
https://docs.openstack.org/nova/latest/admin/configuration/hypervisors.html
http://docs.openstack.org/developer/nova/support-matrix.html

References
==========

* nova-zvm:
    * Overview: Out-of-tree Nova driver for z/VM
    * Source: `<https://git.openstack.org/cgit/openstack/nova-zvm-virt-driver/>`_
    * Bugs: `<https://bugs.launchpad.net/nova-zvm-virt-driver/>`_

* neutron-zvm-agent:
    * Overview: Open source z/VM neutron agent
    * Source: `<https://git.openstack.org/cgit/openstack/networking-zvm/>`_
    * Bugs: `<https://bugs.launchpad.net/networking-zvm/>`_

* ceilometer-zvm:
    * Overview: Ceilometer collector for the z/VM platform.  Captures I/O,
      CPU and memory statistics.
    * Source: `<https://git.openstack.org/cgit/openstack/ceilometer-zvm/>`_
    * Bugs: `<https://bugs.launchpad.net/ceilometer-zvm/>`_

History
=======

z/VM used to submit patches and has some discussions with nova community back
to 2013/2014 time frame. At that time we are lack of CI so we followed
guidelines in creating our CI and do more contributions to community.

And we had more effort in CI test and more cooperation with wider community
like Open mainframe project `<https://www.openmainframeproject.org/>`_
talked above, we want to continue our effort to make z/VM accepted
as in-tree plugin.

.. list-table:: Revisions
   :header-rows: 1

   * - Release Name
     - Description
   * - Queens
     - Introduced
