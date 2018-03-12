..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

==========================
Placement Forbidden Traits
==========================

https://blueprints.launchpad.net/nova/+spec/placement-forbidden-traits

Whereas we have explored the diversity of queries that need to be made against
the Placement API to retrieve resource providers and allocation candidates it
is known that being able to express "not having traits X, Y and Z" is a worthy
pursuit.

Therefore we resolve to add support for additional query syntax (described
below) that will allow such queries to both ``GET /resource_providers`` and
``GET /allocation_candidates``.

Problem description
===================

Traits can be used to signal that a resource provider is special in some
fashion. In those cases, it is useful to be able to say "don't use this special
thing for this non-special workload". This allows the special resources to be
preserved. In order for clients like the Nova scheduler to express this
requirement, the Placement API needs additional query syntax.

This is considered a generally useful expression in the API, even if the use
cases (below) may be resolvable with other tooling.

Use Cases
---------

As an operator of a baremetal service I wish to preserve my expensive GPU
loaded hardware for paying bitcoin miners and would prefer to add traits to my
hardware in a positive fashion. That is, I want to trait the hardware with
CUSTOM_MASSIVE_GPU and not have to put CUSTOM_NOT_MASSIVE_GPU on everything
else. Instead flavors and other forms of workload request would be able to
express NOT CUSTOM_MASSIVE_GPU.

Similarly some operators, deployers, and toolmakers wish to be able to trait
a branch of a tree of nested resource providers as indicating that the branch
belongs to some group or purpose and then be able to express "not that group".

Proposed change
===============

Adjust the handling of the ``required`` parameter so that traits can be
expressed as required to be present or required to be *not* present. Traits
which are required to be not present are prefixed with a '!'. In the following
example we require ``STORAGE_DISK_SSD`` and *not* ``CUSTOM_GOLDEN_RAID``::

    GET /resource_providers?resources=DISK_GB&required=STORAGE_DISK_SSD,!CUSTOM_GOLDEN_RAID

This syntax has the advantage of not requiring a new query parameter, which
might be a good thing. It, however, has the cost of what might be considered
too much encoding and a lack of visibility. '!', however, is frequently
understood to mean "not".

More specifics below.

.. note:: This spec does not enumerate any changes required in nova-scheduler's
          handling of flavor extra specs or image metadata to pass not-required
          traits to the placement API. Such work should be explained in its own
          spec. However, the existing handling of traits in Nova is important
          when considering the syntax; see the alternative below.

Alternatives
------------

The syntax of this change is ripe for bikeshedding, so this list of
alternatives is far from complete, but one example:

Add a new query parameter, ``forbidden``, which is the opposite of ``required``
and has the same syntax. It means "traits listed here should not be in the
results".

This format could be easier to manage and reason about (for *existing* users)
because the existing syntax in flavor extra specs looks like this::

    "trait:$TRAIT_NAME": "required"

This suggests that forbidden would work well as::

    "trait:$TRAIT_NAME": "forbidden"

Whether that syntax should be reflected on the placement side or not is
unclear. The author of this spec feels that two different query parameters for
the same type of thing is confusing, but can certainly understand that this
alternative could work well and feelings are often insufficient justification
for syntax.


Data model impact
-----------------

No changes would be required in the data models themselves, however changes
would be required in data queries to exclude the resource providers that have
the traits that must not be present.

REST API impact
---------------

A new microversion will be created which will update the validation for the
``required`` parameter on ``GET /allocation_candidates`` and ``GET
/resource_providers`` to accept ``!`` as a prefix on listed traits to express
that the prefixed trait is required to be not present in the results.

Those traits which are forbidden will then be passed to the
``ResourceProviderList.get_all_by_filters`` or
``AllocationCandidates.get_by_requests`` methods as required.

A trait that is prefixed with ``!`` that is a duplicate of a trait listed
elsewhere in the ``required`` parameter is an error and will result in a ``400
Bad Request`` response. No whitespace is allowed between the ``!`` and the
trait. Whitespace before or after the phrase of the ``!`` and the trait is
allowed and will be stripped.

A malformed trait will result in a ``400 Bad Request`` response (this is
already the case).

If the alternative format is chosen, the validation (and the associated
response codes) of ``forbidden`` will be the same as that used for
``required``.


Security impact
---------------

N/A

Notifications impact
--------------------

N/A

Other end user impact
---------------------

N/A

Performance Impact
------------------

Queries to the database will see a moderate increase in complexity but existing
table indexes should handle this with aplomb.

Other deployer impact
---------------------

N/A

Developer impact
----------------

Developers of clients of Placement (e.g., nova-scheduler) will want to be aware
of the new syntax.

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

* Update the ``ResourceProviderList.get_all_by_filters`` and
  ``AllocationCandidates.get_by_requests`` methods to change the database
  queries to filter on "not this trait". This work can (and should) be done in
  a patchset separate and prior to the API changes.
* Update the placement API handlers for ``GET /resource_providers`` and ``GET
  /allocation_candidates`` in a new microversion to pass the negative traits to
  the methods changed in the steps above, including input validation
  adjustments.
* Add functional tests of the modified database queries.
* Add gabbi tests that express the new queries, both successful queries and
  those that should cause a 400 response.
* Release note for the API change.
* Update the microversion documents to indicate the new version.
* Update placement-api-ref to show the new query handling.


Dependencies
============

N/A


Testing
=======

There are two levels of testing required here:

* Functional tests to confirm that the database changes are correct.
* Gabbi tests to confirm that the API behaves.


Documentation Impact
====================

Three areas of documentation change:

* The `placement api-ref`_ will be updated to reflect the new syntax.
* `Microversion history`_ document will be updated.
* Release note added.

References
==========

* `placement api-ref`_


.. _placement api-ref: https://developer.openstack.org/api-ref/placement/
.. _microversion history: https://docs.openstack.org/nova/latest/user/placement.html#rest-api-version-history


History
=======

.. list-table:: Revisions
   :header-rows: 1

   * - Release Name
     - Description
   * - Rocky
     - Introduced
