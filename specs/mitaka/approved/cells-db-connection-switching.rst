..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

=======================================
Database connection switching for cells
=======================================

https://blueprints.launchpad.net/nova/+spec/cells-db-connection-switching

In order for Nova API to perform queries on cell databases, the database
connection information for the target cell must be used. Nova API must
pass the cell database connection information to the DB API layer.


Problem description
===================

In Cells v2, instead of using a nova-cells proxy, nova-api will interact
directly with the database and message queue of the cell for an instance.
Instance -> cell mappings are stored in a table in the API level database.
Each InstanceMapping refers to a CellMapping, and the CellMapping contains
the connection information for the cell. We need a way to communicate the
database connection information from the CellMapping to the DB layer, so
when we update an instance, it will be updated in the cell database where
the instance's data resides.

Use Cases
----------

* Operators want to partition their deployments into cells for scaling, failure
  domain, and buildout reasons.  When partitioned, we need a way to route
  queries to the cell database for an instance.

Proposed change
===============

We propose to store the database connection information for a cell in the
RequestContext where it can be used by the DB API layer to interact with
the cell database. Currently, there are two databases that can be used at
the DB layer: 'main' and 'api' that are selected by the caller by method
name. We will want to consolidate the two methods into one that takes a
parameter to choose which EngineFacade to use. The field 'db_connection'
will be added to RequestContext to store the key to use for looking up the
EngineFacade.

When a request comes in, nova-api will look up the instance mapping in the
API database. It will get the database information from the instance's
CellMapping and store a key based on it in the RequestContext 'db_connection'
field. Then, the DB layer will look up the EngineFacade object for interacting
with the cell database using the 'db_connection' key stored in the
RequestContext.

Alternatives
------------

One alternative would be to add an argument to DB API methods to optionally
take database connection information to use instead of the configuration
setting and pass it when taking action on objects. This would require changing
the signatures of all the DB API methods to take the keyword argument or
otherwise finding a way to let all of the DB API methods derive from such an
interface. There is also precedent of allowing use of a field in the
RequestContext to communicate "read_deleted" to the DB API model_query.

Data model impact
-----------------

None

REST API impact
---------------

None

Security impact
---------------

The database connection field in the RequestContext could contain sensitive
data.

Notifications impact
--------------------

None

Other end user impact
---------------------

None

Performance Impact
------------------

This change on its own does not introduce a performance impact. The overall
design of keeping only mappings in the API DB and instance details in the
cell databases introduces an additional database lookup for the cell database
connection information. This can however be addressed by caching mappings.

Other deployer impact
---------------------

None

Developer impact
----------------

This change means that developers should be aware that cell database connection
information is contained in the RequestContext and be mindful that it could
contain sensitive data. Developers will need to use the interfaces for getting
database connection information from a CellMapping and setting it in a
RequestContext in order to interact query a cell database.

Implementation
==============

Assignee(s)
-----------

Primary assignee:
  melwitt

Other contributors:
  dheeraj-gupta4

Work Items
----------

* Add a database connection field to RequestContext

* Add a context manager to nova.context that populates a RequestContext with
  the database connection information given a CellMapping

* Modify nova.db.sqlalchemy.api get_session and get_engine to use the database
  connection information from the context, if it's set

Dependencies
============

* https://blueprints.launchpad.net/nova/+spec/cells-v2-mapping

* https://blueprints.launchpad.net/nova/+spec/cells-instance-mapping

Testing
=======

Since no user visible changes will occur with this change, the current suite of
Tempest or functional tests should be sufficient.

Documentation Impact
====================

Developer documentation could be written to describe how to use the new
interfaces.

References
==========

* https://etherpad.openstack.org/p/kilo-nova-cells
