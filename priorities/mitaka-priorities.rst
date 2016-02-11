.. _mitaka-priorities:

=========================
Mitaka Project Priorities
=========================

List of themes (in the form of use cases) the nova development team is
prioritizing in Mitaka (in no particular order).

+-------------------------+-----------------------+
| Priority                | Primary Contacts      |
+=========================+=======================+
| `Cells V2`_             | `Andrew Laski`_       |
+-------------------------+-----------------------+
| `V2.1 API`_             | `Alex Xu`_,           |
|                         | `Sean Dague`_         |
+-------------------------+-----------------------+
| `Scheduler`_            | `Sylvain Bauza`_,     |
|                         | `Jay Pipes`_          |
+-------------------------+-----------------------+
| `OS VIF Lib`_           | `Daniel Berrange`_,   |
|                         | `Jay Pipes`_          |
+-------------------------+-----------------------+
| `Live Migrate`_         | `Paul Murray`_        |
+-------------------------+-----------------------+

.. _Andrew Laski: https://launchpad.net/~alaski
.. _Alex Xu: https://launchpad.net/~xuhj
.. _Sean Dague: https://launchpad.net/~sdague
.. _Sylvain Bauza: https://launchpad.net/~sylvain-bauza
.. _Jay Pipes: https://launchpad.net/~jaypipes
.. _Daniel Berrange: https://launchpad.net/~berrange
.. _Paul Murray: https://launchpad.net/~pmurray

Cells v2
--------

We started the cells v2 effort in Kilo.

During Mitaka we are focusing on making the default setup a single
cells v2 deployment.

In the N release, we hope to have support for multiple cells in a cells v2
deployment, including a way to migrate existing cells v1 deployments
to cells v2.

V2.1 API
---------

In Liberty, by default we now enable v2.1 for all API endpoints.

In Mitaka, we are going to focus on documenting the API, and work on
items that support the improved Service Catalog efforts.

Scheduler
---------

During Kilo we made much progress on cleaning up the interface between the
scheduler and the rest of Nova. In Liberty we added the request spec object.

In Mitaka we hope to complete the work around request spec and resource
objects. We also want to start looking at the service group API,
and more work on the resource tracker.

OS VIF Lib
----------

We plan to create a library that will contain all the VIF drivers, to make
it easer for Nova and the Neutron Stadium to work together.
It will also include creating a strong interface between Nova and Neutron.

Note: this is dependent on the PrivSep work that is being done to help
os-brick. That work is included in this priority due to the dependency.

Live Migrate
------------

Live Migrate currently has a lot of stability issues. Based on the experiences
of operators trying to use live migrate, lets look at making live migrate more
useful for those operators.

This will include both improving the test coverage around live-migrate, and
ensuring we document how to make best use of live migrate in production.
