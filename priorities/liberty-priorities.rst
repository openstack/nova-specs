.. _liberty-priorities:

===========================
Liberty Project Priorities
===========================

List of priorities (in the form of use cases) the nova development team is
prioritizing in Liberty (in no particular order).

+-------------------------+-----------------------+
| Priority                | Owner                 |
+=========================+=======================+
| `Cells V2`_             | `Andrew Laski`_       |
+-------------------------+-----------------------+
| `V2.1 API`_             | `Ken'ichi Ohmichi`_,  |
|                         | `Sean Dague`_         |
+-------------------------+-----------------------+
| `Scheduler`_            | `Jay Pipes`_          |
+-------------------------+-----------------------+
| `Upgrades`_             | `Dan Smith`_          |
+-------------------------+-----------------------+
| `DevRef Update`_        | `John Garbutt`_       |
+-------------------------+-----------------------+

.. _Andrew Laski: https://launchpad.net/~alaski
.. _Ken'ichi Ohmichi: https://launchpad.net/~oomichi
.. _Sean Dague: https://launchpad.net/~sdague
.. _Jay Pipes: https://launchpad.net/~jaypipes
.. _Dan Smith: https://launchpad.net/~danms
.. _John Garbutt: https://launchpad.net/~johngarbutt


Priorities without a clear plan
-------------------------------

Here are some things we would like to be a priority, but we are currently
lacking either a clear plan or someone to lead that effort:

* A plan for the future of flavors, image properties and host aggregates
* Tasks for API triggered operations
* Simplify Quotas
* Revisit how we talk to Glance, Neutron and Cinder APIs
* Neutron/Nova-network integration (Fast Path, VIF plug)
* Feature Test Classification
* Fixing more bugs

`John Garbutt`_ will work with the Nova community to get backlog specs defined
for all of the above. Firstly, it will make clear the scope of each bullet.
Secondly, we hope it will then be easier to then find help addressing these
items.

Should we find people to work on these items, it is possible we might promote
them to an official priority later in the release, should there appear to be
room in the review pipeline.

Cells v2
--------

We started the cells v2 effort in Kilo. During Liberty are are focusing on
making the default setup a single cells v2 deployment.

In the M release, we hope to have support for multiple cells in a cells v2
deployment, including a way to migrate existing cells v1 deployments
to cells v2.

V2.1 API
---------

Complete the work around API microversions, with a particular focus on
documentation, tempest coverage and python-novaclient support.
We also need to define the policy around when to bump the API microversion
and what changes are allowed in a microversion bump.

We are explicitly excluding work on porting any cosmetic changes from the
previous v3 API efforts into new API microversions.

Scheduler
---------

During Kilo we made much progress on cleaning up the interface between the
scheduler and the rest of Nova.

In Liberty we hope to complete the work around request spec and resource
objects. We also want to start looking at the service group API,
and more work on the resource tracker.

Upgrades
---------

While we have made great strides with our upgrades in the last few releases,
there are several items related to database migrations that need completing.

Firstly, we need to fully document our new online data migration approach that
we tested out during kilo to perform the flavor migration from system metadata
to instance extra. In addition, we should tidy up the documentation around
how we bump RPC and object versions across release boundaries to remove
technical debt.

Secondly, we must complete the first step towards us having online schema
migrations, by splitting the schema migrations into an expand and contract
phase.

Thirdly, we must complete the final parts of converting all code to access
the database via DB objects.

DevRef Update
--------------

A key part of being able to scale out the Nova team is doing a better job of
sharing information on how the Nova community operates, how the Nova
architecture works, the basic design tenets we are using,
the scope of Nova, and so on.

The main goal is to make it easier to on-board new Nova contributors and
make it easier to discover any decisions that have been already made by the
community.
