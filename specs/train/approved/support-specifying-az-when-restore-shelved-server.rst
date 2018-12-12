..
   This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

=================================================
Support specifying az when restore shelved server
=================================================

https://blueprints.launchpad.net/nova/+spec/support-specifying-az-when-restore-shelved-server

This blueprint proposes support admin/user to specify ``availability_zone``
to unshelve a shelved server.

Problem description
===================
If the current instance is in the ``SHELVED_OFFLOADED`` status, then its
``availability_zone`` attribute will be set to None in the ``instances``
database table (this change comes from [1]_). But the ``spec`` attribute
records the value of the AZ of the instance before being shelved in the
``request_specs`` database table. When unshelve the server, the value of
AZ will be taken from ``spec`` as 'instance.availability_zone'.

There are two ways an instance can be in an AZ::

  1. The user passes an AZ on server create or
  2. [DEFAULT]/default_schedule_zone is set.

For the above two cases, the RequestSpec.availability_zone will always remain
in the user-specified or [DEFAULT]/default_schedule_zone AZ, even if the AZ is
later renamed and [DEFAULT]/default_schedule_zone is changed, or that server
is on shelve/unshelve, there is a related bug here [2]_.

Once the AZ in ``spec`` is missing, unshelve server will have an error.

Use Cases
---------
As a administrator/user, I want to specify AZ when executing unshelve/restore
a shelved-offloaded server.

Proposed change
===============
Add a new microversion to the unshelve/restore shelved server
(unshelve Action) API to support specifying AZ to restore a shelved server.

If the operator configures cross_az_attach=True [3]_ in nova.conf, in the
[cinder] group, the server create flow will fail if the specified AZ does
not match the volumes being attached to the server. Unshelve should likely
also fail for the same reason, but to figure that out we'd have to iterate
the volumes (via BDMs) attached to the server and determine if their AZ
matches the user-specified AZ and if not, fail the unshelve request, this
needs to be checked as an edge case in the API.

Add ``availability_zone`` attribute to unshelve Action request body.

The availability_zone parameter for unshelve will just be an availability zone,
not the `ZONE:HOST:NODE`_ (admin-only) format available during server create
which, when HOST and/or NODE are specified, will forcefully bypass the
scheduler.

Alternatives
------------
Creating a server from the shelved snapshot image in another AZ (or just avoid
shelve/unshelve altogether and snapshot the server, delete it, and then create
with the new AZ). The downside is you lose the ports/volumes you had connected
to the previous server.

Another alternative is the AZ rename/delete code could be changed to prevent
renaming/deleting an AZ while there are shelved offloaded servers that were
created in that AZ. This, however, would not be scalable because we'd have to
get and deserialize every RequestSpec for every ``SHELVED_OFFLOADED`` server
just to see if it had a matching AZ.
In other words, because the RequestSpec is a serialized json string in the
database, we cannot do a simple DB query to efficiently get this information.

Data model impact
-----------------
None

REST API impact
---------------
* URL:
    * /v2.1/servers/{server_id}/action

* Request method:
    * POST

The availability zone data will be able to add to request payload ::

    {
        "unshelve": {
            "availability_zone": 'beijing'
        }
    }

The ``availability_zone`` field is optional.

If the server status is 'SHELVED' rather than 'SHELVED_OFFLOADED' and an AZ
is specified the API will return a 400 response, otherwise if my server was
created in AZ1, I shelved it (but didn't offload it yet), and then unshelved
and specified AZ2 but the server doesn't end up in AZ2, this request will be
ignored, because of that will be start instance directly. So this change only
supports the case where the server status is 'SHELVED_OFFLOADED'.

Security impact
---------------
None

Notifications impact
--------------------
None

Other end user impact
---------------------
The python-novaclient and python-openstackclient will be updated.

Performance Impact
------------------
None

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
  Brin Zhang

Work Items
----------
* Add a new microversion to the unshelve/restore shelved server
  (unshelve Action) API
* Add related tests

Dependencies
============
None

Testing
=======
* Add related unit tests
* Add related functional tests

Documentation Impact
====================
Add docs that mention unshelve/restore shelved server after the microversion.

References
==========

.. [1] https://review.opendev.org/#/c/599087/
.. [2] https://bugs.launchpad.net/nova/+bug/1723880

.. [3] https://docs.openstack.org/nova/latest/configuration/config.html#cinder.cross_az_attach
.. _ZONE:HOST:NODE: https://docs.openstack.org/nova/latest/admin/availability-zones.html

History
=======
.. list-table:: Revisions
      :header-rows: 1

   * - Release Name
     - Description
   * - Train
     - Introduced
