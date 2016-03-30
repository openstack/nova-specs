..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

=======================================================================
Show the 'project_id' and 'user_id' information in os-server-groups API
=======================================================================

https://blueprints.launchpad.net/nova/+spec/add-project-id-and-user-id

Show the 'project_id' and 'user_id' information of the server
groups in os-server-groups API. This fix will allow admin user
to identify server group easier.


Problem description
===================

The os-server-groups API currently allows admin user to list server
groups for all projects and the response body doesn't contain project
id information of each server group, it will be hard to identify which
server group belong to which project in multi-tenant env.


Use Cases
---------

As a cloud administrator, I want to easily identify which server group
belongs to which project when sending GET request.


Proposed change
===============

Add a new API microversion to the os-server-groups API extension such that if:
 * The version on the API 'list' request satisfies the minimum version include
   the 'project_id' and 'user_id' information of server groups in the
   response data.
 * The version on the API 'show' request satisfies the minimum version include
   the 'project_id' and 'user_id' information of server groups in the response
   data.
 * The version on the API 'create' request satisfies the minimum version
   include the 'project_id' and 'user_id' information of server groups in
   the response data.

Alternatives
------------

None

Data model impact
-----------------

None

REST API impact
---------------

The proposed change updates the GET response data in the os-server-groups
API extension to include the 'project_id' and 'user_id' field if the request
has a minimum supported version.

The proposed change also updates the POST response data in the
os-server-groups API extension to include the 'project_id' and 'user_id'
field if the request has a minimum supported version.

* Modifications for the method

  * Add project id information to the current response data.
  * Add user id information to the current response data.
  * GET requests response data will be affected.
  * POST requests response data will be affected.

* Example use case:

Request:

GET --header "X-OpenStack-Nova-API-Version: 2.12" \
http://127.0.0.1:8774/v2.1/e0c1f4c0b9444fa086fa13881798144f/os-server-groups

Response:

::

   {
    "server_groups": [
    {
      "user_id": "ed64bccd0227444fa02dbd7695769a7d",
      "policies": [
        "affinity"
      ],
      "name": "test1",
      "members": [],
      "project_id": "b8112a8d8227490eba99419b8a8c2555",
      "id": "e64b6ae1-4d05-4faa-9f53-72c71f8e6f1a",
      "metadata": {}
    },
    {
      "user_id": "9128b975e91846f882eb63dc35c2ffd8",
      "policies": [
        "anti-affinity"
      ],
      "name": "test2",
      "members": [],
      "project_id": "b8112a8d8227490eba99419b8a8c2555",
      "id": "b1af831c-69b5-4d42-be44-d710f2b8954c",
      "metadata": {}
    }
    ]
    }

Request:

GET --header "X-OpenStack-Nova-API-Version: 2.12" \
http://127.0.0.1:8774/v2.1/e0c1f4c0b9444fa086fa13881798144f/os-server-groups/
e64b6ae1-4d05-4faa-9f53-72c71f8e6f1a

Response:

::

   {
      "user_id": "ed64bccd0227444fa02dbd7695769a7d",
      "policies": [
        "affinity"
      ],
      "name": "test1",
      "members": [],
      "project_id": "b8112a8d8227490eba99419b8a8c2555",
      "id": "e64b6ae1-4d05-4faa-9f53-72c71f8e6f1a",
      "metadata": {}
    }

Request:

POST --header "X-OpenStack-Nova-API-Version: 2.12" \
http://127.0.0.1:8774/v2.1/e0c1f4c0b9444fa086fa13881798144f/os-server-groups \
-d {"server_group": { "name": "test", "policies": [ "affinity" ] }}

Response:

::

    {
      "user_id": "ed64bccd0227444fa02dbd7695769a7d",
      "policies": [
        "affinity"
      ],
      "name": "test",
      "members": [],
      "project_id": "b8112a8d8227490eba99419b8a8c2555",
      "id": "e64b6ae1-4d05-4faa-9f53-72c71f8e6f1a",
      "metadata": {}
    }

* There should not be any impacts to policy.json files for this change.

Security impact
---------------

None

Notifications impact
--------------------

None

Other end user impact
---------------------

* The python-novaclient server-group-list, server-group-show
  server-group-create command will be updated to handle microversions
  to show the 'project_id' and 'user_id' information in it's output
  if the requested microversion provides that infomation.

Performance Impact
------------------

None

Other deployer impact
---------------------

None; if a deployer is using the required minimum version of the API to get
the 'project_id' and 'user_id' data they can begin using it, otherwise they
won't see a change.

Developer impact
----------------

None


Implementation
==============

Assignee(s)
-----------

Primary assignee:
  Zhenyu Zheng <zhengzhenyu@huawei.com>

Work Items
----------

* Add a new microversion and change
  nova/api/openstack/compute/server_groups.py to use it to determine
  if the 'project_id' and 'user_id' information of the server group
  should be returned.


Dependencies
============

None


Testing
=======

* Unit tests and API samples functional tests in the nova tree.
* There are currently not any compute API microversions tested in Tempest
  beyond v2.1. We could add support for testing the new version in Tempest
  but so far the API is already at least at v2.10 without changes to Tempest.


Documentation Impact
====================

 * nova/api/openstack/rest_api_version_history.rst document will be updated.
 * api-ref at https://github.com/openstack/api-site will be updated.


References
==========

* Originally reported as a bug:
    https://bugs.launchpad.net/python-novaclient/+bug/1481210

