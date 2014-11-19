.. _kilo-priorities:

========================
Kilo Project Priorities
========================

List of priorities (in the form of use cases) the nova development team is prioritizing in Kilo.

For more information see: http://docs.openstack.org/developer/nova/devref/kilo.blueprints.html#project-priorities

+-------------------------+-----------------------+
| Priority                | Owner                 |
+=========================+=======================+
| `Cells V2`_             | `Andrew Laski`_       |
+-------------------------+-----------------------+
| `Objects`_              | `Dan Smith`_          |
+-------------------------+-----------------------+
| `Scheduler`_            | `Jay Pipes`_          |
+-------------------------+-----------------------+
| `V2.1 API`_             | `Christopher Yeoh`_,  |
|                         | `Ken'ichi Ohmichi`_   |
+-------------------------+-----------------------+
| `Functional testing`_   | `Sean Dague`_         |
+-------------------------+-----------------------+
| `Nova-network/Neutron   | `Mark McClain`_       |
| Migration`_             |                       |
+-------------------------+-----------------------+
| `No downtime DB         | `John Garbutt`_       |
| upgrades`_              |                       |
+-------------------------+-----------------------+
| `Bugs`_                 | `Sean Dague`_         |
+-------------------------+-----------------------+
| `CI`_                   | `Matt Riedemann`_     |
+-------------------------+-----------------------+


.. _Andrew Laski: https://launchpad.net/~alaski
.. _Dan Smith: https://launchpad.net/~danms
.. _Jay Pipes: https://launchpad.net/~jaypipes
.. _Christopher Yeoh: https://launchpad.net/~cyeoh-0
.. _Ken'ichi Ohmichi: https://launchpad.net/~oomichi
.. _Sean Dague: https://launchpad.net/~sdague
.. _Mark McClain: https://launchpad.net/~markmcclain
.. _John Garbutt: https://launchpad.net/~johngarbutt
.. _Matt Riedemann: https://launchpad.net/~mriedem


Cells v2
--------

Although the current Cells code is used in production by several large
deployments, the code is difficult to maintain and the implementation
is missing major features. The goal of this effort is to produce a
replacement for the current cells models, so cells become a first class Nova
citizen.

`cells etherpad <https://etherpad.openstack.org/p/kilo-nova-cells>`_


Objects
-------

Moving to objects makes the code easier to read and more maintainable for
developers and paves the way for online database migrations, one of the
main goals in `No downtime DB upgrades`_.

`objects etherpad <https://etherpad.openstack.org/p/kilo-nova-objects>`_

Scheduler
---------

This paves the way to pulling out the scheduler allowing for faster scheduler
development while reducing the scope of nova to help with nova's growth
challenges


`scheduler etherpad <https://etherpad.openstack.org/p/kilo-nova-scheduler-rt>`_

V2.1 API
---------

Pave the way for a better user experience by moving towards API microversions.

Functional testing
------------------

Nova currently has unit tests and integration testing but practically no
functional testing. This should make it easier to test and debug nova
race conditions and edge cases.

`functional testing etherpad <https://etherpad.openstack.org/p/kilo-nova-functional-testing>`_

Nova-network/Neutron migration
------------------------------

Finish making neutron the preferred networking model so nova can deprecate
nova-network and start the timer to removal. Reduces the scope of nova.

`neutron etherpad <https://etherpad.openstack.org/p/kilo-nova-nova-network-to-neutron>`_

No downtime DB upgrades
------------------------

Operators tell us one of the biggest pain points in upgrading is running the
database migrations, so we are fixing that with online database migrations.

`upgrades etherpad <https://etherpad.openstack.org/p/kilo-nova-zero-downtime-upgrades>`_

Bugs
-----

Nova is doing a bad job of managing bugs, a key way users provide feedback
to the developers.

CI
---

Test coverage, and specifically third party CI coverage, is always an issue.
We frequently say we require it but we don't do a great job of checking on
status, i.e. is a job responding quick enough and is accurate, should it be
voting or not, etc. Also, we ask for third party CI on new features but let
things get merged without enforcing the third party CI, and once the code is
in it's hard to remove it.

`CI etherpad <https://etherpad.openstack.org/p/nova-ci-status-checkpoint-kilo>`_

