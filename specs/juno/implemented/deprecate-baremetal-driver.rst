..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

====================================================
Upgrade from a nova "baremetal" deployment to Ironic
====================================================

https://blueprints.launchpad.net/nova/+spec/deprecate-baremetal-driver

This specification describes the requirements to providing an upgrade path from
a deployment of the nova.virt.baremetal driver to the nova.virt.ironic driver.
It outlines the data migration path and service upgrade process for such an
upgrade.

Problem description
===================

The community has split out the functionality of provisioning bare metal
servers into a separate program, which includes the ironic and
python-ironicclient projects. While the original intent of the
nova.virt.baremetal driver was to be an experimental proof-of-concept for
TripleO, it may have been deployed in some production environments to
facilitate high-performance compute workloads.

It is unreasonable to expect operators who have chosen to use
nova.virt.baremetal to lose all state and delete all instances during an
upgrade. Migration tools will be available within Ironic.

NOTE: The service upgrade is only supported within the same release version,
and will only be supported in the first integrated release containing Ironic.

For example, if this work is completed during the Juno cycle, an upgrade from
"juno baremetal" to "juno ironic" will be supported, but a direct upgrade from
"icehouse baremetal" to "juno ironic" will NOT be supported. That should be
accomplished by first upgrading from "icehouse baremetal" to "juno baremetal"
and then to "juno ironic".

Proposed change
===============

At the start of a release cycle following the cycle in which this work is
completed, the artifacts of baremetal will be delete from the Nova tree.
This includes: the baremetal virt driver, baremetal host manager, 'nova_bm'
database schema and its migration tests.

The API extension will be replaced by a read-only proxy API. This will forward
the following API commands to Ironic:
- baremetal-interface-list
- baremetal-node-list
- baremetal-node-show


Alternatives
------------

Three alternatives have been discussed.

* Do not provide any upgrade path; this met with significant opposition.

* Provide a data-only migration (eg, require that instances be deleted
  prior to, or as part of, the migration). This was also met with opposition.

* Rather than a data extract-and-load script, one could enroll instances
  via Ironic's REST API. This would require ironic's REST API to accept nodes
  that have non-null provision_state and power_state, which it expressly
  does not allow today. This change would require significant changes
  to the provisioning API and state management within the conductor service.

Data model impact
-----------------

The nova_bm schema and all supporting DB migration tests may be deleted.

REST API impact
---------------

The baremetal extension to Nova's REST API will be replaced with a read-only
proxy API to Ironic. This will check policy, and forward the user's token
to Ironic for secondary validation (Ironic requires "admin" privileges).

The following commands will NOT be proxied:
- baremetal-interface-add
- baremetal-interface-remove
- baremetal-node-create
- baremetal-node-delete

The endpoints for these methods will return a 404 NOT FOUND.

Notifications impact
--------------------

None

Security impact
---------------

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

None


Implementation
==============

Assignee(s)
-----------

Primary assignee:
  devananda

Other contributors:
  adam_g
  romcheg

Work Items
----------

* Create new API proxy/extension

* Database extraction-and-loading script
  (in Ironic's tree)

* Flavor update script
  (in Ironic's tree)

* Operator documentation
  (in Ironic's tree)

* Grenade tests
  (in Grenade)

Dependencies
============

This proposal depends primarily upon the acceptance of the nova.virt.ironic
driver into the Nova codebase, and secondarily on grenade testing of the
migration script and upon several open changes in tempest which will allow
Ironic to pass tempest/api/compute.


Testing
=======

A Grenade test will need to be developed that can:

* deploy nova with the fake virt driver

* populate nova_bm database with baremetal nodes and interfaces that map to
  local VMs

* create dummy images in glance for nova-bm's deploy kernel and ramdisk and
  create a flavor referencing them

* install ironic, build and publish new deploy kernel and ramdisk

* perform data migration

* reconfigure nova to use ironic, start ironic, and restart nova-compute

* run tempest


Documentation Impact
====================

Upgrade documentation must be written and maintained for one release cycle.

The proposed upgrade path is:

* build ironic deploy ramdisk and load it in glance

* create empty ironic database

* start maintenance period

* stop nova-compute services which are configured to use the
  nova.virt.baremetal driver

* update flavor metadata in Nova to reference new deploy kernel & ramdisk

* extract data from nova_bm and import to ironic, using the provided tool.
  This tool must accept separate database credentials for each database.

* start ironic services

* observe ironic log files to ensure take over completed w/o errors

* reconfigure nova-scheduler to use the ironic host manager, and, if desired,
  the exact match scheduler filters, then restart it

* reconfigure nova-compute service to use the nova.virt.ironic driver
  and the ClusteredComputeManager, then restart it

* observe nova-compute log files to ensure it has connected to ironic and is
  reporting available resources accurately

* end maintenance period

References
==========

https://etherpad.openstack.org/p/juno-nova-deprecating-baremetal

https://etherpad.openstack.org/p/juno-nova-mid-cycle-meetup

https://review.openstack.org/#/q/topic:ironic_grenade,n,z

https://review.openstack.org/#/q/topic:ironic_tempest,n,z
