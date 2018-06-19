..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

================================
Handling Reshaped Provider Trees
================================

https://blueprints.launchpad.net/nova/+spec/reshape-provider-tree

Virt drivers need to be able to change the structure of the provider trees they
expose. When moving existing resources, existing allocations need to be moved
along with the inventories. And this must be done in such a way as to avoid
races where a second entity can create or remove allocations against the moving
inventories.

Problem description
===================

Use Cases
---------
* The libvirt driver currently inventories VGPU resources on the compute node
  provider. In order to exploit provider trees, libvirt needs to create one
  child provider per physical GPU and move the VGPU inventory from the compute
  node provider to these GPU child providers. In a live deployment where VGPU
  resources are already allocated to instances, the allocations need to be
  moved along with the inventories.
* Drivers wishing to model NUMA must similarly create child providers and move
  inventory and allocations of several classes (processor, memory, VFs on
  NUMA-affined NICs, etc.) to those providers.
* A driver is using a custom resource class. That resource class is added to
  the standard set (under a new, non-``CUSTOM_`` name). In order to use the
  standard name, the driver must move inventory and allocations from the old
  name to the new.

These are just example cases that may exist now or in the future.  We're
describing a generic pivot system here.

Proposed change
===============
The overall flow is as follows. The parts in red only happen when a reshape is
needed. This represents the happy path on compute startup only.

.. seqdiag::

    seqdiag {
        edge_length = 200;
        span_height = 15;
        activation = none;
        default_note_color = white;
        'Resource Tracker'; 'Report Client'; Placement; 'Virt Driver';
        'Resource Tracker' -> 'Virt Driver' [label = "update_provider_tree(provider_tree, nodename, allocations=None)"];
        'Resource Tracker' <- 'Virt Driver' [label = "raise ReshapeNeeded", color = red];
        'Resource Tracker' -> 'Report Client' [label = "get_allocations_for_provider_tree()", color = red];
        'Report Client' -> Placement [label = "GET /resource_providers/{uuid}/allocations", color = red];
        'Report Client' <-- Placement [label = "HTTP 200", color = red];
        'Report Client' -> 'Report Client' [label = "get_allocations_for_consumer(context, consumer)", color = red];
        'Report Client' -> Placement [label = "GET /allocations/{consumer_uuid}", color = red];
        'Report Client' <-- Placement [label = "HTTP 200", color = red];
        'Resource Tracker' <-- 'Report Client' [label = "{allocations by consumer}", color = red];
        'Resource Tracker' -> 'Virt Driver' [label = "update_provider_tree(provider_tree, nodename, allocations=allocations)", color = red];
        'Resource Tracker' <-- 'Virt Driver';
        'Resource Tracker' -> 'Report Client' [label = "update_from_provider_tree(
                                                        context, new_tree,
                                                        allocations)"];
        'Report Client' ->  Placement [label = "POST /resource_providers
                                                (create new providers)"];
        'Report Client' <-- Placement [label = "HTTP 200"];
        'Report Client' ->  Placement [label = "POST /resource_providers/{uuid}/aggregates|traits
                                                (fix up aggregates, traits, etc.)"];
        'Report Client' <-- Placement [label = "HTTP 200"];
        'Report Client' ->  Placement [label = "POST /reshaper {transformation payload}"];
        Placement --> Placement [label = "create/modify/
                                          delete
                                          inventories"];
        Placement --> Placement [label = "create/modify/
                                          delete
                                          allocations", color = red];
        'Report Client' <-- Placement [label = "HTTP 204"];
        'Resource Tracker' <-- 'Report Client'
    }

Note that, for Fast-Forward Upgrades, the ``Resource Tracker`` lane is actually
the `Offline Upgrade Script`_.

.. _`get_allocations_for_provider_tree()`:

SchedulerReportClient.get_allocations_for_provider_tree()
---------------------------------------------------------
A new SchedulerReportClient method shall be implemented::

  def get_allocations_for_provider_tree(self):
      """Retrieve allocation records associated with all providers in the
      provider tree.

      :returns: A dict, keyed by consumer UUID, of allocation records.
      """

A consumer isn't always an instance (it may be a "migration" - or other things
not created by Nova, in the future), so we can't just use the instance list as
the consumer list.

We can't get *all* allocations for associated sharing providers because some of
those will belong to consumers on other hosts.

So we have to discover all the consumers associated with the providers in the
local tree::

  for each "local" provider:
      GET /resource_providers/{provider.uuid}/allocations

We can't use *just* those allocations because we would miss allocations for
sharing providers. So we have to get all the allocations for just the consumers
discovered above::

  for each consumer in ^:
      GET /allocations/{consumer.uuid}

.. note:: We will still miss data if **all** of a consumer's allocations live
          on sharing providers. I don't have a good way to close that hole.
          But that scenario won't happen in the near future, so it'll be noted
          as a limitation via a code comment.

Return a dict, keyed by the ``{consumer.uuid}``, of the resulting allocation
records. This is the form of the new `Allocations Parameter`_ expected by
`update_provider_tree()`_ and `update_from_provider_tree()`_), and return it.

ReshapeNeeded exception
-----------------------
A new exception, ``ReshapeNeeded``, will be introduced. It is used as a signal
from `update_provider_tree()`_ to indicate that a reshape must be performed.
This is for performance reasons so that we don't
`get_allocations_for_provider_tree()`_ unless it's necessary.

.. _`update_provider_tree()`:

Changes to update_provider_tree()
---------------------------------

Allocations Parameter
~~~~~~~~~~~~~~~~~~~~~
A new ``allocations`` keyword argument will be added to
``update_provider_tree()``::

  def update_provider_tree(self, provider_tree, nodename, allocations=None):

If ``None``, the ``upgrade_provider_tree()`` method must not perform a reshape.
If it decides a reshape is necessary, it must raise the new ``ReshapeNeeded``
exception.

When not ``None``, the ``allocations`` argument is a dict, keyed by consumer
UUID, of allocation records of the form::

  { $CONSUMER_UUID: {
        # NOTE: The shape of each "allocations" dict below is identical to the
        # return from GET /allocations/{consumer_uuid}...
        "allocations": {
            $RP_UUID: {
                "generation": $RP_GEN,
                "resources": {
                    $RESOURCE_CLASS: $AMOUNT,
                    ...
                },
            },
            ...
        },
        "project_id": $PROJ_ID,
        "user_id": $USER_ID,
        # ...except for this, which is coming in bp/add-consumer-generation
        "consumer_generation": $CONSUMER_GEN,
    },
    ...
  }

If ``update_provider_tree()`` is moving allocations, it must edit the
``allocations`` dict in place.

.. note:: I don't love the idea of the method editing the dict in place rather
          than returning a copy, but it's consistent with how we're handling
          the ``provider_tree`` arg.

Virt Drivers
~~~~~~~~~~~~
Virt drivers currently overriding ``update_provider_tree()`` will need to
change the signature to accomodate the new parameter. That work will be done
within the scope of this blueprint.

As virt drivers begin to model resources in nested providers, their
implementations will need to:

* determine whether a reshape is necessary and raise ``ReshapeNeeded`` as
  appropriate;
* perform the reshape by processing provider inventories and the specified
  allocations.

That work is outside the scope of this blueprint.

.. _`update_from_provider_tree()`:

Changes to update_from_provider_tree()
--------------------------------------
The ``SchedulerReportClient.update_from_provider_tree()`` method is changed to
accept a new parameter ``allocations``::

  def update_from_provider_tree(self, context, new_tree, allocations):
      """Flush changes from a specified ProviderTree back to placement.

      ...

      ...
      :param allocations: A dict, keyed by consumer UUID, of allocation records
              of the form returned by GET /allocations/{consumer_uuid}. The
              dict must represent the comprehensive final picture of the
              allocations for each consumer therein. A value of None indicates
              that no reshape is being performed.
      ...
      """

When ``allocations`` is ``None``, the behavior of
``update_from_provider_tree()`` is as it was previously (in Queens).

.. _`Resource Tracker _update()`:

Changes to Resource Tracker _update()
-------------------------------------
The ``_update()`` method will get a new parameter, ``startup``, which is
percolated down from ``update_available_resource()``.

Where `update_provider_tree()`_ and `update_from_provider_tree()`_ are
currently invoked, the code flow will be changed to approximately::

  try:
      self.driver.update_provider_tree(prov_tree, nodename)
  except exception.ReshapeNeeded:
      if not startup:
          # Treat this like a regular exception during periodic
          raise
      LOG.info("Performing resource provider inventory and "
               "allocation data migration during compute service "
               "startup or FFU.")
      allocs = reportclient.get_allocations_for_provider_tree()
      self.driver.update_provider_tree(prov_tree, nodename,
                                       allocations=allocs)
  ...
  reportclient.update_from_provider_tree(context, prov_tree, allocs)

Changes to _update_available_resource_for_node()
------------------------------------------------
This is currently where all exceptions for the `Resource Tracker _update()`_
periodic task are caught, logged, and otherwise ignored.

We will add a new parameter, ``startup``, percolated down from
``update_available_resource()``, and a new ``except`` clause of the form::

  except exception.ResourceProviderUpdateFailed:
      if startup:
          # Kill the compute service.
          raise
      # Else log a useful exception reporting what happened and maybe even how
      # to fix it; and then carry on.

The purpose of this is to make exceptions in `update_from_provider_tree()`_
fatal on startup only.

Placement POST /reshaper
------------------------
In a new placement microversion, a new ``POST /reshaper`` operation will be
introduced. The payload is of the form::

  {
    "inventories": [
      $RP_UUID: {
        # This is the exact payload format for
        # PUT /resource_provider/$RP_UUID/inventories.
        # It should represent the final state of the entire set of resources
        # for this provider. In particular, omitting a $RC dict will cause the
        # inventory for that resource class to be deleted if previously present.
        "inventories": { $RC: { <total, reserved, etc.> } }
        "resource_provider_generation": <gen of this RP>,
      },
      $RP_UUID: { ... },
    ],
    "allocations": [
      # This is the exact payload format for POST /allocations
      $CONSUMER_UUID: {
        "project_id": $PROJ_ID,
        "user_id": $USER_ID,
        # This field is part of the consumer generation series under review,
        # not yet in the published POST /allocations payload.
        "consumer_generation": $CONSUMER_GEN,
        "allocations": {
          $RP_UUID: {
            "resources": { $RC: $AMOUNT, ... }
          },
          $RP_UUID: { ... }
        }
      },
      $CONSUMER_UUID: { ... }
    ]
  }

In a single atomic transaction, placement replaces the inventories for each
``$RP_UUID`` in the ``inventories`` dict; and replaces the allocations for each
``$CONSUMER_UUID`` in the ``allocations`` dict.

Return values:

* ``204 No Content`` on success.
* ``409 Conflict`` on any provider or consumer generation conflict; or if a
  concurrent transaction is detected. Appropriate error codes should be used
  for at least the former so the caller can tell whether a fresh ``GET`` is
  necessary before recalculating the necessary reshapes and retrying the
  operation.
* ``400 Bad Request`` on any other failure.

Direct Interface to Placement
-----------------------------
To make the `Offline Upgrade Script`_ possible, we need to make placement
accessible by importing Python code rather than as a standalone service. The
quickest path forward is to use `wsgi-intercept`_ to allow HTTP interactions,
using the `requests`_ library, to work with only database traffic going over
the network. This allows client code to make changes to the placement data
store using the same API, but without running a placement service.

An implementation of this, as a context manager called `PlacementDirect`_, is
merged. The context manager accepts an `oslo config`_, populated by the
caller. This allows the calling code to control how it wishes to discover
configuration settings, most importantly the database being used by placement.

This implementation provides a quick solution to the immediate needs of offline
use of `Placement POST /reshaper`_ while allowing options for prettier
solutions in the future.

Offline Upgrade Script
----------------------
To facilitate Fast Forward Upgrades, we will provide a script that can perform
this reshaping while all services (except databases) are offline. It will look
like::

  nova-manage placement migrate_compute_inventory

...and operate as follows, for each nodename (one, except for ironic) on the
host:

* Spin up a SchedulerReportClient with a `Direct Interface to Placement`_.
* Retrieve a ProviderTree via
  ``SchedulerReportClient.get_provider_tree_and_ensure_root()``.
* Instantiate the appropriate virt driver.
* Perform the algorithm noted in `Resource Tracker _update()`_, as if
  ``startup`` is ``True``.

We may refer to https://review.openstack.org/#/c/501025/ for an example of an
upgrade script that requires a virt driver.

Alternatives
------------

Reshaper API
~~~~~~~~~~~~
Alternatives to `Placement POST /reshaper`_ were discussed in the `mailing list
thread`_, the `etherpad`_, IRC, hangout, etc. They included:

* Don't have an atomic placement operation - do the necessary operations one at
  a time from the resource tracker. Rejected due to race conditions: the
  scheduler can schedule against the moving inventories, based on incorrect
  capacity information due to the moving allocations.
* "Lock" the moving inventories - either by providing a locking API or by
  setting ``reserved = total`` - while the resource tracker does the
  reshape. Rejected because it's a hack; and because recovery from partial
  failures would be difficult.
* "Merge" forms of the new placement operation:

  * ``PATCH`` (or ``POST``) with `RFC 6902`_-style ``"operation", "path"[,
    "from", "value"]`` instructions.
  * ``PATCH`` (or ``POST``) with `RFC 7396`_ semantics. The JSON payload would
    look like a sparse version of that described in `Placement POST
    /reshaper`_, but with only changes included.

* Other payload formats for the placement operation (see the `etherpad`_). We
  chose the one we did because it reuses existing payload syntax (and may
  therefore be able to reuse code) and it provides a full specification of the
  expected end state, which is RESTy.

Direct Placement
~~~~~~~~~~~~~~~~
Alternatives to the ``wsgi-intercept`` model for the `Direct Interface to
Placement`_:

* Directly access the object methods (with some refactoring/cleanup). Rejected
  because we lose things like schema validation and microversion logic.
* Create cleaner, pythonic wrappers around those object methods. Rejected (in
  the short term) for the sake of expediency. We might take this approach
  longer-term as/when the demand for direct placement expands beyond FFU
  scripting.
* Use ``wsgi-intercept`` but create the pythonic wrappers outside of the REST
  layer. This is also a long-term option.

Reshaping Via update_provider_tree()
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

* We considered passing allocations to `update_provider_tree()`_ every time,
  but gathering the allocations will be expensive, so we needed a way to do it
  only when necessary. Enter `ReshapeNeeded exception`_.
* We considered running the check-and-reshape-if-needed algorithm on every
  periodic interval, but decided we should never need to do a reshape except on
  startup.

Data model impact
-----------------
None.

REST API impact
---------------
See `Placement POST /reshaper`_.

Security impact
---------------
None.

Notifications impact
--------------------
None.

Other end user impact
---------------------
See `Upgrade Impact`_.

Performance Impact
------------------
The new `Placement POST /reshaper`_ operation has the potential to be slow, and
to lock several tables. Its use should be restricted to reshaping provider
trees. Initially we may use the reshaper from `update_from_provider_tree()`_
even if no reshape is being performed; but if this is found to be problematic
for performance, we can restrict it to only reshape scenarios, which will be
very rare.

Gathering allocations, particularly in large deployments, has the potential to
be heavy and slow, so we only do this at compute startup, and then only if
`update_provider_tree()`_ indicates that a reshape is necessary.

Other deployer impact
---------------------
See `Upgrade Impact`_.

Developer impact
----------------
See `Virt Drivers`_.

Upgrade impact
--------------
Live upgrades are covered. The `Resource Tracker _update()`_ flow will run on
compute start and perform the reshape as necessary. Since we do not support
skipping releases on live upgrades, any virt driver-specific changes can be
removed from one release to the next.

The `Offline Upgrade Script`_ is provided for Fast-Forward Upgrade. Since code
is run with each release's codebase for each step in the FFU, any virt
driver-specific changes can be removed from one release to the next. Note,
however, that the script must **always be run** since only the virt driver,
running on a specific compute, can determine whether a reshape is required for
that compute. (If no reshape is necessary, the script is a no-op.)

Implementation
==============

Assignee(s)
-----------

* `Placement POST /reshaper`_: jaypipes (SQL-fu), cdent (API plumbing)
* `Direct Interface to Placement`_: cdent
* Report client, resource tracker, virt driver parity: efried
* `Offline Upgrade Script`_: dansmith
* Reviews and general heckling: mriedem, bauzas, gibi, edleafe, alex_xu

Work Items
----------
See `Proposed change`_.

Dependencies
============
* `Consumer Generations`_
* `Nested Resource Providers - Allocation Candidates`_

Testing
=======
Functional test enhancements for everyone, including gabbi tests for `Placement
POST /reshaper`_.

Live testing in Xen (naichuans) and libvirt (bauzas) via their VGPU work.

Documentation Impact
====================
* `Placement POST /reshaper`_ (placement API reference)
* `Offline Upgrade Script`_ (`nova-manage db`_)

References
==========

* `Consumer Generations`_ spec
* `Nested Resource Providers - Allocation Candidates`_
* Placement reshaper API discussion `etherpad`_
* Upgrade concerns... `mailing list thread`_
* `RFC 6902`_ (``PATCH`` with ``json-patch+json``)
* `RFC 7396`_ (``PATCH`` with ``merge-patch+json``)
* `nova-manage db`_ migration helper docs
* `wsgi-intercept`_
* Python `requests`_
* `PlacementDirect`_ implementation
* `oslo config`_ library

.. _`Consumer Generations`: http://specs.openstack.org/openstack/nova-specs/specs/rocky/approved/add-consumer-generation.html
.. _`Nested Resource Providers - Allocation Candidates`: http://specs.openstack.org/openstack/nova-specs/specs/rocky/approved/nested-resource-providers-allocation-candidates.html
.. _`etherpad`: https://etherpad.openstack.org/p/placement-migrate-operations
.. _`mailing list thread`: http://lists.openstack.org/pipermail/openstack-dev/2018-May/130783.html
.. _`RFC 6902`: https://tools.ietf.org/html/rfc6902
.. _`RFC 7396`: https://tools.ietf.org/html/rfc7396
.. _`nova-manage db`: https://docs.openstack.org/nova/latest/cli/nova-manage.html#nova-database
.. _wsgi-intercept: https://pypi.org/project/wsgi_intercept/
.. _requests: http://docs.python-requests.org/
.. _PlacementDirect: https://review.openstack.org/#/c/572576/
.. _oslo config: https://docs.openstack.org/oslo.config/latest/

History
=======

.. list-table:: Revisions
   :header-rows: 1

   * - Release Name
     - Description
   * - Rocky
     - Introduced
