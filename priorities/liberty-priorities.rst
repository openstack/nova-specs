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

* A plan for the future of flavors, image properties and host aggregates.

  * Flavor extra specs are leading to a poor API experience. Poor discovery
    of whether a feature is available, and often leaking implementation
    details.
  * Image creators are exposed to many hypervisor specific image properties
    when trying to get the best performance for their image. We need a better
    way to deal with that.
  * Many private cloud users want more flexibility than flavors allow.
    One of the main trade-offs being losing the capacity planning
    simplification strict flavors can bring.
  * Those who like flavors are faced with an explosion of flavors that might
    be better handled as some kind of optional add on. With some features
    users are forced to create images to set some image property to get the
    feature they want activated.
  * This fights against our mission for all deployments to have the same API.

* Tasks for API triggered operations

  * It is often hard for a user to tell if the action triggered by their API
    request has actually completed.
  * While we have instance actions, they do not cover all operations yet
  * We do have request-ids but they are quite hidden in headers, and not well
    documented as a way to track actions
  * The error handling for operations being interrupted when forcibly
    restarting nova-compute is messy and non-standard, need more consistency.
  * Ideally there would be a more async API with web call backs or a more
    event friendly protocol, but that effort is really separate.

* Simplify Quotas

  * The current quota code has proved unreliable
  * A premature optimisation has been identified that causes DB level races,
    we should experiment with removing that optimisation.
  * The quota reservation and commit system is complicated, we should consider
    removing that complexity, if possible.
  * This effort should make it easier to add new features like nested quotas.

* Revisit how we talk to Glance, Neutron and Cinder APIs

  * Cinder has created os-brick, which should make it easier to support
    new volume drivers in Nova, and stop duplicate code.
  * Neutron VIF driver code in Nova has similar issues to the volume drivers.
    As neutron becomes more decentralized, we need to model the same in our
    VIF driver logic in Nova. A new library has been proposed.
  * More generally, we have had lots of issues with races in the create port
    code that lives in the neutron network API. Ideally we can create some new
    Neutron APIs that reduce the impedance miss match, and reduce races.
  * With glance, there is some code duplicated in both Cinder and Nova to
    access data in glance, including support for the v2 API. It would be good
    to have a library to reduce that duplication.

* Feature Test Classification

  * Our users should also be clear about what features are experimental vs
    tested and ready for production vs deprecated and scheduled for removal.
  * We should look again at the hypervisor support matrix, and look at ways
    to dig into our testing gaps and plug them. Be that missing tempest tests,
    or missing test environments/combinations.
  * Ideally this should include plugging any documentation gaps, particularly
    around API documentation.

* Fixing more bugs

  * We need to get all the pending bug fixes reviewed
  * Need to get a better understanding of all the bugs without fixes
  * Look to identify key themes, like the Quota bugs, to identify areas
    that need some attention.

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
