..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

====================================
Nova REST API Sorting Enhancements
====================================

https://blueprints.launchpad.net/nova/+spec/nova-pagination

Currently, the pagination support for Nova does not allow the caller to
specify the sort order and direction of the data set. This blueprint
enhances the pagination support for the /servers and /servers/detail
APIs so that multiple sort keys and sort directions can be supplied on
the request.


Problem description
===================

There is no support for retrieving server data in a specific order, it is
defaulted to descending sort order by the "created date" and "id" keys. In
order to retrieve data in any sort order and direction, the REST APIs need
to accept multiple sort keys and directions.

Use Cases
---------

A UI that displays a table with only the page of data that it has retrieved
from the server. The items in this table need to be sorted by status first
and by display name second. In order to retrieve data in this order, the
APIs must accept multiple sort keys/directions.

Project Priority
-----------------

There are no set priorities right now but this would fall under user
experience because it allows data to be retrieved in a custom sort order.

Proposed change
===============

The /servers and /servers/detail APIs will support the following parameters
being repeated on the request:

* sort_key: Key used to determine sort order
* sort_dir: Direction for with the associated sort key ("asc" or "desc")

The caller can specify these parameters multiple times in order to generate
a list of sort keys and sort directions. The first key listed is the primary
key, the next key is the secondary key, etc.

For example: /servers?sort_key=status&sort_dir=desc&sort_key=display_name&
&sort_dir=desc&sort_key=created_at&sort_dir=desc

Note: The "created_at" and "id" sort keys are always appended at the end of
the key list if they are not already specified on the request.

The database layer already supports multiple sort keys and directions. This
blueprint will update the API layer to retrieve the sort information from
the API request and pass that information down to the database layer.

All sorting is handled in the sqlalchemy.utils.paginate_query function.  This
function accepts an ORM model class as an argument and the only valid sort
keys are attributes on the given model class.  Therefore, the valid sort
keys are limited to the model attributes on the models.Instance class.

For the v2 API a new 'os-server-sort-keys' API extension will be created to
signify that the new sorting parameters proposed in this blueprint should be
honored. The v3 API will support the new sorting parameters by default.

Alternatives
------------

Repeating parameter key/values was chosen because glance already did it:

https://github.com/openstack/glance/blob/master/glance/api/v2/images.py#L526

However, the list of sort keys and directions could be built by splitting the
associated parameter values.

For example:
/servers?sort_key=status,display_name,created_at&sort_dir=desc,desc,desc

The downside of this approach is that it would require pre-defined token
characters. I'm open to this solution if it is deemed better.

Data model impact
-----------------

None

REST API impact
---------------

A new v2 API extension will be created to signify that the new sorting
parameters should be honored. Extension details:

* Name: ServerSortKeys
* Alias: os-server-sort-keys

Note that this API extension will behave in the same manner as the current
'os-user-data' extension. For example, the extension is defined as:

http://git.openstack.org/cgit/openstack/nova/tree/nova/api/openstack/compute
/contrib/user_data.py

And it is checked in the v2 server API here:

http://git.openstack.org/cgit/openstack/nova/tree/nova/api/openstack/compute/
servers.py#n850

The following existing v2 GET APIs will support the new sorting parameters
if the 'os-server-sort-keys' API extenstion is loaded:

* /v2/{tenant_id}/servers
* /v2/{tenant_id}/servers/detail

The following existing v3 GET APIs will support the new sorting parameters
by default:

* /v3/servers
* /v3/servers/details

Note that the design described in this blueprint could be applied to other GET
REST APIs but this blueprint is scoped to only those listed above. Once this
design is finalized, then the same approach could be applied to other APIs.

The existing API documentation needs to be updated to include the following
new Request Parameters:

+-----------+-------+--------+---------------------------------------------+
| Parameter | Style | Type   | Description                                 |
+===========+=======+========+=============================================+
| sort_key  | query | string | Sort key (repeated for multiple), keys      |
|           |       |        | default to 'created_at' and 'id'            |
+-----------+-------+--------+---------------------------------------------+
| sort_dir  | query | string | Sort direction, either 'asc' or 'desc'      |
|           |       |        | (repeated for multiple), defaults to 'desc' |
+-----------+-------+--------+---------------------------------------------+

Neither the API response format nor the return codes will be modified, only
the order of the servers that are returned.

In the event that an invalid sort key is specifed then a "badRequest" error
response (code 400) will be returned with a message like "Invalid input
received: Invalid sort key".

Security impact
---------------

None

Notifications impact
--------------------

None

Other end user impact
---------------------

The novaclient should be updated to accept sort keys and sort directions, new
parameters:

+-------------+----------------------------------------------------------+
| Parameter   | Description                                              |
+=============+==========================================================+
| --sort-keys | Comma-separated list of sort keys used to specify server |
|             | ordering. Each key must be paired with a sort direction  |
|             | value.                                                   |
+-------------+----------------------------------------------------------+
| --sort-dirs | Comma-separated list of sort directions used to specify  |
|             | server ordering. Each key Must be paired with a sort key |
|             | value. Valid values are 'asc' and 'desc'.                |
+-------------+----------------------------------------------------------+

Performance Impact
------------------

All sorting will be done in the database. The choice of sort keys is limited
to attributes on the models.Instance ORM class -- not every attribute key
returned from a detailed query is a valid sort key.

Performance data was gathered by running on a simple devstack VM with 2GB
memory. 5000 instances were inserted into the DB. The data shows that the
sort time on the main data table is dwarfed (see first table below) when
running a detailed query -- most of the time is spent querying the other
tables for each item; therefore, the impact of the sort key on a detailed
query is minimal.

For example, the data below compares the processing time of a GET request for
a non-detailed query to a detailed query with various limits using the default
sort keys. The purpose of this table is to show the processing time for a
detailed query is dominated by getting the additional details for each item.

+-------+--------------------+----------------+---------------------------+
| Limit | Non-Detailed (sec) | Detailed (sec) | Non-Detailed / Detailed % |
+=======+====================+================+===========================+
| 50    | 0.0560             | 0.8621         | 6.5%                      |
+-------+--------------------+----------------+---------------------------+
| 100   | 0.0813             | 1.6839         | 4.8%                      |
+-------+--------------------+----------------+---------------------------+
| 150   | 0.0848             | 2.4705         | 3.4%                      |
+-------+--------------------+----------------+---------------------------+
| 200   | 0.0874             | 3.2502         | 2.7%                      |
+-------+--------------------+----------------+---------------------------+
| 250   | 0.0985             | 4.1237         | 2.4%                      |
+-------+--------------------+----------------+---------------------------+
| 300   | 0.1229             | 4.8731         | 2.5%                      |
+-------+--------------------+----------------+---------------------------+
| 350   | 0.1262             | 5.6366         | 2.2%                      |
+-------+--------------------+----------------+---------------------------+
| 400   | 0.1282             | 6.5573         | 2.0%                      |
+-------+--------------------+----------------+---------------------------+
| 450   | 0.1458             | 7.2921         | 2.0%                      |
+-------+--------------------+----------------+---------------------------+
| 500   | 0.1770             | 8.1126         | 2.2%                      |
+-------+--------------------+----------------+---------------------------+
| 1000  | 0.2589             | 16.0844        | 1.6%                      |
+-------+--------------------+----------------+---------------------------+

Non-detailed query data was also gathered. The table below compares the
processing time using default sort keys to the processing using display_name
as the sort key. Items were added with a 40 character display_name that was
generated in an out-of-alphabetical sort order.

+-------+--------------------+------------------------+------------+
| Limit | Default keys (sec) | display_name key (sec) | Slowdown % |
+=======+====================+========================+============+
| 50    | 0.0560             | 0.0600                 | 7.1%       |
+-------+--------------------+------------------------+------------+
| 100   | 0.0813             | 0.0832                 | 2.3%       |
+-------+--------------------+------------------------+------------+
| 150   | 0.0848             | 0.0879                 | 3.7%       |
+-------+--------------------+------------------------+------------+
| 200   | 0.0874             | 0.0906                 | 3.7%       |
+-------+--------------------+------------------------+------------+
| 250   | 0.0985             | 0.1031                 | 4.7%       |
+-------+--------------------+------------------------+------------+
| 300   | 0.1229             | 0.1198                 | -2.5%      |
+-------+--------------------+------------------------+------------+
| 350   | 0.1262             | 0.1319                 | 4.5%       |
+-------+--------------------+------------------------+------------+
| 400   | 0.1282             | 0.1368                 | 6.7%       |
+-------+--------------------+------------------------+------------+
| 450   | 0.1458             | 0.1458                 | 0.0%       |
+-------+--------------------+------------------------+------------+
| 500   | 0.1770             | 0.1619                 | -8.5%      |
+-------+--------------------+------------------------+------------+
| 1000  | 0.2589             | 0.2659                 | 2.7%       |
+-------+--------------------+------------------------+------------+

In conclusion, the sort processing on the main data table has minimal impact
on the overall processing time. For a detailed query, the sort time is dwarfed
by other processing -- even if the sort time when up 3x it would only
represent 4.8% of the total processing time for a detailed query with a limit
of 1000 (and only increase the processing time by .11 sec with a limit of 50).

Other deployer impact
---------------------

The choice of sort keys has a minimal impact on data retrieval performance
(see performance data above). Therefore, the user should be allowed to
retrieve data in whatever order they need to for creating their views (see
use case in the Problem Description).

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
  None

Work Items
----------

Ideally the logic for processing the sort parameters would be common to all
components and would be done in oslo; a similar blueprint is also being
proposed in cinder:
https://blueprints.launchpad.net/cinder/+spec/cinder-pagination

Therefore, I see the following work items:

* Create common functions to process the API parameters and create a list of
  sort keys and directions
* Update v2 and v3 APIs to retrieve the sort information and pass down to the
  DB layer (requires changes to compute/api.py, objects/instance.py,
  db/api.py, and db\sqlalchemy\api.py)
* Update the novaclient to accept and process multiple sort keys and sort
  directions


Dependencies
============

* Related (but independent) change being proposed in cinder:
  https://blueprints.launchpad.net/cinder/+spec/cinder-pagination


Testing
=======

Both unit and Tempest tests need to be created to ensure that the data is
retrieved in the specified sort order. Tests should also verify that the
default sort keys ("created_at" and "id") are always appended to the user
supplied keys (if the user did not already specify them).

Testing should be done against multiple backend database types.


Documentation Impact
====================

The /servers and /servers/detail API documentation will need to be updated to:

- Reflect the new sorting parameters and explain that these parameters will
  affect the order in which the data is returned.
- Explain how the default sort keys will always be added at the end of the
  sort key list

The documentation could also note that query performance will be affected by
the choice of the sort key, noting which keys are indexed.


References
==========

None

