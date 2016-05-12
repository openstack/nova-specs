..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

============================================
Message queue connection switching for cells
============================================

https://blueprints.launchpad.net/nova/+spec/cells-mq-connection-switching

In order for Nova API to send RPC messages to cells, the message queue
connection information for the target cell must be used. Nova API must
pass the cell message queue information to the RPC API layer.


Problem description
===================

In Cells v2, instead of using a nova-cells proxy, nova-api will interact
directly with the database and message queue of the cell for an instance.
Instance -> cell mappings are stored in a table in the API level database.
Each InstanceMapping refers to a CellMapping, and the CellMapping contains
the connection information for the cell. We need a way to communicate the
message queue connection information from the CellMapping to the RPC API
layer, so when we receive a request to act upon an instance, the message
will be forwarded to the cell where the instance resides.

Use Cases
---------

* Operators want to partition their deployments into cells for scaling, failure
  domain, and buildout reasons.  When partitioned, we need a way to route
  messages to the cell for an instance.

Proposed change
===============

We propose to store the message queue connection information for a cell in
the RequestContext where it can be used by the RPC API layer to interact with
the cell message queue. Currently, there is only one message queue that can be
used at the RPC API layer and it is a global transport. We will want to be able
to create a transport dynamically based on message queue connection data if it
is present in the RequestContext. The field 'mq_connection' will be added to
RequestContext to store the transport object for the cell message queue.

When a request comes in, nova-api will look up the instance mapping in the
API database. It will get the message queue information from the instance's
CellMapping and store a transport object in the RequestContext 'mq_connection'
field. Then, the RPC API layer will use the transport object for interacting
with the cell message queue using the 'mq_connection' to forward the message.

Alternatives
------------

One alternative would be to add an argument to RPC API methods to optionally
take message queue connection information to use instead of the configuration
setting and pass it when making calls destined for another message queue. This
would require changing the signatures of all the RPC API methods to take the
keyword argument or otherwise finding a way to let the relevant RPC API methods
derive from such an interface. There is also precedent of allowing use of a
field in the RequestContext to communicate "db_connection" to DB API methods
and "read_deleted" to the DB API model_query.

Data model impact
-----------------

None

REST API impact
---------------

None

Security impact
---------------

The message queue connection field in the RequestContext could contain
sensitive data.

Notifications impact
--------------------

None

Other end user impact
---------------------

None

Performance Impact
------------------

This change will create RPC transport objects dynamically based on connection
information from the RequestContext. There is some overhead to this over the
global transport object usually used for a single message queue. The overhead*
is the same as in Cells v1 as both Transport objects and RPCClient objects
are created dynamically for each message sent to a cell. There is the
possibility of caching objects keyed off of hashes of 'mq_connection' along
with an expiration scheme if overhead becomes problematic.

* Creation of Transport objects involves creating the backend driver object
  and connection pool, so creating them dynamically for each message doesn't
  take advantage of connection pooling, a new connection to the broker will
  be made each time.

Other deployer impact
---------------------

None

Developer impact
----------------

This change means that developers should be aware that cell message queue
connection information is contained in the RequestContext and be mindful that
it could contain sensitive data. Developers will need to use the interfaces
for getting message queue connection information from a CellMapping and setting
it in a RequestContext in order to interact with a cell message queue.

Implementation
==============

Assignee(s)
-----------

Primary assignee:
  melwitt

Other contributors:
  None

Work Items
----------

* Add a message queue connection field to RequestContext

* Add message queue connection to the context manager in nova.context that
  populates a RequestContext with cell connection information given a
  CellMapping

* Modify RPC layer and compute RPC API functions to use the message queue
  connection information from the context, if it's set

Dependencies
============

* https://blueprints.launchpad.net/nova/+spec/cells-v2-mapping

* https://blueprints.launchpad.net/nova/+spec/cells-instance-mapping

Testing
=======

Cells v2 testing improvements will include scenarios with multiple cells
and upgrading with multiple cells. That is, however, out of scope for the work
described in this spec and a new functional test exercising message queue
switching combined with the current suite of Tempest and functional tests
should be sufficient.

Documentation Impact
====================

Developer documentation could be written to describe how to use the new
interfaces.

References
==========

* https://review.openstack.org/#/c/274955/

History
=======

.. list-table:: Revisions
   :header-rows: 1

   * - Newton
     - Introduced
