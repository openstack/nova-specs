..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

=============================================
Enable cold migration with target host - Pike
=============================================

https://blueprints.launchpad.net/nova/+spec/cold-migration-with-target-pike

The aim of this feature is to let operators cold migrate instances with
target host manually.

Problem description
===================

A target host can be specified on the live migration operation.
And there is a scheduler rule check and 'force' flag in REST API
when a target host is specified on the live migration operation.

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

This blueprint also provides a way for operators to bypass the scheduler,
we will make the API for cold migration, including a destination host,
by adding an request body argument called 'force'
(accepting True or False, defaulted to False) and
the corresponding CLI methods will expose that force option.
If the microversion asked by the client is older than the version
providing the field, then it won't be passed
(neither True or False, rather the key won't exist)
to the conductor so the conductor won't call the scheduler.

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
            "host": "target-host",
            "force": True
        }
    }

The 'host' parameter to specify a target host is required
(not optional) because of consistency with a live migration API.

If 'force' is True, do not check the destination.
If 'force' is False or null or not provided,
do check the destination.

If 'force' is supplied in the request body and its value is true
but the 'host' parameter is null,
then an HTTP 400 Bad Request will be served to the user.

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
optional. And add the 'force' argument as optional.

nova migrate [--force True] <server> [<host>]

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
* Add API with bumping a new microversion
* Add a target host argument and 'force' argument on novaclient
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

* enable cold migration with target host

  - https://blueprints.launchpad.net/nova/+spec/cold-migration-with-target

History
=======

The blueprint has been approved for Ocata as
'cold-migration-with-target-ocata'.
It is renamed to 'cold-migration-with-target-pike' now.

.. list-table:: Revisions
   :header-rows: 1

   * - Release Name
     - Description
   * - Ocata
     - Approved
   * - Pike
     - Reproposed
