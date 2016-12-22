..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

===============================
Nova Server Count API Extension
===============================

https://blueprints.launchpad.net/nova/+spec/server-count-api

This blueprint proposes a new REST API extension that returns the number of
servers that match the specified search criteria.


Problem description
===================

There is no current API that can retrieve summary count data for servers that
match a variety of search filters. For example, getting the total number of
servers in a given state.

Retrieving all servers and then manually determining the count data does not
scale because pagination queries must be implemented (see Alternatives section
for a detailed explanation).

The use cases that are driving this API extension are derived from a user's
experience in a GUI.

Use Case 1: A UI dashboard that contains servers in various states for a cloud
administrator. A new API extension is needed to retrieve the server count data
associated with various filters (ie, servers in active state, servers in
building state, servers in error state, etc.) for the entire cloud.

Assume that you have 5k instances in your cloud. The admin wants to see a
summary of instances in each state -- this API extension will help them
quickly determine if there is an issue that need attention; for example, if
there are many instances in 'error'. It is likely that once the admin sees
this count that they will then drill down into the data. However, without
this new API extension, the admin will not know if there are unacceptable
number of systems in a given state without drilling down into each set.

From a deployer's perspective, creating this dashboard with the existing APIs
is very painful since pagination is required (assume more then the default of
1k items). Also, processing time to get this data using the existing APIs
(even the non-detailed) is slow (and possibly inaccurate -- see #3) compared
to the processing time to get and return a single number.

Use Case 2: Showing filtered data in a table in the UI. Assume that the UI
supports tables that show filtered data (ie, table just showing instances in
'error' state) and uses pagination to get the data. Many users do not like
"infinite scrolling" where they have no idea how many items really are in the
list (more just show up as you scroll down or navigate to the next page).
Using this new count API, the UI table can indicate how many total items are
in the list (ie, showing 1-20 of 1000).

Assume that you have 500 instances in error state and that you can open a UI
table showing their details -- when creating the table, assume that the UI
uses a page size of 100 and assume that there is no dashboard showing the
'error' count. In this case, the admin logs into the UI and wants to know
how many servers are in error state. In order to do this, the admin navigates
to the 'servers in error state' table -- the UI only retrieves the first 100
items so it impossible to know if there are 101 total items or 500 total
items. As an admin, I would like to know what the total number of items in the
table is.

Use Case 3:  Inherent timing window when adding a new item with limit/marker
processing. Assume that you are using pagination to iterate over the data to
get a count. When you are getting page n, it is possible that page n-1 has a
new item x that was just added. Due to the sorting of the data, limit/marker
will not detect that this new item was added.

While this timing window is small, it does exist so getting an accurate count
using this method is not guaranteed to be accurate.

I realize that you can argue that the count API may not handle this UI use case
either. However, the count will always be accurate from the DB at the time that
the .count() function was processed -- the same claim cannot be made about
getting the count using limit/marker since multiple DB calls are being invoked
to calculate the number.


Proposed change
===============

The new count API extension must accept that same filter values as the
existing /servers and /servers/details APIs and re-use the existing filter
processing (once the common parts are refactored into utility methods that
can be utilized by both paths). Once the filters are processed to create the
query object, then the number of matching servers will be retrieved and
returned from the database.

The count API extension will be both per tenant and global (admin-only),
similar to the existing /servers APIs. An admin can supply the 'all_tenants'
parameter to signify that server count data should be retrieved globally.

This new flow requires new functions to retrieve the count value in the
compute API layer, in the instance layer, and in the database layers; all
functions return an integer value. The naming conventions for the functions
will follow the existing functions used for retrieving server instances, for
example:

* Compute API: get_count function

* Instance layer (InstanceList class): get_count_by_filters function

* DB layer: instance_count_by_filters function

* Sqlalchemy layer: instance_count_by_filters function

In the sqlalchemy DB layer, the filter processing (for processing exact name
filters, regex filters, and tag filters) needs to be moved into a common
function so that both the new count API extension and the existing get servers
APIs can utilize it. Once the query object is created, then the count()
function is invoked to retrieve the total number of matching servers for the
given query.

For the v2 API extension, the existing filtering pre-processing done in
nova.api.openstack.compute.servers.Controller._get_servers needs to be moved
into a static utility method so that the new count API extension can utilize
it; this is critical so that the filtering support for the count API matches
the filtering support for the /servers API.

For the v3 API, a new count function (similar to 'index' and 'detail') needs
to be added to nova.api.openstack.compute.plugins.v3.servers directly. Common
filter processing needs to broken out into utility functions (same idea as the
v2 API). For v3, the 'count' GET API can be registered with the Servers
extensions.V3APIExtensionBase directly.

Alternatives
------------

Other APIs exist that return count data (quotas and limit) but they do not
accept filter values.

A user could accomplish the same result (less the timing window noted in Use
Case #3) using the existing non-detailed /servers API with a filter and then
count up the results. However, the primary use case for this blueprint is
getting summary count data at scale.  For example, if the total cloud has 5k
VMs then doing paginated queries to iterate over the non-detailed '/servers'
API with a filter and limit/marker is really inefficient -- the API is going
to return more data then the user cares about (and do a lot of processing to
get it).  Assume that there are 2,500 instances in an active state; if the
non-detailed query (and the default limit of 1k) is used then the application
would have to make 3 separate REST API calls to get the all of the VMs and,
at the DB layer, the marker processing would be used to find the correct page
of data to return.  Since the user only cares about a summary count, then the
most efficient mechanism to retrieve that data would be a single DB query
using the count() function.

Note that the default maximum page set is set on the server (default of 1k);
therefore, a user MUST HANDLE pagination since the number of items being
queried may be greater then the default.

There are other options for how the v2 and v3 APIs can be registered. For v2,
the new count API could be registered by modifying the API routing in
nova.api.openstack.compute.__init__.APIRouter directly (to create the
/servers/count API just like /server/detail). Since v3 is still experimental,
this blueprint is proposing that the count API is baked into
nova.api.openstack.compute.plugins.v3.servers directly.

I cannot think of alternative implementations. The new API needs to utilitize
the existing filter processing as the current /servers APIs in order to ensure
consistency and prevent dual maintenance.

Data model impact
-----------------

None

REST API impact
---------------

The response for the existing /servers and /servers/detail REST APIs will
not be affected.

* New v2 API extension:

  * Name: ServerCounts
  * Alias: os-server-counts

* NEW v2 URL: v2/{tenant_id}/servers/count

* NEW v3 URL: v3/servers/count

* Description: Get number of servers

* Method type: GET

* Normal Response Codes: Same as the 'v2/{tenant_id}/servers/detail' API):

  * 200
  * 203

* Error Response Codes (same as the 'v2/{tenant_id}/servers/detail' API):

  * computeFault (400, 500, ...)
  * serviceUnavailable (503)
  * badRequest (400)
  * unauthorized (401)
  * forbidden (403)
  * badMethod (405)

* Parameters (same as the 'v2/{tenant_id}/servers' API except the 'limit' and
  'marker' parameters):

+---------------+-------+--------------+--------------------------------------+
| Parameter     | Style | Type         | Description                          |
+===============+=======+==============+======================================+
| all_tenants   | query | xsd:boolean  | Display server count information     |
| (optional)    |       |              | from all tenants (Admin only).       |
+---------------+-------+--------------+--------------------------------------+
| changes-since | query | xsd:dateTime | A time/date stamp for when the       |
| (optional)    |       |              | serverlast changed status.           |
+---------------+-------+--------------+--------------------------------------+
| image         | query | xsd:anyURI   | Name of the image in URL format.     |
| (optional)    |       |              |                                      |
+---------------+-------+--------------+--------------------------------------+
| flavor        | query | xsd:anyURI   | Name of the flavor in URL format.    |
| (optional)    |       |              |                                      |
+---------------+-------+--------------+--------------------------------------+
| name          | query | xsd:string   | Name of the server as a string.      |
| (optional)    |       |              |                                      |
+---------------+-------+--------------+--------------------------------------+
| status        | query | csapi:Server | Value of the status of the server so |
| (optional)    |       | Status       | that you can filter on "ACTIVE" for  |
|               |       |              | example.                             |
+---------------+-------+--------------+--------------------------------------+

  * JSON schema definition for the body data: N/A

  * JSON schema definition for the response data: {"count": <int>}

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

None -- This new API is not introducing any new DB joins that would affect
performance.

Other deployer impact
---------------------

None

Developer impact
----------------

None


Implementation
==============

Assignee(s)
-----------

Primary assignee:
  Steven Kaufer

Other contributors:
  <launchpad-id or None>

Work Items
----------

* Move filter processing code into utility functions at the API layer and at
  the DB sqlalchemy layer.
* Create new API functions in the various layers to get the count data.
* v2 API extension and v3 API updates to expose the new count API function.


Dependencies
============

Related (but independent) change being proposed in cinder:
https://blueprints.launchpad.net/cinder/+spec/volume-count-api


Testing
=======

Both unit and Tempest tests need to be created to ensure that the count data
is accurate for various filters.

Testing should be done against multiple backend database types.


Documentation Impact
====================

Document the new v2 API extension and v3 API updates (see "REST API impact"
section for details).


References
==========

None

