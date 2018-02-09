..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

===============================================
Enable cold migration with target host - Queens
===============================================

https://blueprints.launchpad.net/nova/+spec/cold-migration-with-target-queens

The aim of this feature is to let operators cold migrate instances with
target host manually.

Problem description
===================

A target host can be specified on the live migration operation.
But a target host cannot be specified on the cold migration operation.
It is inconsistent with the live migration operation,
and both of these operations have similar circumstances
when the host needs to be specified.

Use Cases
---------

It is same as the live migration use case.
Sometimes an operator or a script decides which host is the best
suited to accept a cold migration and then wants to perform it.
Consistency with a live migration case should be ensured.

Proposed change
===============

Modify the API and the current resize_instance flow to be able to
specify the target host for cold migration.

Add the function to check whether a destination host is
in accordance with scheduler rules or not in cold migration
as a default behaviour.
Specifically to say, add setting 'requested_destination' of the RequestSpec
object in nova/compute/api.py. The field has already been supported
in the scheduler, so it just needs to be filled in.

Alternatives
------------

None

Data model impact
-----------------

None

REST API impact
---------------

* URL: POST /v2.1/servers/{server_id}/action

  JSON request body::

    {
        "migrate": {
            "host": "target-host"
        }
    }

The 'host' parameter to specify a target host is optional.
Microversion is bumped up.

Security impact
---------------

None

Notifications impact
--------------------

None

Other end user impact
---------------------

python-novaclient will be modified to have a target host argument as
optional.

nova migrate <server> [<host>]

Performance Impact
------------------

None

Other deployer impact
---------------------

None

Developer impact
----------------

None


Implementation
==============

Assignee(s)
-----------

Primary assignee:
  natsume-takashi

Work Items
----------

* Add logic to specify target host for cold migration
* Add processing checking destination host in the cold migration
* Disable retries of the scheduling when the target host is specified
* Add API with bumping a new microversion
* Add nova functional tests
* Add tempest tests

Dependencies
============

None

Testing
=======

Add the following tests.

* Unit tests
* Functional tests
* Tempest tests


Documentation Impact
====================

* API Reference
* CLI Reference
* Admin User Guide on cold migration topic.

References
==========

Mailing list discussion about why ``force`` flag is not added as part of this
proposal: http://lists.openstack.org/pipermail/openstack-dev/2017-August/121654.html

History
=======

The blueprint has been approved for Ocata as
'cold-migration-with-target-ocata' and for Pike as
'cold-migration-with-target-pike'.
It is renamed to 'cold-migration-with-target-queens' now.
But the 'force' parameter to bypass the scheduler check is removed in the spec.

.. list-table:: Revisions
   :header-rows: 1

   * - Release Name
     - Description
   * - Ocata
     - Approved
   * - Pike
     - Reapproved
   * - Queens
     - Reproposed
