..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

======================
Generic Resource Pools
======================

https://blueprints.launchpad.net/nova/+spec/generic-resource-pools

This blueprint aims to address the problem of incorrect resource usage
reporting by introducing the concept of a generic resource pool that manages a
particular amount of some resource.

Problem description
===================

Within a cloud deployment, there are a number of resources that may be consumed
by a user. Some resource types are provided by a compute node; these types of
resources include CPU, memory, PCI devices and local ephemeral disk. Other
types of resources, however, are *not* provided by a compute node, but instead
are provided by some external resource pool. An example of such a resource
would be a shared storage pool like that provided by Ceph or an NFS share.

Unfortunately, due to legacy reasons, Nova considers resources as only being
provided by a compute node. The tracking of resources assumes that it is the
compute node that provides the resource, and therefore when reporting usage of
certain resources, Nova naively calculates resource usage and availability by
simply summing amounts across all compute nodes in its database. This ends up
causing a number of problems [1] with usage and capacity amounts being
incorrect.

Use Cases
---------

As a deployer that has chosen to use a shared storage solution for storing
instance ephemeral disks, I want Nova and Horizon to report the correct
usage and capacity information for disk resources.

As an advanced Neutron user, I wish to use the new routed networks
functionality and be able to have Nova understand that a particular pre-created
Neutron port is associated with a specific subnet pool segment, and ensure that
my instance is booted on a compute node that matches that segment.

As an advanced Cinder user, if I specify a Cinder volume-id on the nova boot
command, I want Nova to be able to know which compute nodes are attached to a
Cinder storage pool that contains the requested volume.

Proposed change
===============

We propose to introduce the concept of a `resource pool` in Nova, and to create
a new RESTful scheduler API that allows the querying and management of these
resource pools.

A resource pool is simply a resource provider for one or more resource types to
multiple consumers of those resources. Resource pools are not specific to
shared storage, even though the impetus for their design is to solve the
problem of shared storage accounting in Nova.

A RESTful API is proposed (see below for details) that will allow
administrative (or service) users to create resource pools, to update the
capacity and usage information for those pools, and to indicate which compute
nodes can use the pool's resources by associating the pool with one or more
aggregates.

Scenario 1: Shared disk storage used for VM disk images
-------------------------------------------------------

In this scenario, we are attempting to make Nova aware that a set of compute
nodes in an environment use shared storage for VM disk images. The shared
storage is an NFS share that has 100 TB of total disk space. Around 1 TB of
this share has already been consumed by unrelated things.

All compute nodes in row 1, racks 6 through 10, are connected to this share.

1) The cloud deployer creates an aggregate representing all the compute
   nodes in row 1, racks 6 through 10::

    $AGG_UUID=`openstack aggregate create r1rck0610`
    # for all compute nodes in the system that are in racks 6-10 in row 1...
    openstack aggregate add host $AGG_UUID $HOSTNAME

2) The cloud deployer creates a resource pool representing the NFS share::

    $RP_UUID=`openstack resource-pool create "/mnt/nfs/row1racks0610/" \
        --aggregate-uuid=$AGG_UUID`

   Under the covers this command line does two REST API requests.
   One to create the resource-pool, another to associate the
   aggregate.

3) The cloud deployer updates the resource pool's capacity of shared disk::

    openstack resource-pool set inventory $RP_UUID \
        --resource-class=DISK_GB \
        --total=100000 --reserved=1000 \
        --min-unit=50 --max-unit=10000 --step-size=10 \
        --allocation-ratio=1.0

.. note::

    The `--reserved` field indicates the portion of the NFS share that has been
    consumed by non-accounted-for consumers. When Nova calculates if a resource
    pool has the capacity to meet a request for some amount of resources, it
    checks using the following formula: ((TOTAL - RESERVED) * ALLOCATION_RATIO)
    - USED >= REQUESTED_AMOUNT

Scenario 2a: Using Neutron routed networks functionality
--------------------------------------------------------

In this (future) scenario, we are assuming the Neutron routed networks
functionality is available in our deployment. There are a set of routed
networks, each containing a set of IP addresses, that represent the physical
network topology in the datacenter. Let us assume that routed network with the
identifier `rnA` represents the subnet IP pool for all compute nodes in rack 1
in row 3 of the datacenter. This subnet has a CIDR of `192.168.10.1/24`. Let us
also assume that unmanaged devices are consuming the bottom 5 IP addresses on
the subnet.

1) The network administrator creates a network and routed network segments
   representing broadcast domains for rack 1 in row 3::

    $NET_UUID=`openstack network create "routed network"`
    $SEG_UUID=`openstack subnet pool create $NET_UUID`
    $SUBNET_UUID=`openstack subnet create $SEG_UUID --cidr=192.168.10.1/24`

2) The cloud deployer creates an aggregate representing all the compute
   nodes in row 3, racks 1 through 5::

    $AGG_UUID=`openstack aggregate create "row 3, rack 1"`
    # for all compute nodes in the system that are in racks 1 in row 3...
    openstack aggregate add host $AGG_UUID $HOSTNAME

3) The cloud deployer creates a resource pool representing the routed network's
   pool of IPs::

    openstack resource-pool create "routed network rack 1 row 3" \
        --uuid=$SUBNET_UUID \
        --aggregate-uuid=$AGG_UUID

.. note::

    Please note that the `--uuid` field in the `openstack resource-pool create`
    call above is an optional argument to `openstack resource-pool create`. You
    may have noticed that in the first use case, we do not provide a UUID when
    creating the resource pool.

    The `--uuid` parameter allows passing in a UUID identifier so that external
    systems can supply an already-known external global identifier for the
    resource pool.  If the `--uuid` parameter is not provided in the call to
    `openstack resource-pool create`, a new UUID will automatically be assigned
    and displayed to the user.

    In the case above, we are assuming that the call to the `openstack
    subnet create` returns some value containing a UUID for the subnet IP
    allocation pool (the segment).

4) The cloud deployer updates the resource pool's capacity of IPv4 addresses::

    openstack resource-pool set inventory $RP_UUID \
        --resource-class=IPV4_ADDRESS \
        --total=254 --reserved=5 \
        --min-unit=1 --max-unit=1 --step-size=1 \
        --allocation-ratio=1.0

.. note::

    Instead of cloud deployer manually updating the resource pool's inventory,
    it's more likely that a script would call the `neutron subnet-XXX` commands
    to determine capacity and reserved amounts.

5) The cloud user creates a port in Neutron, asking for an IP out of a
   particular subnet::

    PORT_UUID=`openstack port create --network-id=$NET_UUID --fixed-ip \
        subnet=$SUBNET_UUID`

6) The cloud user boots an instance, specifying the ID of the port created
   in step 5::

    openstack server create --nic port_id=$PORT_UUID --image XXX --flavor AAA

7) During (or perhaps before) the scheduling process, Nova will want to answer
   the question, "if this port ID is a member of a resource pool containing
   `IPV4_ADDRESS` resources, which compute nodes are possible target
   destinations that are associated with that IPv4 subnet?".

   The Nova scheduler (or conductor) would be able to determine the set of
   compute nodes used in placement decisions by looking at the aggregates that
   the resource pool representing that subnet was associated with, which will
   in turn allow it to identify the compute nodes associated with those
   aggregates.

What this gives the cloud user is basic network affinity during scheduling,
with the cloud user only needing to specify a port ID.

Scenario 2b: Live migration of instance booted in scenario 2a
-------------------------------------------------------------

Assume that the virtual machine launched in step #6 of Scenario 2a needs to be
live-migrated -- perhaps because the compute host is failing or being upgraded.
Live migration moves a workload from a source host to a destination host,
keeping the workload's networking setup intact. In the case where an instance
was booted with a port that is associated with a particular resource pool
containing a routed network's set of IP addresses, we need to ensure that the
target host is in the same aggregate as the source host (since the routed
network only spans the compute hosts in a particular aggregate).

With the generic resource pool information, we can have the scheduler (or
conductor) limit the set of compute nodes used in determining the
live-migration's destination host by examining the resource providers that
match the `IPV4_ADDRESS` resource class for the instance UUID as a consumer.
From this list we can identify the aggregates associated with the resource
provider and from the list of aggregates we can determine the compute hosts
that can serve as target destinations for the migration.

Alternatives
------------

An alternative approach to having an entity in the Nova system to represent
these resource pools would be to have Nova somehow examine a configuration flag
to determine whether disk resources on a compute node are using shared storage
versus locally available. There are a couple problems with this approach:

* This approach is not generic and assumes the only shared resource is disk
  space
* This information isn't really configuration data but rather system inventory
  data, and therefore belongs in the database, not configuration files

Data model impact
-----------------

A new many-to-many mapping table in the API database will be created to enable
an aggregate to be associated with one or more resource pools::

    CREATE TABLE resource_provider_aggregates (
        resource_provider_id INT NOT NULL,
        aggregate_id INT NOT NULL,
        PRIMARY KEY (aggregate_id, resource_provider_id),
        FOREIGN KEY fk_aggregates (aggregate_id)
            REFERENCES aggregates (id),
        FOREIGN KEY fk_resource_providers (resource_provider_id),
            REFERENCES resource_providers (id)
    );

A new nova object model for resource pools will be introduced. This object
model will be a thin facade over the `resource_providers` table and allow
querying for the aggregates associated with the resource pool along with the
inventory and allocation records for the pool.

REST API impact
---------------

*ALL* below API calls are meant only for cloud administrators and/or service
users.

*Note*: All of the below API calls should be implemented in
`/nova/api/openstack/placement/`, **not** in `/nova/api/openstack/compute/`
since these calls will be part of the split-out scheduler REST API.  There
should be a wholly separate placement API endpoint, started on a different port
than the Nova API, and served by a different service daemon defined in
`/nova/cmd/placement-api.py`.

Microversion support shall be added to the new placement API from the start.

ETags will be used to protect against the lost update problem. This
means that when doing a `PUT` the request must include an `If-Match`
header containing an ETag that matches the server's current ETag for
the resource.

The API changes add resource endpoints to:

* `GET` a list of resource pools
* `POST` a new resource pool
* `GET` a single resource pool with links to its sub-resources
* `PUT` a single resource pool to change its name
* `DELETE` a single resource pool and its associated inventories (if
  no allocations are present) and aggregates (the association is
  removed, not the aggregates themselves)
* `GET` a list of the inventories associated with a single resource
  pool
* `POST` a new inventory of a particular resource class
* `GET` a single inventory of a given resource class
* `PUT` an update to an inventory
* `DELETE` an inventory (if no allocations are present)
* `PUT` a list of aggregates to associate with this resource
* `GET` that list of aggregates
* `GET` a list, by resource class, of usages

This provides granular access to the resources that matter while
providing straightfoward access to usage information.

Details follow.

The following new REST API calls will be added:

`GET /resource_pools`
**********************

Return a list of all resource pools in this Nova deployment.

Example::

    200 OK
    Content-Type: application/json

    {
      "resource_pools": [
        {
          "uuid": "b6b065cc-fcd9-4342-a7b0-2aed2d146518",
          "name": "RBD volume group",
          "links": [
             {
               "rel": "self",
               "href": "/resource_pools/b6b065cc-fcd9-4342-a7b0-2aed2d146518"
             },
             {
               "rel": "inventories",
               "href": "/resource_pools/b6b065cc-fcd9-4342-a7b0-2aed2d146518/inventories"
             },
             {
               "rel": "aggregates",
               "href": "resource_pools/b6b065cc-fcd9-4342-a7b0-2aed2d146518/aggregates"
             },
             {
               "rel": "usages",
               "href": "resource-pools/b6b065cc-fcd9-4342-a7b0-2aed2d146518/usages"
             }
          ]
        },
        {
          "uuid": "eaaf1c04-ced2-40e4-89a2-87edded06d64",
          "name": "Global NFS share",
          "links": [
             {
               "rel": "self",
               "href": "/resource_pools/eaaf1c04-ced2-40e4-89a2-87edded06d64"
             },
             {
               "rel": "inventories",
               "href": "/resource_pools/eaaf1c04-ced2-40e4-89a2-87edded06d64/inventories"
             },
             {
               "rel": "aggregates",
               "href": "resource_pools/eaaf1c04-ced2-40e4-89a2-87edded06d64/aggregates"
             },
             {
               "rel": "usages",
               "href": "resource-pools/eaaf1c04-ced2-40e4-89a2-87edded06d64/usages"
             }
          ]
        }
      ]
    }

`POST /resource_pools`
**********************

Create one new resource pool.

An example POST request::

    Content-type: application/json

    {
        "name": "Global NFS share",
        "uuid": "eaaf1c04-ced2-40e4-89a2-87edded06d64"
    }

The body of the request must match the following JSONSchema document::

    {
        "type": "object",
        "properties": {
            "name": {
                "type": "string"
            },
            "uuid": {
                "type": "uuid"
            }
        },
        "required": [
            "name"
        ]
        "additionalProperties": False
    }

The response body is empty. The headers include a location header
pointing to the created resource pool::

    201 Created
    Location: /resource_pools/eaaf1c04-ced2-40e4-89a2-87edded06d64

A `409 Conflict` response code will be returned if another resource pool
exists with the provided name.

`GET /resource_pools/{uuid}`
****************************

Retrieve a representation of the resource pool identified by `{uuid}`.

Example::


    GET /resource_pools/eaaf1c04-ced2-40e4-89a2-87edded06d64

    200 OK
    Content-Type: application/json

    {
      "uuid": "eaaf1c04-ced2-40e4-89a2-87edded06d64",
      "name": "Global NFS share",
      "links": [
         {
           "rel": "self",
           "href": "/resource_pools/eaaf1c04-ced2-40e4-89a2-87edded06d64"
         },
         {
           "rel": "inventories",
           "href": "/resource_pools/eaaf1c04-ced2-40e4-89a2-87edded06d64/inventories"
         },
         {
           "rel": "aggregates",
           "href": "resource_pools/eaaf1c04-ced2-40e4-89a2-87edded06d64/aggregates"
         },
         {
           "rel": "usages",
           "href": "resource-pools/eaaf1c04-ced2-40e4-89a2-87edded06d64/usages"
         }
      ]
    }

If the resource pool does not exist a `404 Not Found` must be
returned.

`PUT /resource_pools/{uuid}`
*****************************

Update the name of resource pool identified by `{uuid}`.

Example::

    PUT /resource_pools/eaaf1c04-ced2-40e4-89a2-87edded06d64

    Content-type: application/json

    {
        "name": "Global NFS share"
    }

The returned HTTP response code will be one of the following:

* `204 No Content` if the request was successful and the resource
  pool was updated.
* `400 Bad Request` for bad or invalid syntax.
* `404 Not Found` if a resource pool with `{uuid}` does not exist.
* `409 Conflict` if another resource pool exists with the provided
  name.

`DELETE /resource_pools/{uuid}`
********************************

Delete the resource pool identified by `{uuid}`.

This will also disassociate aggregates and delete inventories.

The body of the request and the response is empty.

The returned HTTP response code will be one of the following:

* `204 No Content` if the request was successful and the resource
  pool was removed.
* `404 Not Found` if the resource pool identified by `{uuid}` was
  not found.
* `409 Conflict` if there exist allocations records for any of the
  inventories that would be deleted as a result of removing the
  resource pool.

`GET /resource_pools/{uuid}/inventories`
*****************************************

Retrieve a list of inventories that are associated with the resource
pool identified by `{uuid}`.

Example::

    GET /resource_pools/eaaf1c04-ced2-40e4-89a2-87edded06d64/inventories

    200 OK
    Content-Type: application/json

    {
      "inventories": {
        'DISK_GB': {
          "total": 2048,
          "reserved": 512,
          "min_unit": 10,
          "max_unit": 1024,
          "step_size": 10,
          "allocation_ratio": 1.0
        },
        'IPV4_ADDRESS': {
          "total": 256,
          "reserved": 2,
          "min_unit": 1,
          "max_unit": 1,
          "step_size": 1,
          "allocation_ratio": 1.0
        }
      }
    }

The returned HTTP response code will be one of the following:

* `200 OK` if the resource pools exists.
* `404 Not Found` if the resource pool identified by `{uuid}` was
  not found.

`POST /resource_pools/{uuid}/inventories`
*****************************************

Create a new inventory for the resource pool identified by `{uuid}`.

Example::

    POST /resource_pools/eaaf1c04-ced2-40e4-89a2-87edded06d64/inventories
    Content-Type: application/json

    {
      "resource_class": "DISK_GB",
      "total": 2048,
      "reserved": 512,
      "min_unit": 10,
      "max_unit": 1024,
      "step_size": 10,
      "allocation_ratio": 1.0
    }

The body of the request must match the following JSONSchema document::

    {
        "type": "object",
        "properties": {
            "resource_class": {
                "type": "string",
                "pattern": "^[A-Z_]+"
            },
            "total": {
                "type": "integer"
            },
            "reserved": {
                "type": "integer"
            },
            "min_unit": {
                "type": "integer"
            },
            "max_unit": {
                "type": "integer"
            },
            "step_size": {
                "type": "integer"
            },
            "allocation_ratio": {
                "type": "number"
            },
        },
        "required": [
            "resource_class",
            "total"
        ],
        "additionalProperties": False
    }

The response body is empty. The headers include a location header
pointing to the created resource pool::

    201 Created
    Location: /resource_pools/eaaf1c04-ced2-40e4-89a2-87edded06d64/inventories/DISK_GB

.. note::

    If some non-Nova things have consumed some amount of resources in the pool,
    the "reserved" field should be used to adjust the total capacity of the
    inventory.

The returned HTTP response code will be one of the following:

* `201 Created` if the inventory is successfully created
* `404 Not Found` if the resource pool identified by `{uuid}` was
  not found
* `400 Bad Request` for bad or invalid syntax (for example an
  invalid resource class)
* `409 Conflict` if an inventory for the proposed resource class
  already exists

`GET /resource_pools/{uuid}/inventories/{resource_class}`
**********************************************************

Retrieve a single inventory of class `{resource_class}` associated
with the resource pool identified by `{uuid}`.

Example::

    GET /resource_pools/eaaf1c04-ced2-40e4-89a2-87edded06d64/inventories/DISK_GB
    200 OK
    {
      "resource_class": "DISK_GB",
      "total": 2048,
      "reserved": 512,
      "min_unit": 10,
      "max_unit": 1024,
      "step_size": 10,
      "allocation_ratio": 1.0
    }


The returned HTTP response code will be one of the following:

* `200 OK` if the inventory exists
* `404 Not Found` if the resource pool identified by `{uuid}` was
  not found or an inventory of `{resource_class}` is not associated
  with the resource pool

`PUT /resource_pools/{uuid}/inventories/{resource_class}`
**********************************************************

Update an existing inventory.

Example::

    PUT /resource_pools/eaaf1c04-ced2-40e4-89a2-87edded06d64/inventories/DISK_GB
    {
      "total": 1024,
      "reserved": 512,
      "min_unit": 10,
      "max_unit": 1024,
      "step_size": 10,
      "allocation_ratio": 1.0
    }

The body of the request must match the JSONSchema document described
in the inventory POST above, except that `resource_class` is not
required and if present is ignored.

The returned HTTP response code will be one of the following:

* `204 No Content` if the inventory is successfully created
* `404 Not Found` if the resource pool identified by `{uuid}` was
  not found
* `400 Bad Request` for bad or invalid syntax
* `409 Conflict` if the changes `total`, `reserved` or
  `allocation_ratio` would causes existing allocations to be in
  conflict with proposed capacity

`DELETE /resource_pools/{uuid}/inventories/{resource_class}`
*************************************************************

Delete an existing inventory.

Example::

    DELETE /resource_pools/eaaf1c04-ced2-40e4-89a2-87edded06d64/inventories/DISK_GB

The body is empty.

The returned HTTP response code will be one of the following:

* `204 No Content` if the inventory is successfully removed
* `404 Not Found` if the resource pool identified by `{uuid}` was
  not found or if there is no associated inventory of
  `{resource_class}`
* `400 Bad Request` for bad or invalid syntax
* `409 Conflict` if there are existing allocations for this
  inventory

`GET /resource_pools/{uuid}/aggregates`
***************************************

Get a list of aggregates associated with this resource pool.

Example::

    GET /resource_pools/eaaf1c04-ced2-40e4-89a2-87edded06d64/aggregates

    {"aggregates":
      [
        "21d7c4aa-d0b6-41b1-8513-12a1eac17c0c",
        "7a2e7fd2-d1ec-4989-b530-5508c3582025"
      ]
    }

.. note:: The use of a name `aggregates` list preserves the option
          of adding other keys to the object later. This is standard
          api-wg form for collection resources.

The returned HTTP response code will be one of the following:

* `200 OK` if the resource pool exists
* `404 Not Found` if the resource pool identified by `{uuid}` was
  not found

`PUT /resource_pools/{uuid}/aggregates`
**************************************

Associate a list of aggregates with this resource pool.

Example::

    PUT /resource_pools/eaaf1c04-ced2-40e4-89a2-87edded06d64/aggregates

    [
        "21d7c4aa-d0b6-41b1-8513-12a1eac17c0c",
        "b455ae1f-5f4e-4b19-9384-4989aff5fee9"
    ]

The returned HTTP response code will be one of the following:

* `204 No content` if the aggregates are successfully updated
* `404 Not Found` if the resource pool does not exist
* `400 Bad Request` for bad or invalid syntax.

`GET /resource_pools/{uuid}/usages`
***********************************

Retrieve a report of usage information for resources associated with
the resource pool identified by `{uuid}`. The value is a dictionary
of resource classes paired with the sum of the allocations of that
resource class for this resource pool.

Example::

    GET /resource_pools/eaaf1c04-ced2-40e4-89a2-87edded06d64/usages

    {
      "usages": {
        "DISK_GB": 480,
        "IPV4_ADDRESS": 2
      }
    }

The returned HTTP response code will be one of the following:

* `200 OK` if the resource pool exists. If there are no associated
  inventories the `usages` dictionary should be empty.
* `404 Not Found` if the resource pool does not exist.

.. note:: Usages are read only.


Security impact
---------------

None.

Notifications impact
--------------------

We should create new notification messages for when resource pools are created,
destroyed, updated, associated with an aggregate and disassociated from an
aggregate.

Other end user impact
---------------------

New openstackclient CLI commands should be created for the corresponding
functionality:

* `openstack resource-pool list`
* `openstack resource-pool show $UUID`
* `openstack resource-pool create "Global NFS share" \
  --aggregate-uuid=$AGG_UUID \
  [--uuid=$UUID]`
* `openstack resource-pool delete $UUID`
* `openstack resource-pool update $UUID --name="New name"`
* `openstack resource-pool list inventory $UUID`
* `openstack resource-pool set inventory $UUID \
   --resource-class=DISK_GB \
   --total=1024 \
   --reserved=450 \
   --min-unit=1 \
   --max-unit=1 \
   --step-size=1 \
   --allocation-ratio=1.0`
* `openstack resource-pool delete inventory $UUID \
  --resource-class=DISK_GB`
* `openstack resource-pool add aggregate $UUID $AGG_UUID`
* `openstack resource-pool delete aggregate $UUID $AGG_UUID`

Performance Impact
------------------

None.

Other deployer impact
---------------------

Deployers who are using shared storage will need to create a resource pool for
their shared disk storage, create any host aggregates that may need to be
created for any compute nodes that utilize that shared storage, associate the
resource pool with those aggregates, and schedule (cronjob or the like) some
script to periodically run `openstack resource-pool set inventory $UUID
--resource-class=DISK_GB --total=X --reserved=Y`.

We should include a sample script along with the documentation for this.

Developer impact
----------------

None.

Implementation
==============

Assignee(s)
-----------

Primary assignee:
  cdent

Other contributors:
  jaypipes

Work Items
----------

* Create database models and migrations for new `resource_provider_aggregates`
  table.
* Create `nova.objects` models for `ResourcePool`
* Create REST API controllers for resource pool querying and handling
* Modify resource tracker to pull information on aggregates the compute node is
  associated with and the resource pools available for those aggregates. If the
  instance is requesting some amount of DISK_GB resources and the compute node
  is associated with a resource pool that contains available DISK_GB inventory,
  then the resource tracker shall claim the resources (write an allocation
  record) against the resource pool, not the compute node itself.
* Modify the scheduler to look at resource pool information for aggregates
  associated with compute nodes to determine if request can be fulfilled by the
  resource pool

  For this particular step, the changes to the existing filter scheduler
  should be minimal. Right now, the host manager queries the list of all
  aggregates in the deployment upon each call to
  `select_destinations()`. This call to
  `nova.objects.AggregateList.get_all()` returns a set of aggregate
  objects that are then collated to the hosts that are in each
  aggregate. During certain filter `host_passes()` checks, the
  aggregate's extra specs can be queried to determine if certain
  capability requests are satisfied. We will want to return inventory
  and usage information for each resource pool assigned to each
  aggregate so that filters like the `DiskFilter` can query not just the
  host's `local_gb` value but also the aggregate's inventory information
  for share disk storage.

* Docs and example cronjob scripts for updating capacity and usage information
  for a shared resource pool of disk
* Functional integration tests in a multi-node devstack environment with shared
  storage

Dependencies
============

* `policy-in-code` Blueprint must be completed before this one since we want to
  use the new policy framework in the new placement API modules
* `resource-classes` Blueprint must be completed before this one.
* `resource-providers` Blueprint must be completed before this one in order to
  ensure the `resource-providers`, `inventories` and `allocations` tables
  exist.
* `compute-node-inventory-newton` Blueprint must be completed in order for all
  compute nodes to have a UUID column and a record in the `resource_providers`
  table. This is necessary in order to determine which resource providers are
  resource pools and not compute nodes.
* The part of the `resource-providers-allocations` blueprint that involves
  migrating the `inventories`, `allocations`, `aggregates`,
  `resource_providers` tables to the top-level API database must be completed
  before this

Testing
=======

Full unit and functional integration tests must be added that demonstrate
proper resource accounting of shared storage represented with a generic
resource pool.

Documentation Impact
====================

Developer docs should be added that detail the new resource pool functionality,
how external scripts can keep capacity and usage information updated for a
resource pool.

References
==========

[1] Bugs related to resource usage reporting and calculation:

* Hypervisor summary shows incorrect total storage (Ceph)
  https://bugs.launchpad.net/nova/+bug/1387812
* rbd backend reports wrong 'local_gb_used' for compute node
  https://bugs.launchpad.net/nova/+bug/1493760
* nova hypervisor-stats shows wrong disk usage with shared storage
  https://bugs.launchpad.net/nova/+bug/1414432
* report disk consumption incorrect in nova-compute
  https://bugs.launchpad.net/nova/+bug/1315988
* VMWare: available disk spaces(hypervisor-list) only based on a single
  datastore instead of all available datastores from cluster
  https://bugs.launchpad.net/nova/+bug/1347039

History
=======

.. list-table:: Revisions
   :header-rows: 1

   * - Release Name
     - Description
   * - Newton
     - Introduced
