..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

================================
Detach Service from Compute_Node
================================

https://blueprints.launchpad.net/nova/+spec/detach-service-from-computenode

Remove the nested dependency in between Service and ComputeNode

Problem description
===================

There is no good reason to keep a dependency in between a service, which is the
representation of the message bus and a compute_node, which is a collection of
resources for the solely use of the scheduler. The fact that they are related
to each other means that the resource tracker ends up needing to "find" its
compute node record by first looking up the service record for the 'compute'
topic and the host for the resource tracker, and then grabs the first
compute_node record that is related to the service record that matches that
query. There is no reason to do this in the resource tracker other than the
fact that right now the compute_nodes table has a service_id field and a
relation to the services table.

It also carries a dependency on the compute_nodes table as there is a foreign
key on a separate table for something totally unrelated to the Scheduler, which
prevents the Scheduler to be split unless we continue to carry that
relationship.


Use Cases
---------

This is a refactoring effort helping out to split the scheduler by reducing the
dependencies it has to manage.


Project Priority
----------------

This blueprint is part of the 'scheduler' refactoring effort, defined as a 3rd
priority for the Kilo release.


Proposed change
===============

Instead of having a relationship using a foreign key, the proposal will consist
of adding a new field called 'host' for compute_nodes and a unique constraint
on (host, hypervisor_hostname). Also, service_id field will be marked as
deprecated and not updated in the compute_nodes table and ComputeNode object
field service_id will be left unset. SQLA relationship on service will be
deleted and Service object will keep a compute_node field but will actually not
use this relationship.

Implementation proposal can be found in the patch series [1].

Alternatives
------------

Only change DB API to remove the relationship without changing callers but
it would create some confusion and obfuscate the need of modifying accessors.

Data model impact
-----------------

Most of the change is about changing the model, but let's rephrase it.
compute_nodes.service relationship will be deleted, compute_nodes.service_id
will be marked as deprecated and not updated by Kilo compute nodes and
compute_nodes.host will be added as a String (identical to Service.host field).

As it was agreed during Summit, no data migrations will happen for updating
either when creating the host column (for populating its values) or when
downgrading by repopulating service_id.

Instead, data migration (here service_id to host) will be managed at the Object
level (here ComputeNode) each time a save operation will happen by querying
Service object to get the host value and set service_id to NULL.

There is no sense to keep a specific ID while the tuple (host, node) is
identified as the source of truth for idenfifying compute nodes.

ComputeNode object will still continue to have a service field but it will
no longer use the relationship to get that info. In parallel, Service object
will continue to have a nested ComputeNode object for backwards compatibility
but won't also use the relationship to get that object.


REST API impact
---------------

In order to preserve API stability, we will still provide service information
when querying compute nodes but this extra information will be on a
case-by-case basis thanks to an extra flag passed to the DB API asking to join
service and compute_nodes tables on service.host == compute_nodes.host.
We expect no performance penalty as it is already done this way in
db.compute_node_get_all() with an INTEGER matching instead of a VARCHAR(255).

No changes in the API model.

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

An external tool could be provided for migrating offline existing compute nodes
which don't yet have the host field set.


Developer impact
----------------

None

Implementation
==============

Assignee(s)
-----------

Primary assignee:
    sbauza

Other contributors:
    None

Work Items
----------

Code was already posted as a patch series [1] :

* Add host field to compute_nodes table
* Add extra methods for querying this new field
* Use these extra methods instead of querying Service for getting the node(s)
* Make service info optional when querying compute nodes
* Remove query by service_id on compute_nodes
* Do not provide by default service info when querying compute nodes
* Deprecate service_id field from compute_nodes and delete service relationship

Dependencies
============

None

Testing
=======

Current Tempest and unittests already cover this.

Documentation Impact
====================

None

References
==========

Formerly it was a bug:
https://bugs.launchpad.net/nova/+bug/1357491

[1]: https://review.openstack.org/#q,topic:bp/detach-service-from-computenode,n,z