..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

========================================
Filter Resource Provider List for Traits
========================================
https://blueprints.launchpad.net/nova/+spec/traits-on-list-resource-providers

Partly for continued parity with `GET /allocation_candidates`_ and partly
because we need it for a `bug`_ fix, this spec proposes to add the
``?required=<trait_list>`` queryparam filter to the `GET /resource_providers`_
placement API.

Problem description
===================
Use Cases
---------
As a Nova developer consuming the placement API, I want to be able to retrieve
all and only the sharing providers (those with the
``MISC_SHARES_VIA_AGGREGATE`` trait) associated via aggregate with my compute
node.

Proposed change
===============
In a new microversion, allow the `GET /resource_providers`_ API to accept an
additional query parameter, ``required``, which accepts a comma-separated list
of string trait names.  When specified, the API results will be filtered to
include only resource providers marked with *all* the specified traits.

This is in addition to (logical ``AND``) any filtering based on other query
parameters.

Trait names which are empty, do not exist in the Trait database, or are
otherwise invalid will result in a 400 error.

Alternatives
------------
For the specific example in `Use Cases`_, first retrieve the full list of
resource providers associated via aggregate with my compute node; then iterate
through each of those, invoking the `GET /resource_providers/{uuid}/traits`_
API, looking for the ``MISC_SHARES_VIA_AGGREGATE`` trait in the result, and
keeping only the providers where that trait is present.  This is what we may
need to backport to fix_ the bug_ which prompted this spec.

Data model impact
-----------------
None

REST API impact
---------------
See `Proposed change`_.  The parameter is optional.  It does not result in the
addition of any new response codes.

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
This should result in a performance improvement by reducing the number of
placement API calls from N+1 to 1, where N is the number of providers that
would be returned by the initial call to `GET /resource_providers`_ in the
absence of the new query parameter.  It is expected that the additional
processing on the placement server will be negligible compared to the overhead
of these additional API calls.  (And that processing would have been needed on
the client side anyway.)

Other deployer impact
---------------------
None

Developer impact
----------------
Developers have a convenient way to get trait-filtered lists of resource
providers in a single API call.

Upgrade impact
--------------
Until their minimum required placement microversion is at least the
microversion produced by this spec, clients implementing this feature will need
to invoke fallback code such as described in `Alternatives`_ when 406 is
received.

Implementation
==============
Assignee(s)
-----------
Primary assignee:
  efried

Work Items
----------
* Create JSON Schema for a new microversion of `GET /resource_providers`_.
* Add a new micro-versioned handler in
  ``nova.api.openstack.placement.handlers.resource_provider.list_resource_providers``
  to accept the new ``required`` parameter and add it to ``filters``.
* Adjust the ``ResourceProviderList.get_all_by_filters`` method to additionally
  filter on the specified trait names.
* Update the placement-api-ref.

Dependencies
============
None

Testing
=======
Gabbits will be added to validate the query parameter.

Documentation Impact
====================
* Update the placement API reference section for `GET /resource_providers`_.
* Update the `REST API Version History`_.

References
==========
* The bug_ that prompted this change.
* The fix_ required if this API change is not implemented.
* The `GET /allocation_candidates`_ API documentation.
* The `GET /resource_providers`_ API documentation.
* The `GET /resource_providers/{uuid}/traits`_ API documentation.
* The placement `REST API Version History`_ documentation.

.. _bug: https://bugs.launchpad.net/nova/+bug/1750084
.. _fix: https://review.openstack.org/#/c/545494/1/nova/scheduler/client/report.py@485
.. _GET /allocation_candidates: https://developer.openstack.org/api-ref/placement/#list-allocation-candidates
.. _GET /resource_providers: https://developer.openstack.org/api-ref/placement/#list-resource-providers
.. _GET /resource_providers/{uuid}/traits: https://developer.openstack.org/api-ref/placement/#list-resource-provider-traits
.. _REST API Version History: https://docs.openstack.org/nova/latest/user/placement.html#rest-api-version-history

History
=======
.. list-table:: Revisions
   :header-rows: 1

   * - Release Name
     - Description
   * - Rocky
     - Introduced
