..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

================
Remove tenant_id
================

https://blueprints.launchpad.net/nova/+spec/remove-tenant-id

The blueprint proposes to remove the API interface that uses
``tenant_id`` and replace it with ``project_id``.

Problem description
===================

Currently, Nova API supports both ``tenant_id`` and ``project_id``,
which is unfriendly to users.

The following is a confusing question.
By default, we support filtering instances by ``all_tenants (Optional)``,
but through this parameter, we get a list of all instances that they
cannot get instances by ``tenant_id``.

We can see from `bug 1185290`_ that when using the ``nova list`` command,
if ``tenant_id`` is required, ``all_tenants`` must appear, as description
in [1]_, which is somewhat unintuitive.

.. note:: [1]_ mainly said: "As explained in lp:#1185290, if `all_tenants`
          is not passed we must ignore the `tenant_id` search option.".

We can know from `bug 1468992`_ that many users want to use ``tenant_id``
filtering instances, and using the concept of tenants in many of our
large-scale customer scenarios, they hope we can filter the expected
instances through ``tenant_id``.

Use Cases
---------

As an (admin) user, I would like to use ``project_id`` uniformly in nova api,
instead of supporting both ``tenant_id`` and ``project_id``.

Proposed change
===============

Add a new microversion to the request or response parameter changes API.

Remove the ``tenant_id`` field, using ``all_projects`` replace ``all_tenants``
parameter, and then remove``all_tenants`` parameter in the following APIs:

* GET /servers (List Servers)
* GET /servers/detail (List Server Detailed)

Replace ``tenant_id`` with ``project_id`` in request body in follow APIs:

* GET /limits (Show Rate And Absolute Limits)
* GET /os-quota-sets/{tenant_id} (Show A Quota)
* PUT /os-quota-sets/{tenant_id} (Update Quotas)
* GET /os-quota-sets/{tenant_id}/defaults (List Default Quotas For Tenant)
* GET /os-quota-sets/{tenant_id}/detail (Show The Detail of Quota)
* GET /os-simple-tenant-usage/{tenant_id} (Show Usage Statistics For Tenant)

Replace ``tenant_id`` with ``project_id`` in response body in follow APIs:

* GET /servers/detail (List Server Detailed)
* GET /servers/{server_id} (List Server Detailed)
* PUT /servers/{server_id} (Update Server)
* POST /servers/{server_id}/action (Rebuild Server (rebuild Action))
* GET /servers/{server_id}/os-security-groups (List Security Groups By Server)
* GET /flavors/{flavor_id}/os-flavor-access (List Flavor Access Information
                                             For Given Flavor)
* POST /flavors/{flavor_id}/action (Add Flavor Access To Tenant
                                    (addTenantAccess Action))
* POST /flavors/{flavor_id}/action (Remove Flavor Access From Tenant
                                    (removeTenantAccess Action))
* GET /os-simple-tenant-usage (List Tenant Usage Statistics For All Tenants)
* GET /os-simple-tenant-usage/{tenant_id} (Show Usage Statistics For Tenant)

The keyword ``tenant`` in the path will be replaced with ``project`` as below
APIs:

* `GET /os-simple-tenant-usage` APIs will be renamed to
  `GET /os-simple-project-usage`
* `GET /os-simple-tenant-usage/{tenant_id}` APIs will be renamed to
  `GET /os-simple-project-usage/{project_id}`

We should block change the ``tenant_id`` below the deprecated APIs:

* GET /os-security-groups (List Security Groups)
* GET /os-security-groups/{security_group_id} (Show Security Group Details)
* PUT /os-security-groups/{security_group_id} (Update Security Group)
* POST /os-security-group-rules (Create Security Group Rule)
* GET /os-cells (List Cells)
* GET /os-fping?all_tenants=1 (Ping Instances)

By the way, tenant* reference will be replaced with project* in all policies,
code and docs too.

Alternatives
------------

None

Data model impact
-----------------

None

REST API impact
---------------

Add a new microversion.

Replace ``all_tenants`` with ``all_projects`` parameter, and remove
``all_tenants`` in request body in follow APIs:

* GET /servers (List Servers)
* GET /servers/detail (List Server Detailed)

Replace ``tenant_id`` with ``project_id`` in request body in follow APIs:

* GET /limits (Show Rate And Absolute Limits)
* GET /os-quota-sets/{tenant_id} (Show A Quota)
* PUT /os-quota-sets/{tenant_id} (Update Quotas)
* GET /os-quota-sets/{tenant_id}/defaults (List Default Quotas For Tenant)
* GET /os-quota-sets/{tenant_id}/detail (Show The Detail of Quota)
* GET /os-simple-tenant-usage/{tenant_id} (Show Usage Statistics For Tenant)
* GET /os-cells (List Cells)

Replace ``tenant_id`` with ``project_id`` in response body in follow APIs:

* GET /servers/detail (List Server Detailed)
* GET /servers/{server_id} (List Server Detailed)
* PUT /servers/{server_id} (Update Server)
* POST /servers/{server_id}/action (Rebuild Server (rebuild Action))
* GET /servers/{server_id}/os-security-groups (List Security Groups By Server)
* GET /flavors/{flavor_id}/os-flavor-access (List Flavor Access Information
                                             For Given Flavor)
* POST /flavors/{flavor_id}/action (Add Flavor Access To Tenant
                                    (addTenantAccess Action))
* POST /flavors/{flavor_id}/action (Remove Flavor Access From Tenant
                                    (removeTenantAccess Action))
* GET /os-simple-tenant-usage (List Tenant Usage Statistics For All Tenants)
* GET /os-simple-tenant-usage/{tenant_id} (Show Usage Statistics For Tenant)

Security impact
---------------

None

Notifications impact
--------------------

None

Other end user impact
---------------------

Update openstacksdk, python-novaclient and python-openstackclient
for the new microversion.

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
  brinzhang

Feature Liaison
---------------

Feature liaison:
  brinzhang

Work Items
----------

* Replace ``tenant_id`` with ``project_id`` in relate APIs,
  policies and code.
* Replace ``all_tenants`` with ``all_projects`` in relate APIs,
  policies and code.
* Add related tests.
* Docs for the new microversion.
* Check the python-novaclient , python-openstackclient and openstacksdk,
  just support requesting ``project_id`` in related APIs.

Dependencies
============

None

Testing
=======

* Add related unit test for negative scenarios.
* Add related functional test (API samples).

Tempest testing should not be necessary for this change.

Documentation Impact
====================

Update the API reference for the new microversion, and update all uses of
``tenant`` to ``project`` in all docs and code.

References
==========

.. _`bug 1185290`: https://bugs.launchpad.net/nova/+bug/1185290
.. _`bug 1468992`: https://bugs.launchpad.net/nova/+bug/1468992

.. [1] Mainly info: https://opendev.org/openstack/nova/src/branch/stable/ussuri/nova/api/openstack/compute/servers.py#L294-L295

History
=======

.. list-table:: Revisions
   :header-rows: 1

   * - Release Name
     - Description
   * - Wallaby
     - Introduced
