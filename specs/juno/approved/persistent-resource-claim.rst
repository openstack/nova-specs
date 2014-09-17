..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

==========================================
Persistent resource claims
==========================================

https://blueprints.launchpad.net/nova/+spec/persistent-resource-claim

This blueprint plans to enhance the compute resource tracker to keep resource
claim as persistent to across nova-compute restart. This will be helpful
to move the resource claim process to the conductor.

Problem description
===================

The resource tracker provides an interface to claim resources for an instance.
However, the claim result is only kept in memory instead of kept persistently
and a context manager is returned to the caller.

There are several potential issue with this implementation. Firstly, it is
not easy to support two-phases resources claim, because it return the claim
as a context manager. Secondly without the persistent claim, the resource
tracker has to recalculate the claims from instances and migration object,
which requires more DB access and also requires locks to create the migration
object and to set the instance's host/node. Thirdaly, it's not easy to move
the _prep_resize() to the conductor because the claim is not persistent and
can't be invoked remotely.

Proposed change
===============

We suggest to change the resource tracker to track the resources claim and
persist the resources claim.

* When resources claim, the resource tracker will track the result claim. Each
  claim will be identified by compute node and a unique ID in the node.

* The resources claim is kept persistently by compute manager.

  There are several solutions to persist the claim like keeping it in
  central DB or in a local sqlite. In this spec, we will persistent the claim
  in local sqlite only, and a claim table is created to track the resources
  claim. We will enhance it later to be configurable as local sqlite or
  central DB. A mechanism like service_group is used to make the future
  extension easier.

  See "Alternative" for more info.

* The claim persistent code defines claim format version and upgrades the claim
  table if new version is required, so that we can enhance the resources claim,
  like support for extra_info, easily. A separate sqlite table is created to
  save the current claim table's version information.

  When a compute service is restarted after upgrade, it will check the claim
  table version. If the claim table version is lower than the latest version
  in the claim persistent code, it will upgrade the claim table to
  latest version and then update the version table. The upgrade code knows
  about the schema for each version so that we don't need keep schema
  information in the sqlite.

* When the compute node upgrades from non-persistent claim to persist
  claim, the upgrade code will find the table does not exist and thus
  will create the table from scratch based on the instance/migration
  information.

* The compute manager's periodic task will clean up any orphan claims. If
  a resources claim has no corresponding instance or migration object in the
  node, and it has been created for a specified period, it's an orphan claim
  and will be cleaned. The 'specified' time is a configuration item.

  Also if a server is evacuated when host is shutdown, the corresponding
  resources claim will be released when the compute service is restarted.

  In future, such clean up should happen in conductor which will take response
  of garbage collector.

Alternatives
------------

We had some discussions on how to keep the claims persistent. Originally it's
proposed to keep the claims in central DB. central DB will provide a global
view and will be more robust, but it will impact performance for each periodic
task. Later, it's suggested to keep in sqlite first which will provide much
better performance and can be extended to central DB in future.

Data model impact
-----------------

A sqlite table (claim table) is created to keep the claim. Below is
the data model to be used in sqlite. Although defined with sqlite
type, but it should similar to central DB also:

id: INTEGER
host: TEXT
node: TEXT
instance_uuid: TEXT
vcpus: INTEGER
memory_mb: INTEGER
disk_gb: INTEGER
pci: TEXT
resize_target: INTEGER
created_at: TEXT

The resize_target is to distinguish the resources claims in the same host for
the same instance, when resize in the same host. It is in fact a boolean value
stored as integers 0 (false) and 1 (true).

The created_at is the timestamp when the claim is created. It's a ISO 8601
format string.

Another table is created to keep the claim format version information.
table_name: TEXT
version: INTEGER

This table has only one entry, with the table_name as "claims" and the version
is the version of the claims in the claim table. As stated above, the upgrade
code knows about the schema of each version and knows how to upgrade between
versions.

REST API impact
---------------

No.

Security impact
---------------

No.

Notifications impact
--------------------

No.

Other end user impact
---------------------

No.

Performance Impact
------------------

No for this BP since we will not cover the DB solution.

Other deployer impact
---------------------

A new configuration 'claim_db' will be added to define how the sqlite
database is stored on disk. It will be a relative path to state_path
configuration item. The default value is claim.sqlite, which means
$state_path/claim.sqlite.

A new configuration 'claim_expiry_time'. A claim that has been created for
'claim_expiry_time' seconds and not is not associated with a instance or
migration object is an orphan claim and will be released.
The default value is 300 seconds.

Developer impact
----------------

No

Implementation
==============

Assignee(s)
-----------

Primary assignee:
  yunhong-jiang

Work Items
----------

* Claims persistent code.
* Update the resource tracker.

Dependencies
============
No

Testing
=======

We should have test code to check the sqlite is really populated correctly.

Documentation Impact
====================

The documentation should be updated to describe the 'claim_db' configuration,
where is the sqlite db lives now. Also the documents should describe how the
upgrade works according to the "Proposed change" section.

References
==========

https://wiki.openstack.org/wiki/Persistent_resource_claim
