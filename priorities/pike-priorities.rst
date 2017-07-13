.. _pike-priorities:

=======================
Pike Project Priorities
=======================

List of efforts the Nova development team is prioritizing for reviews in the
Pike release (in no particular order).

+-------------------------------------------+-----------------------+
| Priority                                  | Primary Contacts      |
+===========================================+=======================+
| `Cells V2`_                               | `Dan Smith`_          |
|                                           | `Melanie Witt`_       |
+-------------------------------------------+-----------------------+
| `Placement`_                              | `Jay Pipes`_          |
|                                           | `Sylvain Bauza`_      |
|                                           | `Chris Dent`_         |
|                                           | `Ed Leafe`_           |
|                                           | `Alex Xu`_            |
+-------------------------------------------+-----------------------+
| `Integrate Cinder 3.27`_                  | `John Garbutt`_       |
|                                           | `Matt Riedemann`_     |
+-------------------------------------------+-----------------------+
| `Run API under WSGi (Community Goal)`_    | `Chris Dent`_         |
|                                           | `Sean Dague`_         |
+-------------------------------------------+-----------------------+
| `Support Python 3.5 (Community Goal)`_    | `ChangBo Guo`_        |
+-------------------------------------------+-----------------------+

.. _Dan Smith: https://launchpad.net/~danms
.. _Melanie Witt: https://launchpad.net/~melwitt
.. _Jay Pipes: https://launchpad.net/~jaypipes
.. _Sylvain Bauza: https://launchpad.net/~sylvain-bauza
.. _Chris Dent: https://launchpad.net/~cdent
.. _Ed Leafe: https://launchpad.net/~ed-leafe
.. _Alex Xu: https://launchpad.net/~xuhj
.. _John Garbutt: https://launchpad.net/~johngarbutt
.. _Matt Riedemann: https://launchpad.net/~mriedem
.. _Sean Dague: https://launchpad.net/~sdague
.. _ChangBo Guo: https://launchpad.net/~glongwave

Cells v2
--------

A single-cell cells v2 deployment was made required in the Ocata release.

In Pike, the goal is to support multiple cells v2 cells in a deployment. There
are several priority efforts to get us there.

* `Cells-aware API`_: Many of the nova-api entry points will not know about
  cells properly to pass their operations through to the appropriate
  connection so we need to make them cell-aware.
* `Quotas in the API cell`_: The quotas tables have moved to the API database
  but we want to avoid an 'up-call' from the compute cells to the API when
  handling quota commits and rollbacks. With cells v2 we have an opportunity to
  rethink how Nova supports counting resources and tracking quota, so this
  effort aims to move quota handling to a more simplified solution which is
  more eventually consistent and avoids invalid over-quota failures by design.
* Support a simple python merge operation when sorting and/or filtering a list
  of instances across multiple cells. Long-term this may be handled by
  `Searchlight`_ but for Pike we will have a simple but albeit less performant
  solution.
* Continuous integration testing of multiple cells v2 cells with a multi-node
  job.

.. note:: Move operations across cells, such as live migration, will not be supported in the
  Pike release, but may be a focus for a future release.

.. _Cells-aware API: https://blueprints.launchpad.net/nova/+spec/cells-aware-api
.. _Quotas in the API cell: ../specs/pike/approved/cells-count-resources-to-check-quota-in-api.html
.. _Searchlight: ../specs/pike/approved/list-instances-using-searchlight.html

Placement
---------

The Placement service was made required in the Ocata release.

In Pike, the goals focus on expanding the capabilities of the Placement service
and leverage those to fix some long-standing architectural issues within Nova.

* `Resource provider traits`_: This allows modeling of qualitative information
  about resource providers. For example, in Ocata we know quantitative
  information about a resource provider, such as how much DISK_GB inventory it
  has. Traits allow the system to model the type of disk, e.g. HDD or SDD.
  Traits will also be used to model resource provider aggregate relationships
  for things like shared storage pools.
* `Custom resource classes`_: This is continuing work from Ocata to have the
  Ironic compute driver provide Ironic node resource class information to the
  placement service which will eventually be used for scheduling decisions.
* `Claim resources during scheduling`_: This is a refactor to move resource
  claims out of the compute service ResourceTracker and into the controller
  service(s) during scheduling which should drastically reduce build retries
  due to resource contention in a pack-oriented scheduling configuration. This
  is also needed to avoid 'up-calls' from computes to controller services in
  a multi-cell deployment.
* `Handle aggregate resources`_: This is continuing work from Ocata where we
  need to be able to model resource provider aggregates for things like shared
  storage and IP allocation pools. Then the resource tracker in the compute
  nodes can pull this information from the placement service when a request is
  made for shared storage in a compute node within a particular aggregate. The
  allocation claim is then made on the resource provider rather than the
  compute node.

.. _Resource provider traits: ../specs/pike/approved/resource-provider-traits.html
.. _Custom resource classes: ../specs/ocata/implemented/custom-resource-classes.html
.. _Claim resources during scheduling: ../specs/pike/approved/placement-claims.html
.. _Handle aggregate resources: ../specs/newton/implemented/generic-resource-pools.html

Integrate Cinder 3.27
---------------------

In Ocata, Cinder provided the `3.27 microversion`_. In Pike, Nova will use the
3.27 API to `attach and detach volumes`_. This is an effort to reduce technical
debt and state management between both the Nova and Cinder projects by
abstracting volume attachment state information in Cinder where it belongs.
This is also a pre-requisite to support attaching multiple instances to the
same volume, which will likely be a priority in a future release.

.. _3.27 microversion: https://specs.openstack.org/openstack/cinder-specs/specs/ocata/add-new-attach-apis.html
.. _attach and detach volumes: ../specs/pike/approved/cinder-new-attach-apis.html

Run API under WSGi (Community Goal)
-----------------------------------

This is a community-wide release goal for Pike. The goal for Nova is to
support, and test, running `nova-api under WSGI`_.

.. _nova-api under WSGI: https://governance.openstack.org/tc/goals/pike/deploy-api-in-wsgi.html

Support Python 3.5 (Community Goal)
-----------------------------------

This is a community-wide release goal for Pike. The goal for Nova is to
support, and test, running with `python 3.5`_.

.. _python 3.5: https://governance.openstack.org/tc/goals/pike/python35.html
