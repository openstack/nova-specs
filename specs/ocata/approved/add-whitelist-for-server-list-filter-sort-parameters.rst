..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

======================================================================
Add whitelist for filter and sort query parameters for server list API
======================================================================

https://blueprints.launchpad.net/nova/+spec/add-whitelist-for-server-list-filter-sort-parameters

Currently the filtering and sorting parameters which can be used for server
list/detail API are not explicitly defined. That leads to some bugs and
problems in the API. This spec aims to add a strict set of whitelisted
filtering and sorting parameters for server list/detail operations.

Problem description
===================

The query parameters for server list/detail API are not limited and
controlled at API layer. This leads to some problems:

* The DB schema exposes to the REST API directly. For example, if a new column
  added to the DB schema, the new column will be enabled as filter and sort
  parameter directly. This break the API rule: New feature needs to enable with
  microversion bump.
* The joined-table and the internal attributes of DB model object expose to the
  REST API. For example, the joined-table `extra` and the internal attributes
  `__mapper__`, if filtering or sorting based on those parameters,
  the API returns `HTTP Internal Server Error 500`.

Use Cases
---------

* Avoid to expose the joined-table/internal attribute of DB object to the API
  user.
* There isn't random query parameters enabled without microversion.

Proposed change
===============

According to the consistent direction [0]. This spec proposes:

* Return `HTTP Bad Request 400` for the filters/sort keys which are joined
  table (`block_device_mapping`, `extra`, `info_cache`, `system_metadata`,
  `metadata`, `pci_devices`, `security_groups`, `services`) and db model object
  internal attributes (there is long, they are like `__class__`,
  `__contains__`, `__copy__`, `__delattr__`...).
* Ignore the filter and sort parameters which aren't mapping to the REST API
  representation.

The whitelist for REST API filters are ['user_id', 'project_id', 'tenant_id',
'launch_index', 'image_ref', 'image', 'kernel_id', 'ramdisk_id', 'hostname',
'key_name', 'power_state', 'vm_state', 'task_state', 'host', 'node',
'flavor', 'reservation_id', 'launched_at', 'terminated_at',
'availability_zone', 'name', 'display_name', 'description',
'display_description', 'locked_by',
'uuid', 'root_device_name', 'config_drive', 'access_ip_v4', 'access_ip_v6',
'auto_disk_config', 'progress', 'sort_key', 'sort_dir', 'all_tenant',
'deleted', 'limit', 'marker', 'status', 'ip', 'ip6', 'tag', 'not-tag',
'tag-any', 'not-tag-any']

For the non-admin user, there have a whitelist for filters already [1]. That
whitelist will be kept. In the future, we hope to have same list for the admin
and non-admin users.

The policy 'os_compute_api:servers:detail:get_all_tenants' and
'os_compute_api:servers:index:get_all_tenants' are deprecated. The default rule
changes to '@'. In next release, it will be removed.

The new rule 'os_compute_api:servers:all_tenants_visible' is introduced
instead. It is a soft enforcement rule. When the user can't pass the rule, the
API still return successfully, but the user only can see his own instances. The
default rule is `rule:admin_api`.

The whitelist for sorts are pretty similar with filters.
['user_id', 'project_id', 'launch_index', 'image_ref', 'kernel_id',
'ramdisk_id', 'hostname', key_name', 'power_state', 'vm_state', 'task_state',
'host', 'node', 'instance_type_id', 'launched_at',
'terminated_at', 'availability_zone', 'display_name', 'display_description',
'locked_by', 'uuid', 'root_device_name', 'config_drive', 'access_ip_v4',
'access_ip_v6', 'auto_disk_config', 'progress')

The sorts whitelist compare to the filters, some parameters which aren't
mapping to the API representation are removed, and tags filters, pagination
parameters.

For the non-admin user, the sort key 'host' and 'node' will be excluded. Those
two columns are about the cloud internal. It can't be leaked to the end user.

Alternatives
------------

Initially we expect to have very smaller whitelist and remove most of
parameters without db index. But that way has risk to break the
API users. And even we shrink the list to very small list, it still needs
a ton of index. The mail[0] have the detail for the problem.

Data model impact
-----------------

None

REST API impact
---------------

* Request `HTTP BadRequest 400` for internal joined-table and internal
  attributes.
* Few filters and sorts which aren't mapping to the REST API representaion
  will be ignored in all microversions.
* The default behaviour of `all_tenants` changed. The new soft enforcement rule
  is instead of the hard enforcement rule. The API behavours is as below for
  a fresh install of Nova:

  * For non-admin user, list servers with `all_tenants=True`, it will pass the
    old rule `os_compute_api:servers:index:get_all_tenants`, and fails the new
    rule `os_compute_api:servers:all_tenants_visible`. Then the API returns
    successfully, but the response is still only includes the user-owned
    instances.
  * For admin user, list servers with `all_tenants=True`, it will pass the old
    rule and the new rule. Then the API returns successfully, and the response
    will includes all the instances from all the tenants.


Security impact
---------------

The whitelist of query parameters is introduced. There isn't any random db
columns exposed to the user directly, which may leads to DoS attack.

Notifications impact
--------------------

None

Other end user impact
---------------------

Few filters and sorts which aren't mapping to the API REST representaion will
be ingored.

Performance Impact
------------------

None

Other deployer impact
---------------------

The new `os_compute_api:servers:all_tenants_visible` is introduced. The
old rule `os_compute_api:servers:index:get_all_tenants` and
`os_compute_api:servers:detail:get_all_tenants` is deprecated. The default
of old rules are changed to '@' in Ocata. The old rule will be removed in the
future.

For a fresh install of Nova, the API behaviour is just as the description
in the `REST API impact`_ section.

For a upgrade of Nova from Newton, if the `policy.json` has an explicit setting
which is the old default of admin-only or a custom rule. This overrides the
default in code change to `@` for the old rules. The API behaviour will be same
as before, when the request can't pass the old rule check, the API returns
`HTTP Forbidden 403`.


Developer impact
----------------

The developer needs to add new query parameters explicitly in the future.
And using the json-schema to validate the query parameters for server list/
detail API.

Implementation
==============

Assignee(s)
-----------

Primary assignee:
  ZhenYu Zheng <zhengzhenyu@huawei.com>

Other contributors:
  Alex Xu <hejie.xu@intel.com>

Work Items
----------

1. Add query parameter white list for server index/detail API.
2. Add sort parameter white list for sort_keys.
3. Add doc illustrate how to correctly use filter and sort params
   when list servers

Dependencies
============

https://blueprints.launchpad.net/nova/+spec/consistent-query-parameters-validation

Testing
=======

Few unittest needs to be adjusted to work correctly. All the unittest and
functional should be passed after the change.

Documentation Impact
====================

The devref need to describe which parameters can be used.

References
==========

[0] `http://lists.openstack.org/pipermail/openstack-dev/2016-December/108944.html`
[1] `https://github.com/openstack/nova/blob/f8a81807e016c17e6c45d318d5c92ba0cc758b01/nova/api/openstack/compute/servers.py#L1103`

History
=======

.. list-table:: Revisions
   :header-rows: 1

   * - Release Name
     - Description
   * - Ocata
     - Introduced
