..
    This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

=====================================================
Support re-configure deleted_on_termination in server
=====================================================

https://blueprints.launchpad.net/nova/+spec/destroy-instance-with-datavolume

This blueprint proposes to allow changing the ``deleted_on_termination``
attribute of a volume after an instance is booted.

Problem description
===================

Currently, nova support configuring ``deleted_on_termination`` for the root
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

The end user expects to be able to decide the policy by which the volumes
are preserved or destoryed at any point in the vms lifecyle.

Proposed change
===============

Add a new microversion to the Servers with volume attachments model,
to support configuring whether to delete the attached volume when the
instance is destroyed. Add ``deleted_on_termination`` property to the
request body. The ``volume_id`` parameter in the url is the volume that
will be set to ``deleted_on_termination``.

Alternatives
------------

Configure the ``delete_on_termination`` by the volume attach API (reference
to the volume attach API [1]_.), if you want to change that value with the
data volume, you could just detach and re-attach with the new value.

If you boot from volume where nova creates the root volume and
``delete_on_termination=True`` when you created the server, but if you want
to preserve the root volume after the server is deleted, you can create a
snapshot of the server.

Another option is change the exist PUT update a volume attachment API, add
``delete_on_termination`` property to the request body, and should make
the ``volumeId`` is optional in the request body. This API is typically meant
to only be used as part of a larger orchestrated volume migration operation
initiated in the block storage service via the ``os-retype`` or
``os-migrate_volume`` volume actions.

If we change this API, the current ``PUT`` API will become extremely
complicated and difficult to use. In addition, the default policy is
administrative role, which is not applicable to the current use case.

Data model impact
-----------------

None

REST API impact
---------------

Configure ``delete_on_termination`` for the volume attached to the instance.

URL: /servers/{server_id}/os-volume_attachments/{volume_id}

* Request method: PATCH (Patch volume attachment)

  Add the ``delete_on_termination`` parameter to the request body.

* Patch volume attachment API's request body:

  .. code-block:: json

    {
        "volumeAttachment": {
           "delete_on_termination": true
        }
    }

  The ``delete_on_termination`` in the request body is required:

  - It will return 400 if ``volume_id`` in the path and/or
    ``delete_on_termination`` in the request body are not specified.

  Allow admin or owner role to perform this operation and add
  'rule: system_admin_or_owner' policy.

Security impact
---------------

None

Notifications impact
--------------------

None

Other end user impact
---------------------

python-novaclient will add support for this ``PATCH`` API,
to support setting ``delete_on_termination`` parameter to
an attached volume.

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

During a rolling upgrade if this PATCH update volume attachment API
is call, the request will be reject until all hosts are upgraded.

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

* Add patch volume attachment support in nova API.
* Add microversion support.
* Add patch volume attachment API support in python-novaclient.
* Add related tests.

Dependencies
============

None

Testing
=======

* Add related unit tests for negative scenarios such as trying to call
  patch volume attachment API to update an attached volume with an older
  microversion, passing ``delete_on_termination`` with an invalid value
  like null, etc.
* Add related functional tests for normal scenarions, e.g. API samples.

Tempest testing should not be necessary since in-tree functional testing
with the CinderFixture should be sufficient for testing this feature.

Documentation Impact
====================

Add docs description about this patch volume attachment API.

References
==========

For the discussion of this feature at the Forum in Berlin:

* https://etherpad.openstack.org/p/BER-bfv-improvements
  BFV improvements, discussion on or around line 52.

For the disscussion of this feature at the Forum in Shanghai:

* https://etherpad.openstack.org/p/nova-shanghai-ptg
  Discussion on or around line 252.

.. [1] http://specs.openstack.org/openstack/nova-specs/specs/train/approved/support-delete-on-termination-in-server-attach-volume.html

.. _PATCH how to works: https://developer.mozilla.org/en-US/docs/Web/HTTP/Methods/PATCH

PoC code: https://review.opendev.org/#/c/693828/

History
=======

.. list-table:: Revisions
   :header-rows: 1

   * - Release Name
     - Description
   * - Ussuri
     - Introduced
