..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

========================================================
Support to query nova resources filter by changes-before
========================================================

https://blueprints.launchpad.net/nova/+spec/support-to-query-nova-resources-filter-by-changes-before

The compute API already has the changes-since filter to filter servers updated
since the given time and this spec proposes to add a changes-before filter to
filter servers updated before the given time. In addition, the filters could
be used in conjunction to build a kind of time range filter, e.g. to get the
nova resources between changes-since and changes-before.

Problem description
===================
By default, nova can query the instance resource in the
updated_at >= changes-since time period. Users can only query resources
operated at given time, not during given period. Users may be interested in
resources operated in a specific period for monitoring or statistics purpose
but currently they have to retrieve and filter the resources by themselves.
This change can bring facility to users and also improve the efficiency of
timestamp based query.

Use Cases
---------
In large scale environment, lots of resources were created in system.
For tracing the change of resource, user or manage system only need to get
those resources which was changed with some time period, instead of querying
all resources every time to see which was changed.

For example, if you are trying to get the nova resources that were changed
before '2018-07-26T10:31:49Z', you can filter servers like:

* GET /servers/detail?changes-before=2018-07-26T10:31:49Z

Or if you want to filter servers in the time range(e.g. changes-since=
2018-07-26T10:31:49Z -> changes-before=2018-07-30T10:31:49Z), you can
filter servers like:

* GET /servers/detail?changes-since=2018-07-26T10:31:49Z&changes-before=
  2018-07-30T10:31:49Z

Proposed change
===============
Add a new microversion to os-instance-actions, os-migrations and servers
list APIs to support changes-before.

Introduce a new changes-before filter for retrieving resources. It accepts a
timestamp and projects will return resources whose updated_at fields are
earlier than this timestamp, it means that "updated_at <= changes-before".
Its(changes-before) value is optional. If changes-since and changes-before
pass the value, the projects will return resources whose updated_at fields
are earlier than or equal to this changes-before, and later than or equal
to changes-since.

**Reading deleted resources**

Like the ``changes-since`` filter, the ``changes-before`` filter will also
return deleted servers.

This spec does not propose to change any read-deleted behavior in the
os-instance-actions or os-migrations APIs. The os-instance-actions API
with the 2.21 microversion allows retrieving instance actions for a deleted
server resource. The os-migrations API takes an optional ``instance_uuid``
filter parameter but does not support returning deleted migration records like
``changes-since`` does in the servers API.

Alternatives
------------
As discussed in `Problem description`_ section, users can retrieve and then
filter resources by themselves, but this method is extremely inconvenient.
Having said that, services like Searchlight do exist which have similar
functionality, i.e. listening for nova notifications and storing them in
a time-series database like elasticsearch from which results can later be
queried. However, requiring Searchlight or a similar alternative solution for
this relatively small change is likely excessive.
Leaving filtering work to the database can utilize the optimization of database
engine and also reduce data transmitted from server to client.

Data model impact
-----------------
None

REST API impact
---------------
A new microversion will be added.

List API will accept new query string parameter changes-before.
Judging in the following cases:

* If the user specifies the changes-before < changes-since, it will
  return HTTPBadRequest 400.
* If the user only specifies changes-before, all nova resource before
  changes-before will be returned, including the deleted servers.
* If the user specifies changes-since and changes-before, that will
  get changes from a specific period, including the deleted servers.
* When the user only specifies changes-since, the original features
  remain unchanged.

Users can pass time to the list API url to retrieve resources operated since
a specific time.

* GET /servers?changes-before=2018-07-26T10:31:49Z
* GET /servers/detail?changes-before=2018-07-26T10:31:49Z
* GET /servers/{server_id}/os-instance-actions?changes-before=
  2018-07-26T10:31:49Z
* GET /os-migrations?changes-before=2018-07-26T10:31:49Z

Security impact
---------------
None

Notifications impact
--------------------
None

Other end user impact
---------------------
Python client may add help to inform users this new filter.
Add support for the changes-before filter in python-novaclient
for the 'nova list', 'nova migration-list' and
'nova instance-action-list' command.

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
  Brin Zhang

Work Items
----------
* Add querying support in sql
* Add API filter
* Add related test
* Add support for changes-before to the 'nova list' operation in novaclient
* Add support for changes-before to the 'nova instance-action-list'
  in novaclient
* Add support for changes-before to the 'nova migration-list' in novaclient

Dependencies
============
None

Testing
=======
* Add related unittest
* Add related functional test

Documentation Impact
====================
The nova API documentation will need to be updated to reflect the
REST API changes, and adding microversion instructions.

References
==========
None

History
=======
.. list-table:: Revisions
   :header-rows: 1

   * - Release Name
     - Description
   * - Stein
     - Introduced
