..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

==================================================
show which server group a server is in "nova show"
==================================================

bp link:

https://blueprints.launchpad.net/nova/+spec/show-server-group

Problem description
===================

Currently you had to loop over all groups to find the group the server
belongs to. This spec tries to address this by proposing showing the server
group information in API ``GET /servers/{server_id}``.

Use Cases
---------

* Admin/End user want to know the server group that the server belongs to
  in a direct way.


Proposed change
===============

Proposes to add the server-group UUID to ``GET /servers/{id}``,
``PUT /servers/{server_id}`` and REBUILD API
``POST /servers/{server_id}/action``.

The server-group information will not be included in
``GET /servers/detail`` API, because the server-group information
needs another DB query.


Alternatives
------------

* One alternative is support the server groups filter by server UUID. Like
  ``GET /os-server-groups?server=<UUID>``.

* Another alternative to support the server group query is following API:
  ``GET /servers/{server_id}/server_groups``.

Data model impact
-----------------

NO


REST API impact
---------------


Allows the ``GET /servers/{server_id}`` API to show server group's UUID.
``PUT /servers/{server_id}`` and REBUILD API
``POST /servers/{server_id}/action`` also response same information.

The returned information for server group::

    {
        "server": {
            "server_groups": [ # not cached
                   "0b5d2c72-12cc-4ba6-a8d7-3ff5cc1d8cb8"
            ]
        }
    }



Security impact
---------------

N/A

Notifications impact
--------------------

N/A

Other end user impact
---------------------

* python novaclient would contain the server_group information.

Performance Impact
------------------

* Need another DB query retrieve the server group UUID. To reduce the
  perfermance impact for batch API call, ``GET /servers/detail`` won't
  return server group information.

Other deployer impact
---------------------

N/A

Developer impact
----------------

N/A

Upgrade impact
--------------

N/A

Implementation
==============

Assignee(s)
-----------

Primary assignee:
  Yongli He


Work Items
----------

* Add new microversion for this change.


Dependencies
============

N/A

Testing
=======

* Add functional api_sample tests.
* Add microversion releated test to tempest.

Documentation Impact
====================

* The API document should be changed to introduce this new feature.

References
==========

* Stein PTG discussion: https://etherpad.openstack.org/p/nova-ptg-stein


History
=======

.. list-table:: Revisions
   :header-rows: 1

   * - Release Name
     - Version
   * - Stein
     - First Version

