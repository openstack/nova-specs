..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

======================================================
Add generation to aggregate association representation
======================================================

https://blueprints.launchpad.net/nova/+spec/placement-aggregate-generation

As resource provider handling has evolved, it has become clear that virt
drivers may wish to manage a complex collection of interrelated resource
providers, resource classes, traits and aggregates. Some of those entities
may need to be managed by multiple threads of processing, including
different nova-compute processes.

The `generation` concept in the placement service provides a tool for managing
these kind of concurrent operations: a write API request that includes a
generation has that generation compared against the value on the server. If
there is a match the request can go ahead, otherwise a ``409 Conflict``
response is returned.

This functionality is not present when associating or disassociating a resource
provider with one or more aggregate uuids. For virt drivers that wish to manage
aggregate associations safely, this is necessary. This spec describes the
changes necessary to add the functionality.

Problem description
===================

As stated above, a virt driver may wish to manage resource provider aggregate
associations in a thread-safe fashion. Since aggregate association does not
currently use the `generation` mechanism for managing concurrency, this is not
possible. The main concern is with accidentally removing an aggregate that some
other thread B has set when setting aggregates from thread A, or re-adding one
that thread B removed.

Use Cases
---------

As the developer of a virt driver that manages resources that might be shared
between compute-nodes (for example storage in a PowerVM or vCenter that is used
by multiple clusters) I would like to be able to ensure that I am not
clobbering aggregate associations that another thread may have set when setting
associations myself.

Proposed change
===============

In a new microversion the representation of ``GET`` and ``PUT``
``/resource_providers/{uuid}/aggregates`` will be updated to a) be the same for
both methods and, b) include a ``resource_provider_generation`` attribute that
has as its value the `generation` of the resource provider identified by
``{uuid}``.

When processing a ``PUT`` request, if the `generation` does not match the
current (server-side) generation of the resource provider, the request will be
rejected with a ``409 Conflict`` response.

Details of representation changes can be found below.

Alternatives
------------

We can consider doing nothing. Initially we didn't think we would need this
functionality because the expectation was that there wouldn't be multiple
threads attempting to manage the aggregate associations for a single resource
provider. The canonical example is the shared storage resource described above.
In that instance, multiple compute-nodes will want to manage the aggregate
associations.

We'd like to support that, so doing nothing isn't really an alternative.

Data model impact
-----------------

The data model will not change. The persistence of aggregate associations will
remain the same.

REST API impact
---------------

.. highlight:: javascript

The format ``GET /resource_providers/{uuid}/aggregates`` will change to add a
``resource_provider_generation`` field::

    {
        "aggregates": [
            "42896e0d-205d-4fe3-bd1e-100924931787",
            "5e08ea53-c4c6-448e-9334-ac4953de3cfa"
        ],
        "resource_provider_generation": 5
    }

Valid response codes will remain the same.

The `previous get format`_, introduced in microversion 1.1, does not include
the generation field.

The format for ``PUT /resource_providers/{uuid}/aggregates`` will be identical
to the GET format (above). This is different from the `previous put format`_ in
that now, instead of a bare list of UUIDs there is an object with two fields:
``aggregates`` (taking a list of UUIDs), and ``resource_provider_generation``
(taking a non-negative integer).  JSON Schema will be updated to reflect these
requirements.

In addition to the existing 200, 400 and 404 response codes currently possible
when calling ``PUT /resource_providers/{uuid}/aggregates``, a ``409 Conflict``
response code will be returned when the ``resource_provider_generation`` field
does not match the server-side value.

Security impact
---------------

N/A

Notifications impact
--------------------

N/A

Other end user impact
---------------------

The osc-placement plugin could be updated to reflect this new functionality.

Performance Impact
------------------

N/A

Other deployer impact
---------------------

N/A

Developer impact
----------------

With this functionality, virt driver developers will be able to more
effectively manage aggregate associations using the ProviderTree mechanism.

Upgrade impact
--------------

N/A


Implementation
==============

Assignee(s)
-----------

Primary assignee:
  cdent

Other contributors:
  efried

Work Items
----------

* Create JSON Schema for a new microversion of
  `PUT /resource_providers/{uuid}/aggregates`.
* Add new micro-versioned handlers to support the new formats for GET and PUT
  with gabbi-driven tests.
* Adjust the ``ResourceProvider.set_aggregates`` method to `optionally` use
  the ``_increment_provider_generation`` and raise ``ConcurrentUpdateDetected``
  when the generation does not match, resulting in a ``409 Conflict`` being
  sent as the response.
* Update the placement-api-ref.


Dependencies
============

N/A


Testing
=======

Gabbi tests which cause expected 409 responses should be sufficient for testing
this feature.

Documentation Impact
====================

placement-api-ref updates should be sufficient.

References
==========

* `previous get format`_ (microversion 1.1)
* `previous put format`_ (microversion 1.1)

.. _previous get format: https://developer.openstack.org/api-ref/placement/#list-resource-provider-aggregates
.. _previous put format: https://developer.openstack.org/api-ref/placement/#update-resource-provider-aggregates


History
=======

.. list-table:: Revisions
   :header-rows: 1

   * - Release Name
     - Description
   * - Rocky
     - Introduced
