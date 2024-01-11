..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

==========================================
List requested Availability Zones
==========================================

Currently server show and server list --long output, displays the
current AZ of the instance. That is, the AZ to which the host of
the instance belongs. There is no way to tell from this information
that whether the instance create request included an AZ or not.

This implementation enables users to validate that their request for
Availability Zone was correctly processed and satisfied, by returning
back information, not only about current placement of the instance,
but also original request.

Problem description
===================
As of today, the server show and server list --long output, displays
the current AZ of the instance. That is, the AZ to which the host
of the instance belongs. There is no way to tell from this information
that whether the instance created request included an AZ or not.

Also when cross_az_attach option is False and booting an instance
from volume, the instance can be pinned to AZ and in that case,
instance will be scheduled on host belonging to pinned AZ.

Also when default_schedule_zone config option set to specific
AZ, in that case, instance would be pinned to that specific
AZ, and instance will be scheduled on host belonging to pinned AZ.


Use Cases
---------
- As an operator, I want to know if the instance create request
  asked for an AZ expliclity or not. And whether the requested AZ and
  current AZ are both same or different.

Proposed change
===============

The instances table from nova cell database does not have requested
availability zone information. The same can be get from request_specs
table in nova_api database.

For server show output, use the existing get_by_instance_uuid method from
RequestSpec object and display it in the output.

For server list --long output, implement a method get_by_instance_uuids for
RequestSpec object, which takes list of instance uuids of instances which
will be shown in the listed output and return a list of RequestSpec objects
of those instances.

Alternatives
------------
As an alternative, we could add the requested availability zone information in
instances table and when doing server list --long or server show use the data
from instances table only and display to users, but it would duplicate the
data in request_specs table as well as in instances table.

Data model impact
-----------------

For implementation, we need to add a method get_by_instance_uuids to
the RequestSpec object, which takes list of instance uuids as input and
returns list of RequestSpec objects of those instances.

REST API impact
---------------

This change will be done with a new microversion bump.

Below are the two APIs that will be changed.

``GET /servers/{server_id}``

- server show api response will include availability zone requested
  during server creation.

  .. code-block::

     {
       "server":
           {
               ...
               "pinned_availability_zone": None
               ...
           }
     }

``GET /servers/detail``

- server list --long api response will include availability zone
  requested during server creation.

  .. code-block::

     {
       "servers": [
           {
               ...
               "pinned_availability_zone": None
               ...
           }
           {
               ...
               "pinned_availability_zone": None
               ...
           }
       ]
     }



Security impact
---------------

None

Notifications impact
--------------------

None

Other end user impact
---------------------


Performance Impact
------------------

There will be minor performance impact when user calls server list --long
because we will be adding another database call to get list of request_specs
of instances.

Other deployer impact
---------------------

None

Developer impact
----------------

None

Upgrade impact
--------------

None

Implementation
==============

Assignee(s)
-----------

Primary assignee:
  ratailor

Feature Liaison
---------------

Feature liaison:
  ratailor


Work Items
----------

- Implement API changes
- Add tests

Dependencies
============

- openstackclient and openstacksdk needs to be updated to implement
  this change.

Testing
=======

- Add unit tests
- Add functional tests (API samples)

Documentation Impact
====================

The api-ref will be updated to reflect the changes.

References
==========

None

History
=======


.. list-table:: Revisions
   :header-rows: 1

   * - Release Name
     - Description
   * - 2024.1 Caracal
     - Introduced
