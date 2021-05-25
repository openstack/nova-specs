..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.
 http://creativecommons.org/licenses/by/3.0/legalcode

===============================================
Allow Project admin to list allowed hypervisors
===============================================

https://blueprints.launchpad.net/nova/+spec/allow-project-admin-list-hypervisors

Allow Project admin to get the allowed hypervisors info so that
they can create a server to specify the host in ``POST /servers`` API.

Problem description
===================

Project admin can currently create a server on a specific hypervisor (via host
in the availability_zone field). However, project admin is not allowed to
`list the hypervisors`__ On the other hand, only system admins or system
readers can list hypervisors, but they cannot create a server on the project's
behalf because there is no way to pass the `project_id in POST /servers API`__.
This way, we make 'POST /servers with specific host' unusable unless the user
gives extra token permission to the project admin or system users.

__ https://github.com/openstack/nova/blob/b0cd985f0c09088098f74cc0cb1df616cc0ef12b/nova/policies/hypervisors.py#L37
__ https://github.com/openstack/nova/blob/b0cd985f0c09088098f74cc0cb1df616cc0ef12b/nova/api/openstack/compute/schemas/servers.py#L149


Use Cases
---------

As a user (project admin currently and project manager in new RBAC), I should
be able to create the server on specific host which is assigned in that
project.

Proposed change
===============
Below are the three proposed changes:

#. ``GET /os-hypervisors`` API

   Allow project admin to list ``uuid``, ``state``, and, ``status``
   of the hypervisors they are assigned to. That will be retrieved from
   aggregate metadata info (``filter_tenant_id``).

   If the requested project is in ``filter_tenant_id`` then that host info will
   be listed for project admin. If no project is listed in ``filter_tenant_id``
   then return an empty list. Only below hypervisors' fields will be returned
   for project admin, and the rest of the fields will be returned with value
   as None.

   * uuid
   * state
   * status

   A new API policy will be introduced to switch the above behaviour to return
   the complete list of hypervisors info to allowed users.

   No change in returning the hypervisors list for System scoped users.

#. ``POST /servers`` API

   ``POST /servers`` API will start accepting hypervisor uuid in request field
   to boot the server on that hypervisor. The existing field
   ``hypervisor_hostname`` is used to pass the hypervisor name and we will not
   change that for existing use case. We will add a new field
   ``hypervisor_uuid`` in request so that user can pass hypervisor uuid. The
   hypervisor uuid will be used to boot the server for for host with scheduler
   run case.

#. Remove the legacy hack of passing the host and node in ``availability_zone``
   request field. This will be removed for newer microversion only and keep it
   same for older microversion.

   This is legacy hack to force the server boot on requested host and node.
   This one - https://github.com/openstack/nova/blob/e28afc564700a1a35e3bf0269687d5734251b88a/nova/compute/api.py#L555-L561
   Removing this legacy hack will standaradize the 'server boot on requested
   host' request.

Alternatives
------------

System users knowing the hypervisor info can switch to the project admin token
and boot server on specific host.

Data model impact
-----------------

None.

REST API impact
---------------

This change will be done with a microversion bump.

Below are the two APIs that will be changed:

``GET /os-hypervisors``

- Allow policy 'os_compute_api:os-hypervisors:list' to project admin also
  (scope to system and project).

- Check if the requester is system user or project admin (via request context's
  system_scope). For system users no change in API from what we have currently.
  For project admin, return ``uuid``, ``state``, and ``status`` of
  those hosts which are assigned to that project, and the rest of the fields
  will be returned with value as None.

  .. code-block::

     {
       "hypervisors": [
           {
               "hypervisor_hostname": None,
               "id": "1bb62a04-c576-402c-8147-9e89757a09e3",
               "state": "up",
               "status": "enabled"
           }
       ],
       "hypervisors_links": None
     }

``POST /servers``

- ``POST /servers`` API will start accepting hypervisor uuid in request field
  to boot the server on that hypervisor. We will add a new  field
  ``hypervisor_uuid`` in create server request so that user can pass uuid.
  The hypervisor uuid will be used to boot the server for host with scheduler
  run case.

- Remove the legacy hack of passing the host and node in ``availability_zone``
  request field. For older microversions, it will keep working as it is working
  currently. With this new microversion, only a valid AZ will be accepted in
  ``availability_zone`` field otherwise 404. Basically removing this legacy
  hack - https://github.com/openstack/nova/blob/e28afc564700a1a35e3bf0269687d5734251b88a/nova/compute/api.py#L555-L561


Security impact
---------------

None. Already assigned host uuid name will be listed to project admin also.

Notifications impact
--------------------

None.

Other end user impact
---------------------

The nova api-ref will updated to reflect the changes.

Performance Impact
------------------

None.

Other deployer impact
---------------------

None.

Developer impact
----------------

None.

Upgrade impact
--------------

Upgrade notes will be added for the new workflow of boot server on
specific host.

Implementation
==============

Assignee(s)
-----------

Primary assignee:
  gmann
Other contributors:
  None

Feature Liaison
---------------

Feature liaison:
  None

Work Items
----------

- API changes with microversion
- Testing for the changes.

Dependencies
============

None.

Testing
=======

- Unit or functional testing for API change.
- Tempest test to boot server with hypervisor uuid.

Documentation Impact
====================

The api-ref will be updated to reflect the changes.

References
==========

* https://etherpad.opendev.org/p/nova-xena-ptg
* https://review.opendev.org/c/openstack/nova-specs/+/779821
* https://github.com/openstack/nova/blob/b0cd985f0c09088098f74cc0cb1df616cc0ef12b/nova/policies/servers.py#L179

History
=======

.. list-table:: Revisions
   :header-rows: 1

   * - Release Name
     - Description
   * - Yoga
     - Introduced
