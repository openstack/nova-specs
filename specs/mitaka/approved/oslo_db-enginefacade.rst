..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

=====================================
Use the new enginefacade from oslo_db
=====================================

https://blueprints.launchpad.net/nova/+spec/new-oslodb-enginefacade

Implement the new oslo.db enginefacade interface described here:

https://blueprints.launchpad.net/oslo.db/+spec/make-enginefacade-a-facade


Problem description
===================

The linked oslo.db spec contains the details of the proposal, including its
general advantages to all projects. In summary, we transparently track database
transactions using the RequestContext object. This means that if there is
already a transaction in progress we will use it by default, only creating a
separate transaction if explicitly requested.


Use Cases
----------

These changes will only affect developers.

* Allow a class of database races to be fixed

Nova currently only exposes database transactions in nova/db/sqlalchemy/api.py,
which means that every db api call is in its own transaction.  Although this
will remain the same initially, the new interface allows a caller to extend a
transaction across several db api calls if they wish. This will enable callers
who need these to be atomic to achieve this, which includes the save operation
on several Nova objects.

* Reduce connection load on the database

Many database api calls currently create several separate database connections,
which increases load on the database. By reducing these to a single connection,
load on the db will be decreased.

* Improve atomicity of API calls

By ensuring that database api calls use a single transaction, we fix a class of
bug where failure can leave a partial result.

* Make greater use of slave databases for read-only transactions

The new api marks sections of code as either readers or writers, and enforces
this separation. This allows us to automatically use a slave database
connection for all read-only transactions. It is currently only used when
explicitly requested in code.


Proposed change
===============

Code changes
------------

* Decorate the RequestContext class

nova.RequestContext is annotated with the
@enginefacade.transaction_context_provider decorator. This adds several code
hooks which provide access to the transaction context via the RequestContext
object.

* Update database apis incrementally

Database apis will be updated in batches, by function. For example, Service
apis, quota apis, instance apis. Invidual calls will be annotated as either
readers or writers. Existing transaction management will be replaced. Calls
into apis which have not been upgraded yet will continue to explicitly pass the
session or connection object.

* Remove uses of use_slave wherever possible

The use_slave parameter will be removed from all upgraded database apis, which
will involve updating call sites and tests. Where the caller no longer uses the
use_slave parameter anywhere, the removal will be propagated as far as
possible.  The exception will be external interfaces. All uses of use_slave
will be removed. External interfaces will continue to accept it, but will not
use it.

* Cells 'api' database calls

get_api_engine() and get_api_session() will be replaced by a context manager
which changes the current transaction manager.

Alternatives
------------

Alternatives were examined during the design of the oslo.db code. The goal of
this change is to implement a solution which is common across OpenStack
projects.

Data model impact
-----------------

None.

REST API impact
---------------

None.

This change obsoletes the use_slave parameter everywhere it is used, which
includes several apis with external interfaces. We remove it from all internal
interfaces. For external interfaces we leave it in place, but ignore it. Slave
connections will be used everywhere automatically, whenever possible

Security impact
---------------

Nothing obvious.

Notifications impact
--------------------

None.

Other end user impact
---------------------

None.

Performance Impact
------------------

By reducing connection load on the database, the change is expected to provide
a small performance improvement. However, the primary purpose is correctness.

Other deployer impact
---------------------

None.

Developer impact
----------------

The initial phase of this work will be to implement the new engine facade in
nova/db/sqlalchemy/api.py only, and the couple of cells callers which access
the database outside this module. There will be some minor changes to function
signatures in this module due to removing use_slave, but all callers will be
updated as part of this work. Callers will not have to consider transaction
context if they do not currently do so, as it will be created and destroyed
automatically.

This change will allow developers to explicitly extend database transaction
context to cover several database calls. This allows the caller to make
multiple database changes atomically.


Implementation
==============

Assignee(s)
-----------

Primary assignee:
  mbooth-9

Work Items
----------

* Enable use of the new api in Nova

* Migrate api bundles along functional lines:
    * Service
    * ComputeNode
    * Certificate
    * FloatingIP
    * DNSDomain
    * FixedIP
    * VIF
    * Instance, InstanceInfoCache, InstanceExtra, InstanceMetadata,
      InstanceSystemMetadata, InstanceFault, InstanceGroup, InstanceTag
    * KeyPair
    * Network
    * Quota
    * EC2
    * BDM
    * SecurityGroup
    * ProviderFWRule
    * Migration
    * ConsolePool
    * Flavor
    * Cells
    * Agent
    * Bandwidth
    * Volume
    * S3
    * Aggregate
    * Action
    * Task
    * PCIDevice


Dependencies
============

A version of oslo.db including the new enginefacade api:

https://review.openstack.org/#/c/138215/


Testing
=======

This change is intended to have no immediate functional impact. The current
tests should continue to pass, except where:

* An internal API is modified to remove use_slave
* The change exposes a bug
* The tests assumed implementation details which have changed


Documentation Impact
====================

None.


References
==========

https://blueprints.launchpad.net/oslo.db/+spec/make-enginefacade-a-facade
