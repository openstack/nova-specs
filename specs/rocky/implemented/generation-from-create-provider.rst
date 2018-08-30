..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

=================================================
Return Generation from Resource Provider Creation
=================================================
https://blueprints.launchpad.net/nova/+spec/generation-from-create-provider

To facilitate opaqueness of resource provider generation internals, we need to
return the (initial) generation when a provider is created. For consistency
with other APIs, we will do this by returning the entire resource provider
record (which includes the generation) from `POST /resource_providers`_.

Problem description
===================
As described in `bug 1746075`_, placement API consumers have an awkward time
handling the initial generation of a newly-created resource provider.  The Nova
report client deals with it by assuming the initial generation is ``0``, which
violates the intended opaqueness of the generation in the API.

Use Cases
---------
As a consumer of the placement API, I want to be able to glean the initial
generation value of a freshly-created provider while preserving its opaqueness.

Proposed change
===============
In a new microversion, the `POST /resource_providers`_ API shall, upon success,
return ``200`` with a payload representing the resource provider record.  This
payload will be identical to what would be returned by `GET
/resource_providers/{uuid}`_ at the current microversion.

Alternatives
------------
#. Immediately follow `POST /resource_providers`_ with `GET
   /resource_providers/{uuid}`_, using URI in the location header returned by
   the ``POST``.  This would work fine, but it's an extra REST call.  The
   proposed implementation is more convenient.
#. Assume the initial generation of a provider is ``0``.  While this happens to
   be true, the assumption violates the intended opaqueness of the generation
   in the API.

Data model impact
-----------------
None

REST API impact
---------------
See `Proposed change`_.  The input spec is identical except for the
``Openstack-API-Version`` header.  The difference in the response is:

* On success, instead of ``201``, the new microversion will respond ``200``.
* On success, instead of an empty body, the new microversion will include a
  JSON payload representing the record of the newly-created resourcec provider,
  in a format identical to the response of `GET /resource_providers/{uuid}`_ at
  the current microversion.

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
Developers have a convenient way to glean the generation of a newly-created
provider without additional API calls.

Upgrade impact
--------------
Until their minimum required placement microversion is at least the
microversion produced by this spec, clients implementing this feature will need
to fall back to one of the `Alternatives`_ when 406 is received.

Implementation
==============
Assignee(s)
-----------
Primary assignee:
  efried

Work Items
----------
* Add a new micro-versioned handler in
  ``nova.api.openstack.placement.handlers.resource_provider.create_resource_provider``
  to return ``200`` with the provider payload.
* Update the placement-api-ref.

Dependencies
============
None

Testing
=======
Gabbits will be added to validate the new behavior.

Documentation Impact
====================
* Update the placement API reference section for `POST /resource_providers`_.
* Update the `REST API Version History`_.

References
==========
* The `POST /resource_providers`_ API documentation.
* `bug 1746075`_
* The `GET /resource_providers/{uuid}`_ API documentation.
* The placement `REST API Version History`_ documentation.

.. _POST /resource_providers: https://developer.openstack.org/api-ref/placement/#create-resource-provider
.. _bug 1746075: https://bugs.launchpad.net/nova/+bug/1746075
.. _GET /resource_providers/{uuid}: https://developer.openstack.org/api-ref/placement/#show-resource-provider
.. _REST API Version History: https://docs.openstack.org/nova/latest/user/placement.html#rest-api-version-history

History
=======
.. list-table:: Revisions
   :header-rows: 1

   * - Release Name
     - Description
   * - Rocky
     - Introduced
