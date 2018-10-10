..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

================================================
Remove force flag from live-migrate and evacuate
================================================

https://blueprints.launchpad.net/nova/+spec/remove-force-flag-from-live-migrate-and-evacuate

Force live-migrate and evacuate operations cannot be meaningfully supported for
servers having complex resource allocations. So this spec proposes to remove
the ``force`` flag from these operations in a new REST API microversion.

Problem description
===================

Today when ``force: True`` is specified nova tries to blindly copy the resource
allocation from the source host to the target host. This only works if the
the server's allocation is satisfied by the single root resource provider both
on the source host and on the destination host. As soon as the allocation
become more complex (e.g. it allocates from more than one provider
(including sharing providers) or allocates only from a nested provider) the
blind copy will fail.

Use Cases
---------

This change removes the following use case from the system:

* The admin cannot force a live-migration to a specified destination host
  against the Nova scheduler and Placement agreement.
* The admin cannot force a evacuate to a specified destination host against
  the Nova scheduler and Placement agreement.

This does not effect the use cases when the operator specifies the destination
host and let Nova and Placement verify that host before the move.

Please note that this removes the possibility to force live-migrate servers to
hosts where the nova-compute is disabled as the ComputeFilter in the filter
scheduler will reject such hosts.

Proposed change
===============

Forcing the destination host in a complex allocation case cannot supported
without calling Placement to get allocation candidates on the destination host
as Nova does not know how to copy the complex allocation. The documentation
of the force flag states that Nova will not call the scheduler to verify the
destination host. This rule has already been broken since Pike by two
`bugfixes`_.  Also supporting complex allocations requires to get allocation
candidates from Placement. So the spec proposes to remove the ``force`` flag as
it cannot be supported any more.

Note that fixing old microversions to fail cleanly without leaking resources
in complex allocation scenarios is not part of this spec but handled as part of
`use-nested-allocation-candidates`_ That change will make sure that the forced
move operation on a server that either has complex allocation on the source
host or would require complex allocation on the destination host will be
rejected with a NoValidHost exception by the Nova conductor.

Alternatives
------------

* Try to guess when the server needs a complex allocation on the destination
  host and only ignore the force flag in these cases.
* Do not manage resource allocations for forced move operations.

See more details in the `ML thread`_

Data model impact
-----------------

None

REST API impact
---------------

In a new microversion remove the ``force`` flag from both APIs:

* POST /servers/{server_id}/action (os-migrateLive Action)
* POST /servers/{server_id}/action (evacuate Action)


Security impact
---------------

None

Notifications impact
--------------------

None

Other end user impact
---------------------

Update python-novaclient and python-openstackclient to support the new
microversion.

As the admin cannot skip the scheduler any more when moving servers, such move
can fail with scheduler and Placement related reasons.

Performance Impact
------------------

As the admin cannot skip the scheduler when moving a server, such move will
take a bit more time as Nova will call the scheduler and Placement.

Other deployer impact
---------------------

Please note that this spec removes the possibility to force live-migrate
servers to hosts where the nova-compute is disabled as the ComputeFilter in
the filter scheduler will reject such hosts.

Developer impact
----------------

Supporting the force flag has been a detriment to maintaining nova since it's
an edge case and requires workarounds like the ones made in Pike to support it.
Dropping support over time will be a benefit to maintaining the project and
improve consistency/reliability/usability of the API.

Upgrade impact
--------------

None

Implementation
==============

Assignee(s)
-----------


Primary assignee:
  balazs-gibizer


Work Items
----------

* Add a new microversion to the API that removes the ``force`` flag from the
  payload. If the new microversion is used in the request then default
  ``force`` to False when calling Nova internals.
* Document the new microversion
* Add support for the new microversion in the python-novaclient and in the
  python-openstackclient


Dependencies
============

* Some part of `use-nested-allocation-candidates`_ is a dependecy of this work.

Testing
=======

* Functional and unit test will be provided

Documentation Impact
====================

* API reference document needs to be updated

References
==========

.. _`use-nested-allocation-candidates`: https://blueprints.launchpad.net/nova/+spec/use-nested-allocation-candidates
.. _`ML thread`: http://lists.openstack.org/pipermail/openstack-dev/2018-October/135551.html
.. _`bugfixes`: https://review.openstack.org/#/q/I6590f0eda4ec4996543ad40d8c2640b83fc3dd9d+OR+I40b5af5e85b1266402a7e4bdeb3705e1b0bd6f3b

History
=======

.. list-table:: Revisions
   :header-rows: 1

   * - Release Name
     - Description
   * - Stein
     - Introduced
