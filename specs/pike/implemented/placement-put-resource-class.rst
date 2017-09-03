..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

=============================
Idempotent PUT resource class
=============================

https://blueprints.launchpad.net/nova/+spec/placement-put-resource-class

The current method for creating or updating a custom resource class in the
placement API has two flaws which can be resolved by deprecating the existing
``POST /resource_classes`` and changing ``PUT /resource_classes/{name}`` to be
an idempotent create or validate.

Problem description
===================

Microversion 1.2 of the placement API added support for managing custom
resource classes in the usual ``POST`` to create, ``PUT`` to update style. It
turns out, however, that the most common interaction is to want to create a
custom resource class if it doesn't already exist. The current process for this
is::

    GET /resource_classes/CUSTOM_FOOBAR

If the response is ``404`` then::

    POST /resource_classes

    {"name": "CUSTOM_FOOBAR"}

If the response is successful then it was created. If the response is ``409``
then the resource class already exists and some other process created it in the
time since the ``GET``. Once could also do the ``POST`` without the ``GET`` and
accept the ``409`` as a form of success but that's not a normal form of
interaction in HTTP APIs.

Meanwhile, ``PUT`` to update has the form::

    PUT /resource_classes/CUSTOM_FOOBAR

    {"name": "CUSTOM_NEWBAR"}

This is not actually something we want to allow. We do not want existing
references to a resource class to be renamed as those updates will not be
reflected anywhere outside the placement service.

Use Cases
---------

As a developer of systems that manage custom resource classes I want to
manage them simply, efficiently and correctly.

Proposed change
===============

Since the meaning of a single custom resource class is present in just the URL
we can adjust ``PUT /resources_class/{name}`` to be an idempotent creator and
validator of a single resource class. To create a new custom resource class::

    PUT /resource_class/CUSTOM_FOOBAR
    <empty body>

    Status: 201 Created

If it might already exist, that's okay::

    PUT /resource_class/CUSTOM_FOOBAR
    <empty body>

    Status: 204 No Content

No ``GET`` or ``POST`` is required, the PUT requires no body, and the
undesirable rename behavior with the previous mechanics of the PUT request
(described in the problem statement above) will be removed.

This functionality will be implemented in a new microversion that will provide
new handler code for the ``PUT`` method. Support for the ``POST`` method (which
currently accepts a body with a name attribute) will be kept around as this
allows the new microversion to continue accepting creation requests in the old
style and this is good for stability.

If, sometime in the future, we realize we need to add additional fields to a
resource class, such as `description`, then we should again bump the
microversion to allow a ``PUT`` with a body that includes those new fields, but
does not include the resource class name. This will allow us to continue having
the desired idempotent behavior with ``PUT`` requests and will still prevent
the rename confusion (described above). Until such a time that we need those
additional fields, including a body on the PUT request is redundant so we may
as well not allow it.

Alternatives
------------

We could do nothing, but that leaves us with the potentially dangerous rename
behavior.

Data model impact
-----------------

None.

REST API impact
---------------

The main change is to add a microversion which adjusts the handling of ``PUT
/resource_classes/{name}`` so it no longer takes a body and either creates or
verifies the existence of the custom resource class identified by ``{name}``::

    PUT /resource_classes/CUSTOM_FOOBAR
    <empty body>

Successful responses include no body and have one of the following status
codes:

* `201 Created`: if the custom resource class is newly created
* `204 No Content`: if the custom resource class already exists

Possible error response codes are:

* `400 Bad Request`: if the format of the proposed resource class is not valid


Security impact
---------------

The rename problem described above is a data integrity issue that this change
resolves. The surface area of that problem is small because currently the
placement API is admin only.

Notifications impact
--------------------

None.

Other end user impact
---------------------

None.

Performance Impact
------------------

There's a very minor performance impact via the current scheduler report client
because we are now doing a maximum of one instead of two requests when handling
custom resource classes.

Other deployer impact
---------------------

Because this change is being done on a microversion, older versions of the
scheduler report client will continue to work against newer placement APIs.

Developer impact
----------------

None.


Implementation
==============

Assignee(s)
-----------

Primary assignee:
  cdent

Other contributors:
  None

Work Items
----------

* Create new handler code for ``PUT /resource_classes/{name}`` in a new
  microversion.
* Add gabbi tests that exercise the new microversion.
* Update microversion history.
* Update placement-api-ref.
* Update the scheduler report client to use the new interface.


Dependencies
============

None


Testing
=======

New gabbi and existing scheduler functional tests and tempest tests will
exercise this change.


Documentation Impact
====================

The `placement-api-ref` will need to be updated to reflect this change, but
the change has no impact on installation or configuration, so those docs should
be fine.

References
==========

* `Custom Resource Classes Spec <http://specs.openstack.org/openstack/nova-specs/specs/ocata/implemented/custom-resource-classes.html>`_


History
=======

.. list-table:: Revisions
   :header-rows: 1

   * - Release Name
     - Description
   * - Pike
     - Introduced
