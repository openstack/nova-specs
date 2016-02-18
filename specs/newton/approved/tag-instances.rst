..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

========================================
Allow simple string tagging of instances
========================================

https://blueprints.launchpad.net/nova/+spec/tag-instances

This blueprint aims to add support for a simple string tagging mechanism
for the instance object in the Nova domain model.

Problem description
===================

In most popular REST API interfaces, objects in the domain model can be
"tagged" with zero or more simple strings. These strings may then be used
to group and categorize objects in the domain model.

In order to align Nova's REST API with the Internet's common understanding
of `resource tagging`_, we can add a API microversion that allows normal users
to add, remove and list tags for an instance.

.. _resource tagging: http://en.wikipedia.org/wiki/Tag_(metadata)

Use Cases
---------

A typical end-user would like to attach a set of strings to an instance. The
user does not wish to use key/value pairs to tag the instance with some
simple strings.


Proposed change
===============

No changes to existing metadata, system_metadata or extra_specs functionality
are being proposed. This is *specifically* for adding a new API for *normal
users* to be able to tag their instances with simple strings.

Add a API microversion that allows a user to add, remove, and list tags
for an instance.

Add a API microversion to allow searching for instances based on one
or more string tags.

Alternatives
------------

Alternatives to simple string tagging are already available in Nova through the
instance metadata key/value pairs API extension. But it's not quite right to
use metadata for tagging. Tags are often confused with metadata. While the two
have an intersection, the main function of tags is to classify a collection of
entities in groups, while metadata is used to attach additional information to
entities.

Data model impact
-----------------

The `nova.objects.instance.Instance` object would have a new `tags` field
of type `nova.objects.fields.ListOfStrings` that would be populated on-demand
(i.e. lazy-loaded).

A tag shall be defined as a Unicode bytestring no longer than 60 bytes in
length.

The tag is an opaque string and is not intended to be interpreted or even
read by the virt drivers. In the REST API changes below, non-URL-safe
characters in tags will need to be urlencoded if referred in the URI (for
example, doing a DELETE /servers/{server}/tags/{tag}, the {tag} would need
to be urlencoded.

Also according to tagging guidelines [3] tag names have the following
restrictions:

* Tags are case sensitive.
* '/' is **not** allowed to be in a tag name
* Comma is **not** allowed to be in a tag name in order to simplify requests
  that specify lists of tags
* All other characters are allowed to be in a tag name

.. note::

    The '/' character is forbidden because some servers have a problem with
    encoding this character. The problem is that the server will handle '%2F'
    as '/' even though '/' is encoded. It's a problem of poor server
    implementation. To avoid problems with handling URLs character '/' is
    forbidden in tag names.

For the database schema, the following table constructs would suffice ::

    CREATE TABLE tags (
        resource_id CHAR(32) NOT NULL PRIMARY KEY,
        tag VARCHAR(60) NOT NULL CHARACTER SET utf8
         COLLATION utf8_ci PRIMARY KEY,
        CONSTRAINT resource_tag_constraint UNIQUE (resource_id, tag),
        deleted_at DATETIME,
        deleted INT DEFAULT 0
    );

There shall be a new hard-coded limit of 50 for the number of tags a user can
use on a server. No need to make this configurable or use the quota system at
this point.

REST API impact
---------------

This proposal would add a API microversion for retrieving and setting tags
against an instance. In addition, it would add a API microversion to allow
the searching/listing of instances based on one or more string tags.

The tag CRUD operations API microversion would look like the following:

A list of tags for the specified server returns with the server details
information ::

    GET /servers/{server_id}

Response ::

    {
        'id': {server_id},

        ... other server resource properties ...

        'tags': ['foo', 'bar', 'baz']
    }

A servers list detail request returns details information about each server,
including a list of tags for each server ::

    GET /servers/detail

Response ::

    {
        'servers': [
            {
                'id': {server1_id},

                ... other server resource properties ...

                'tags': ['foo', 'bar', 'baz']
            },
            {
                'id': {server2_id},

                ... other server resource properties ...

                'tags': ['one', 'two']
            }
    }

Get **only** a list of tags for the specified server ::

    GET /servers/{server_id}/tags

Response ::

    {
        'tags': ['foo', 'bar', 'baz']
    }

Replace set of tags on a server ::

    PUT /servers/{server_id}/tags

with request payload ::

    {
        'tags': ['foo', 'bar', 'baz']
    }

Response ::

    {
        'tags': ['foo', 'bar', 'baz']
    }

If the number of tags exceeds the limit of tags per server, shall return
a `400 Bad Request`

Add a single tag on a server ::

    PUT /servers/{server_id}/tags/{tag}

Returns `201 Created`.

If the tag already exists, no error is raised, it just returns the
`204 No Content`

If the number of tags would exceed the per-server limit, shall return a
`400 Bad Request`

Check if a tag exists or not on a server ::

    GET /servers/{server_id}/tags/{tag}

Returns `204 No Content` if tag exist on a server.

Returns `404 Not Found` if tag doesn't exist on a server.

Remove a single tag on a server ::

    DELETE /servers/{server_id}/tags/{tag}

Returns `204 No Content` upon success. Returns a `404 Not Found` if you
attempt to delete a tag that does not exist.

Remove all tags on a server ::

    DELETE /servers/{server_id}/tags

Returns `204 No Content`.

The API microversion that would allow searching/filtering of the `GET /servers`
REST API call would add the following query parameters:

* `tags`
* `tags-any`
* `not-tags`
* `not-tags-any`

To request the list of servers that have a single tag, ``tags`` argument
should be set to the desired tag name. Example::

    GET /servers?tags=red

To request the list of servers that have two or more tags, the ``tags``
argument should be set to the list of tags, separated by commas. In this
situation the tags given must all be present for a server to be included in
the query result. Example that returns servers that have the "red" and "blue"
tags::

    GET /servers?tags=red,blue

To request the list of servers that have one or more of a list of given tags,
the ``tags-any`` argument should be set to the list of tags, separated by
commas. In this situation as long as one of the given tags is present the
server will be included in the query result. Example that returns the servers
that have the "red" or the "blue" tag::

    GET /servers?tags-any=red,blue

To request the list of servers that do not have one or more tags, the
``not-tags`` argument should be set to the list of tags, separated by commas.
In this situation only the servers that do not have any of the given tags will
be included in the query results. Example that returns the servers that do not
have the "red" nor the "blue" tag::

    GET /servers?not-tags=red,blue

To request the list of servers that do not have at least one of a list of
tags, the ``not-tags-any`` argument should be set to the list of tags,
separated by commas. In this situation only the servers that do not have at
least one of the given tags will be included in the query result. Example that
returns the servers that do not have the "red" tag, or do not have the "blue"
tag::

    GET /servers?not-tags-any=red,blue

The ``tags``, ``tags-any``, ``not-tags`` and ``not-tags-any`` arguments can be
combined to build more complex queries. Example::

    GET /servers?tags=red,blue&tags-any=green,orange

The above example returns any servers that have the "red" and "blue" tags, plus
at least one of "green" and "orange".

Complex queries may have contradictory parameters. Example::

    GET /servers?tags=blue&not-tags=blue

In this case we should let Nova find these servers. Obviously there are no such
servers and Nova will return an empty list.

No change is needed to the JSON response for the `GET /servers/` call.


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

None, though REGEXP-based querying on some fields might be modified to
use a faster tag-list filtering query.

Other deployer impact
---------------------

None

Developer impact
----------------

None

Implementation
==============

See `Work Items`_ section below.

Assignee(s)
-----------

Primary assignee:
  snikitin

Other contributors:
  jaypipes

Work Items
----------

Changes would be made, in order, to:

1. the database API layer to add support for CRUD operations on instance tags
   (Done)
2. the database API layer to add tag-list filtering support to
   `instance_get_all_by_filters` (Done for 'tags' and 'tags-any' filters)
3. the nova.objects layer to add support for a tags field of the Instance
   object (Done)
4. the API microversion for CRUD operations on the tag list

Dependencies
============

None.

Testing
=======

Would need new Tempest and unit tests.

Documentation Impact
====================

Docs needed for new API microversion and usage.

References
==========

Mailing list discussions:

[1] http://lists.openstack.org/pipermail/openstack-dev/2014-April/033222.html
[2] http://lists.openstack.org/pipermail/openstack-dev/2014-April/034004.html

Tagging guidelines:

[3] http://specs.openstack.org/openstack/api-wg/guidelines/tags.html

History
=======

Optional section for Mitaka intended to be used each time the spec
is updated to describe new design, API or any database schema
updated. Useful to let reader understand what's happened along the
time.

.. list-table:: Revisions
   :header-rows: 1

   * - Release Name
     - Description
   * - Juno
     - Introduced
   * - Kilo
     - Implementation
   * - Liberty
     - Implementation
   * - Mitaka
     - Implementation
   * - Newton
     - Implementation
