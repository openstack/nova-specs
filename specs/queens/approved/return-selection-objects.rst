..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

========================
Return Selection Objects
========================

https://blueprints.launchpad.net/nova/+spec/return-selection-objects

In Queens, we will be changing what we return from select_destinations() in
order to both provide additional 'alternate' hosts for each requested instance
and also the allocation_request for building on each host. Returning this as an
unstructured chunk of data will be fragile and potentially confusing. It would
be far better to create an object to hold this data and make it accessible in a
simpler and documented way.

Problem description
===================

Before Queens, the scheduler's select_destinations() method returned a list,
containing a dictionary representing the selected host for each requested
instance. In Queens, we need to return much more information to the caller of
select_destinations(). We could attempt to return a list of HostDicts, which
represents the selected host as in the past, along with zero or more
'alternate' hosts that are in the same cell and also meet the requested
resources. Additionally, each of these will also be accompanied by a dictionary
for the allocation_request required to claim that host. The end result will be
a list, with one item per requested instance. Each item in that list will be a
list of 2-tuples of (HostState, allocation_request). The HostState is a simple
dict, but the allocation_request is itself a complex nested dict.

The result of these changes would mean that the data returned would be a
complex nested combination of dictionaries, lists, and tuples. This data
structure would be both difficult to understand how to use correctly, and
confusing to developers looking at the code for the first time (or even after a
period of being away from it). It is also unversioned, meaning it is impossible
to track and respond to future changes in a reliable manner.

Use Cases
---------

As an experienced Nova developer, I would like to be able to write code that
uses the information returned from select_destinations() without having to
decipher a complex data structure.

As a newcomer to the Nova codebase, I would like to be able to read code that
is clear so that I can work with it quicker and with more confidence that my
changes won't break something.

Proposed change
===============

We propose to create a new Selection object that would contain the data that
represents a single destination: both the host information as well as the
corresponding allocation_request needed for claiming. The host information,
which is currently in a dictionary containing hostname, nodename, and limits
keys, will now be stored as simple object fields along with the
allocation_request. Additionally, the compute_node_uuid field will be added, as
it would be useful to have this available in some of our allocation cleanup
tasks.

There is no need for a corresponding SelectionList object, as there is no need
for DB creation or retrieval. The select_destinations() method will return
simple Python lists of Selection objects. The Scheduler will return one list
of Selection objects for each requested instance, representing the selected
host as well as any alternates.

Alternatives
------------

We could cache the allocation_request data in placement, and simply return a
key along with the resource providers. When a claim needs to be made, the key
would be POSTed instead of the full allocation_request data, and Placement
would use the cached data to carry out the claim. This has the advantage that
nothing on the Nova side of things ever uses the data in the
allocation_request; to Nova, it's an opaque blob. The downside, of course, is
that Placement would have to handle the cache.

We could return the full allocation_request data to the scheduler, and then
handle the caching and key management on the Nova side. When a claim/unclaim is
needed, the allocation_request would be retrieved from this cache and POSTed to
placement. This alternative doesn't require any changes to placement, but
requires that both the API-level cell and all local cells have access to some
form of 'global ram' cache that is accessible across cells.

We could just return an unstructured bunch of Python data, and add a ton of
comments everywhere it is used in the hope that anyone looking at the code
would understand what each bit represents, and that every future change to the
data required would be able to be handled without versioning.

Data model impact
-----------------

There will be no changes to any database schemas, but this will introduce a new
versioned object. This object will contain the following fields, along with
their types::

 * compute_node_uuid: fields.UUIDField
 * service_host: fields.StringField
 * nodename: fields.StringField
 * cell_uuid: fields.UUIDField
 * numa_limits: fields.ObjectField("NUMATopologyLimits")
 * allocation_request: fields.StringField

There isn't a good field type for the allocation_request value, as it is a
complex nested structure, so instead we'll store it as its JSON respresentation
in a StringField. The structure of an allocation_request, as described in this
spec[2], looks like::

    "allocations": [
        {
            "resource_provider": {
                "uuid": $COMPUTE_NODE1_UUID
            },
            "resources": {
                "VCPU": $AMOUNT_REQUESTED_VCPU,
                "MEMORY_MB": $AMOUNT_REQUESTED_MEMORY_MB
            }
        },
        {
            "resource_provider": {
                "uuid": $SHARED_STORAGE_UUID
            },
            "resources": {
                "DISK_GB": $AMOUNT_REQUESTED_DISK_GB
            }
        },
    ]

REST API impact
---------------

None

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

It will make life a little easier for anyone working with the Nova codebase by
not making them decipher complex data structures, but other than that, none.


Implementation
==============

Assignee(s)
-----------

Primary assignee:
  ed-leafe

Other contributors:
  None

Work Items
----------

* Create the Selection object.

* Modify the scheduler's select_destinations() method to populate these objects
  with the selected host info and return them.

Dependencies
============

None


Testing
=======

This is one part of the overall sweeping changes being made in Queens, and all
of it will have to be tested. The Selection object will need some basic tests,
but the bulk of the testing will be in the conductor to verify that it is
working with Selection objects for host selection, resource claiming, and
retries on build failures.


Documentation Impact
====================

The developer reference docs will need to be updated to document this new
object. The docs for the scheduler workflow will also need to be updated to
reflect these changes.

References
==========

The initial problem was documented in a blog post[0], and was then discussed at
the Nova Scheduler subteam meeting[1], where this approach was agreed upon.

[0] https://blog.leafe.com/handling-unstructured-data/
[1] http://eavesdrop.openstack.org/meetings/nova_scheduler/2017/nova_scheduler.2017-08-28-14.00.log.html#l-140
[2] https://specs.openstack.org/openstack/nova-specs/specs/pike/approved/placement-allocation-requests.html

History
=======

.. list-table:: Revisions
   :header-rows: 1

   * - Release Name
     - Description
   * - Queens
     - Introduced
