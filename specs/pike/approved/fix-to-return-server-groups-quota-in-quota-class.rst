..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

==========================================================
Fix to return server groups quota in the quota-classes API
==========================================================

https://blueprints.launchpad.net/nova/+spec/fix-quota-classes-api

The quotas of `server_groups` and `server_group_members` are missed in the
response of quota-classes v2.1 API. This spec proposes to add those quotas
back to the API in new microversion.

Problem description
===================

V2 API has extension 'os-server-group-quotas', which enabled the quota
`server_groups` and `server_group_members` in the quota-classes API. But
during the porting the v2 extensions to the v2.1 API, this extension was
missed. It leads to the quota `server_groups` and `server_group_members`
missing in the response of quota-classes API.

Use Cases
---------

* As an API user, he can query the default quota value by the quota-classes
  API, and which is the same API when he set the default value.

Proposed change
===============

This spec propose to fix this bug as microversion by adding `server_groups`
and `server_group_memeber` back to the v2.1 API.

The legacy v2.1 compatible API won't be fixed, since it is as the default
backend for legacy v2 endpoint in Liberty. And Liberty is already EOL, there
is no way to back port the fix to the Liberty.

Alternatives
------------

Fix this bug without microversion for v2.1 API, it will lead to the API
interoperability issue.

Data model impact
-----------------

None

REST API impact
---------------

Add the 'server_groups' and 'server_group_members' field to the quota-classes
API by new microversion in v2.1 API.

Two fields will be added to the response of the APIs::

    GET /os-quota-class-sets/{quota_class}
    PUT /os-quota-class-sets/{quota-class}

Security impact
---------------

None

Notifications impact
--------------------

None

Other end user impact
---------------------

The python-novaclient will also need to be updated to handle the new
microversion for the python API binding and the "nova quota-class" CLIs.

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
    Ghanshyam Mann <ghanshyammann@gmail.com>

Other contributors:
    Alex Xu <hejie.xu@intel.com>

Work Items
----------

* Fix the v2.1 API by new microversion.
* Update the python-novaclient to support new microversion.

Dependencies
============

None

Testing
=======

The corresponding unittest and functional test will be added.

Documentation Impact
====================

Update the `api-ref`_ about this bug fix and the workaround to use the
`os-quota-sets` API. The reno is required to note this bug also.

References
==========

* https://bugs.launchpad.net/nova/+bug/1693168

.. _api-ref: http://developer.openstack.org/api-ref/compute/

History
=======

.. list-table:: Revisions
   :header-rows: 1

   * - Release Name
     - Description
   * - Pike
     - Introduced
