..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

====================================
Placement Minimum HTTP Cache Headers
====================================

https://blueprints.launchpad.net/nova/+spec/placement-cache-headers

:rfc:`7232#section-2.2` says that a web service should send a last-modified
header for any representation for a last-modified time can reasonable be
deduced. The placement service does not currently do this. Including it will
make it a better HTTP citizen and also provide useful metadata in the response.
If a last-modified header is added then it is also necessary to add a
cache-control header with a value of "no-cache" to insure that clients and
proxies are not inclined to cache representations provided by the placement
service.

Problem description
===================

By not sending appropriate cache headers, placement is presenting two small
problems:

* It is not following accepted standards for HTTP services.

* There is a chance that clients and proxies pasing requests to placement will
  cache responses from the service. Given that the majority of data provided by
  placement highly time dependent, this is problematic.


Use Cases
---------

As a user of an HTTP API I expect it to follow standards and provide me with a
``last-modified`` header that reflects the last modified time of the resource.

Proposed change
===============

In a new microversion, for any ``GET`` request handled by the placement service
add two additional headers in the response:

* ``last-modified`` with a meaningful time and data value (see below).
* ``cache-control`` with a value of ``no-cache``. See
  :rfc:`7234#section-5.2.1.4` for additional detail on what this means.

The value of the ``last-modified`` header is chosen from three different
options:

* If the request is for a singular entity directly associated with a database
  row that has an ``updated_at`` or ``created_at`` field, then the value of one
  of those fields will be used, preferring ``updated_at`` if it is set (it
  won't be if the resource has only been created but not yet updated).
* If the request is for a collection of entities that are directly associated
  with the database, the value will be the max of the ``updated_at`` or
  ``created_at`` for all the entities in the collection.
* If the request is for an entity or collection which is composed from multiple
  parts, then the value of the header will be the current time.

Alternatives
------------

A viable alternative is to do nothing. If we don't add the ``last-modified``
headers then the risk of caching is very small (as there is no conditional
header present). But then we would be bad HTTP citizens.

Another alternatives is to start using ETags within the placement service.
This would enable fairly complex and complete server-side and client-side
caching of resources, saving bandwidth and database queries. It is, however, a
fairly serious undertaking and would not remove the need for ``last-modified``
headers, so best to take smaller steps towards having the full suite of
headers.

Data model impact
-----------------

The database tables already have the desired ``updated_at`` and ``created_at``
fields but the OVO in ``nova/objects/resource_provider.py`` need to be updated
to expose those fields. This can be done by using the ``NovaTimestampObject``
mixin.

REST API impact
---------------

As stated, every GET request will get two additional headers ``cache-control:
no-cache`` and ``last-modified: <timestamp>``. These will only be exposed in
the newly created microversion.

Security impact
---------------

None.

Notifications impact
--------------------

None.

Other end user impact
---------------------

If we consider the scheduler report client to be the primary "end user" of
placement, these headers will have no impact on it, especially as the client
uses explicit microversions in its requests.

Performance Impact
------------------

A slight impact when requesting large collections. That collection is
traversed to find the last-modified value. Most of this impact can be
alleviated by combining that work in the existing traversal that creates the
JSON response body.

Other deployer impact
---------------------

None.

Developer impact
----------------

When developers add new handlers for ``GET`` requests to the placement service,
they will need to add these headers.


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

* Create a new microversion for this functionality
* Update the objects in ``nova/objects/resource_provider.py`` to expose the
  ``updated_at`` and ``created_at`` fields
* For each handler for a ``GET`` request, add the headers
* Updated gabbi tests to inspect the new headers and confirm their presence in
  the new microversion and lack of presence in older microversions
* Update placement api-ref

Dependencies
============

None.

Testing
=======

As stated in the work items, it's important to confirm that the headers show up
as expected in the new microversion. It's equally important to confirm that
they do _not_ in older microversions.


Documentation Impact
====================

None

References
==========

* `Related mailing list thread`_
* `Proof of concept`_

History
=======

.. list-table:: Revisions
   :header-rows: 1

   * - Release Name
     - Description
   * - Queens
     - Introduced

.. _Related mailing list thread: http://lists.openstack.org/pipermail/openstack-dev/2017-August/121288.html
.. _Proof of concept: https://review.openstack.org/#/c/495380/
