..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

==========================================
Remove shared storage flag in evacuate API
==========================================

https://blueprints.launchpad.net/nova/+spec/remove-shared-storage-flag-in-evacuate-api

Today evacuate API expects an onSharedStorage flag to be provided by the admin
however this information can be detected by the virt driver as well. To ease
the work of the admin and to allow easier automation of the evacuation tasks
this spec propose to remove the onSharedStorage flag from the API in a new
microversion.

Problem description
===================

Use Cases
---------
When an instance needs to be evacuated from a failed host the admin has to
check if the instance was stored on shared storage or not to issue the evacuate
command properly. The admin wants to rely on the virt driver to detect if
the instance data is available on the target host and use it if possible for
the evacuation.
An external automatic evacuation engine also wants to let nova to decide
if the instance can be evacuated without rebuilding it on the target host.

Proposed change
===============

In compute manager in the rebuild_instance function the on_shared_storage
flag is made optional with a previous spec so that the onSharedStorage
parameter now can be removed from the evacuate API.

The evacuate API supports providing a new admin password optionally. This
makes the solution a bit more complicated.
Nova can only decide if the instance is on shared storage if the target host
of the evacuation is already known which means only after the scheduler
selected the new host because nova needs to check if the disk of the instance
is visible from the target host. However the evacuation API call returns the
new admin password in the response. This logic cannot be fully kept if the
onSharedStorage flag is removed.

There are two cases to consider if the onSharedStorage flag is removed:

* Client doesn't provide admin password. Nova will generate a new password.
  If nova finds that the instance is on shared storage then
  the instance will be rebooted and will use the same admin password as before.
  If nova finds that the instance is not on shared storage then the instance
  will be recreated and the newly generated admin password will be used.
* Client provides admin password.
  If nova finds that the instance is on shared storage then
  the password the client provided will be silently ignored. If nova finds
  that the instance is not on shared storage then the provided password will
  be injected to the recreated instance.

This spec propose to

* Remove the onSharedStorage parameter of the
  /v2.1/{tenant_id}/servers/{server_id}/action API
* Remove adminPass from the response body of the API call. Admin user can still
  access the generated password via
  /v2.1/{tenant_id}/servers/{server_id}/os-server-password API

Alternatives
------------
For the automation use case the alternative would be to reimplement the
checking of the instance availability on the disk in the theoretical external
evacuation engine. However this would be a clear code duplication as nova
already contains this check in the virt driver.

Data model impact
-----------------
None

REST API impact
---------------
The onSharedStorage parameter of the
/v2.1/{tenant_id}/servers/{server_id}/action API will be removed.
So the related JSON schema would be change to the following::

    {
    'type': 'object',
    'properties': {
        'evacuate': {
            'type': 'object',
            'properties': {
                'host': parameter_types.hostname,
                'adminPass': parameter_types.admin_password,
            },
            'required': [],
            'additionalProperties': False,
        },
    },
    'required': ['evacuate'],
    'additionalProperties': False,
    }

Also the adminPass will be removed from the response body.
This would make the response body empty therefore the API response
will not return a response body instead.

Security impact
---------------
None

Notifications impact
--------------------
None

Other end user impact
---------------------
None

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
  balazs-gibizer

Work Items
----------

* Remove onSharedStorage from the evacuate REST API
* Remove adminPass and therefore the whole response body of the evacuate API


Dependencies
============
None

Testing
=======
Unit and functional test coverage will be provided.

Documentation Impact
====================
Admin guide needs to be updated with the new behavior of the evacuate
function.


References
==========
[1] The bp that made the on_shared_storage optional in compute manager in
    Liberty https://blueprints.launchpad.net/nova/+spec/optional-on-shared-storage-flag-in-rebuild-instance
[2] The code that made the  on_shared_storage optional in compute manager in
    Liberty https://review.openstack.org/#/c/197951/

History
=======

.. list-table:: Revisions
   :header-rows: 1

   * - Release Name
     - Description
   * - Mitaka
     - Introduced
