..
    This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

====================================================
Support re-configure delete_on_termination in server
====================================================

https://blueprints.launchpad.net/nova/+spec/destroy-instance-with-datavolume

This blueprint proposes to allow changing the ``delete_on_termination``
attribute of a volume after an instance is booted, or set the new volume's
``delete_on_termination`` during swap volume.

Problem description
===================

Currently, nova supports configuring ``delete_on_termination`` for the root
disk and data volume (refrerence to the volume attach API [1]_.) when the
instance is created, but does not allow it to be updated after the instance
is created.

Use Cases
---------

In large scale environment, lots of resources can be created in system, and
sometimes some discarded instances need to cleaned up from the production
environment.

As the admin that is tasked with cleaning up the production environment
may be distinct from the user that created the instances, it is desirable
to be able to alter the ``delete_on_termination`` property to either
preserve important data while freeing compute resources or freeing
storage space and cleaning up sensitive data.

As an admin user, I expect that I can set ``delete_on_termination``
during swap volume.

The end user expects to be able to decide the policy by which the volumes
are preserved or destoryed at any point in the vms lifecyle.

Proposed change
===============

Add a new microversion to the Servers with volume attachments model,
to support configuring whether to delete the attached volume when the
instance is destroyed. Add ``delete_on_termination`` property to the
request body. The ``volume_id`` parameter in the url is the volume that
will be set to ``delete_on_termination``.

Change swap volume policy's rule name to
``os_compute_api:os-volumes-attachments:swap``, and make the original
policy's rule name (``os_compute_api:os-volumes-attachments:update``)
allow the update a volume atachment API.

Add 'rule:system_admin_or_owner' policy to the update volume API.

After this change, the update volume attachment API will have two policies,
one for general updates (currently only ``delete_on_termination``) and one
for admins which allows changing the volume id (i.e. swap volume) as well
as other attributes. In other words, the swap policy is a superset of the
update policy.

Alternatives
------------

Configure the ``delete_on_termination`` by the volume attach API (reference
to the volume attach API [1]_.), if you want to change that value with the
data volume, you could just detach and re-attach with the new value.

If you boot from volume where nova creates the root volume and
``delete_on_termination=True`` when you created the server, but if you want
to preserve the root volume after the server is deleted, you can create a
snapshot of the server.

Another option is add a PATCH volume attachment API, allowing a
``delete_on_termination`` property in the request body to support updating
the attached volume, but that will break the nova API and introduce a new
PATCH method.

Data model impact
-----------------

None

REST API impact
---------------

Configure ``delete_on_termination`` for the volume attached to the instance.

URL: /servers/{server_id}/os-volume_attachments/{volume_id}

* Request method: PUT (Update a volume attachment)

  Add the ``delete_on_termination`` parameter to the request body.

* Update a volume attachment API's request body:

  .. code-block:: json

    {
        "volumeAttachment": {
           "volumeId": "a07f71dc-8151-4e7d-a0cc-cd24a3f11113",
           "delete_on_termination": true
        }
    }

  Other than ``volumeId``, as of the new microversion only
  ``delete_on_termination`` may be changed from the current value. Otherwise,
  that will be return 400.

Add 'rule:system_admin_or_owner' policy role to the
update a volume attachment API.

Security impact
---------------

None

Notifications impact
--------------------

None

Other end user impact
---------------------

python-novaclient will be updated to support changing
the ``delete_on_termination`` flag.

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
  zhangbailin

Feature Liaison
---------------

Feature liaison:
  zhangbailin

Work Items
----------

* Add a new microversion which enables code that allows updating
  ``delete_on_termination`` during a PUT request.
* Change the original policy role name for update a volume attachment API.
* Add new policy to the update a volume attachment API.
* Change python-novaclient to support this microversion.
* Add related tests.

Dependencies
============

None

Testing
=======

* Add related unit tests for negative scenarios such as trying to call
  update a volume attachment API to update an attached volume with an older
  microversion, passing ``delete_on_termination`` with an invalid value
  like null, etc.
* Add related functional tests for normal scenarions, e.g. API samples.

Tempest testing should not be necessary since in-tree functional testing
with the CinderFixture should be sufficient for testing this feature.

Documentation Impact
====================

Add docs description about this microversion.

References
==========

For the discussion of this feature at the Forum in Berlin:

* https://etherpad.openstack.org/p/BER-bfv-improvements
  BFV improvements, discussion on or around line 52.

For the disscussion of this feature at the Forum in Shanghai:

* https://etherpad.openstack.org/p/nova-shanghai-ptg
  Discussion on or around line 252.

.. [1] http://specs.openstack.org/openstack/nova-specs/specs/train/approved/support-delete-on-termination-in-server-attach-volume.html

History
=======

.. list-table:: Revisions
   :header-rows: 1

   * - Release Name
     - Description
   * - Ussuri
     - Introduced
