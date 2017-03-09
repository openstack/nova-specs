..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

====================================================
The Traits API - Manage Traits with ResourceProvider
====================================================

https://blueprints.launchpad.net/nova/+spec/resource-provider-traits

This spec aims to propose a new REST resource `traits` in placement API to
manage the qualitative parts of ResourceProviders. Using Traits API, the
placement service can manage the characteristics of resource providers by
Traits, and then help scheduler make better placement decisions that match the
boot requests.

Problem description
===================

The ResourceProvider has a collection of Inventory and Allocation objects to
manage the *quantitative* aspects of a boot request: When an instance uses
resources from a ResourceProvider, the corresponding resource amounts of
Inventories are subtracted by its Allocations. Despite the quantitative
aspects, the ResourceProvider also needs non-consumable *qualitative* aspects
to differenitiate their characteristics from each other.

The classic example is requesting disk from different providers: a user may
request 80GB of disk space for an instance (quantitative), but may also expect
that the disk be SSD instead of spinning disk (qualitative). Having a way to
mark that a storage provider (it can be a shared storage or compute node's
attached storage) is SSD or spinning is what we are concerned with.

Many traits are defined in a standard way by OpenStack, such as the Intel CPU
instruction set extensions. These are reported programmatically, and will be
consistent across all OpenStack clouds. However, the deployer may have some
other custom traits that placement service needs to support.

Use Cases
---------

* An admin user wants to know the valid traits that the cloud can recognize.
* Other OpenStack services want to know whether user input traits are valid in
  the cloud.
* Other OpenStack services want a way to indicate the traits of the
  ResourceProviders (For example, Nova wants to indicate which cpu features
  a compute node provides)
* A cloud provider admin wants a way to indicate the traits of resource
  providers. (For example, a cloud provider admin wants to indicate that some
  storage providers are better-performing than others)

Proposed change
===============

We propose to use a new REST resource `trait` in the placement API to manage
qualitative information of resource providers. The `trait` is just a string, it
is pretty similar with `Tags` which are defined in `Tags API-WG guideline`_.

There are two kinds of Traits: The standard traits and the custom traits.

The standard traits are interoperable across different Openstack cloud
deployments. The definition of standard traits comes from the `os-traits`
library. The standard traits are read-only in the placement API which means
that the user can't modify any standard traits through API. All the traits are
classified into different namespaces. The namespace is defined by `os-traits`
also. The definition of traits in `os-traits` will be discussed in a separate
proposal. All the traits used in the examples below are for demonstration
purposes only.

The custom traits are used by admin users to manage the non-standard
qualitative information of ResourceProviders. The admin user can define the
custom traits from the placement API. The custom trait must prefix with
the namespace `CUSTOM_`. The namespace `CUSTOM_` is defined in `os-traits`.

The users can only use valid traits in the request. The valid traits include
the standard traits and the custom traits.

The Traits API's usage scenarios are listed below:

Scenario 1: Single Resource Provider
------------------------------------

In this scenario, Nova creates one ResourceProvider for each compute node.
Each compute node then reports its qualitative information, which are tagged
with a set of Traits. This will be updated regularly, although we don't expect
a resource provider's qualitative information to change very often.

Scenario 2: Shared Storage Resource Provider
--------------------------------------------

Using shared storage in this example, the cloud admin can then tag certain
provider as having SSD trait so that they are only used by flavors that specify
SSD trait.

The first three steps are the same as in:
`http://specs.openstack.org/openstack/nova-specs/specs/newton/approved/generic-resource-pools.html#scenario-1-shared-disk-storage-used-for-vm-disk-images`

1) The cloud deployer creates an aggregate representing all the compute
   nodes in row 1, racks 6 through 10::

    $AGG_UUID=`openstack aggregate create r1rck0610`
    # for all compute nodes in the system that are in racks 6-10 in row 1...
    openstack aggregate add host $AGG_UUID $HOSTNAME

2) The cloud deployer creates a ResourceProvider representing the NFS share::

    $RP_UUID=`openstack resource-provider create "/mnt/nfs/row1racks0610/" \
        --aggregate-uuid=$AGG_UUID`

   Under the covers this command line does two REST API requests.
   One to create the resource-provider, another to associate the
   aggregate.

3) The cloud deployer updates the resource provider's capacity of shared disk::

    openstack resource-provider set inventory $RP_UUID \
        --resource-class=DISK_GB \
        --total=100000 --reserved=1000 \
        --min-unit=50 --max-unit=10000 --step-size=10 \
        --allocation-ratio=1.0

4) The cloud deployer adds the `STORAGE_SSD` trait, which is a standard trait
   in `os-traits`, to the compute node resource provider::

    openstack resource-provider trait add $RP_UUD STORAGE_SSD


Sync os-traits values into Placement
------------------------------------

The placement API is designed to be the single source of truth for validing
which traits are valid in the deployment. There is no hard dependency chain
for upgrading services, but operators have to keep in mind that only Placement
API os-traits version will be the master in the deployment.

The new command `placement-manage os-traits sync` will be added. It is used to
sync the standard traits from `os-traits` into the placement DB. The deployer
should invoke this command after `os-traits` upgrade.

Traits API vs. Aggregate metadata API
-------------------------------------

Previously, a deployer would manage qualitative information through the use of
Aggregate metadata. They would do this by creating an aggregate for the hosts
with a particular trait that they wished to track, and then set metadata on
that aggregate to identify the trait that those hosts have. This practice has
limited scalability and is hard to manage. Take for example the situation where
there are variety of trait combinations in a deployment: this requires managing
aggregates indirectly instead of straightforward traits. This creates a very
complex mapping between traits and hosts.  It is also not a simple task to
determine which traits a particular host may have.  Finally, this approach only
works for compute nodes, not all potential resource providers.

The proposed `traits` REST API endpoint will replace the use of aggregates to
track and manage qualitative information. The traits for a given host will be
a flat list, and is straightforward to manage through the API.

Once the use of Traits API is in place, the use of aggregate metadata will
be deprecated. Of course, aggregates themselves will remain, as they are used
for much more than metadata purposes. The deprecation of aggregate metadata
will be discussed in a separate spec.

Alternatives
------------

An alternative for naming this new REST resource as Tags in previous proposal.
But currently, there is a validation for the standard traits from the
'os-traits' library. The API needs to distinguish the standard traits and
custom traits, they won't be some generic tags anymore. So 'Traits' is
the correct term.

An alternative idea is adding attributes to the traits. An example would be in
creating namespaces: instead of prefixing the trait string with a namespace
string, we would add an attribute to trait that denotes its namespace. This
would eliminate the need to add the "HW" and "HV" parts of the trait name in
the examples above. Another use of attributes is to distinguish between
system-generated and custom traits. Yet another potential use is define
classes of traits, such as user-queryable. So while this simplifies some things
by making these aspects of traits queryable, it means that we have to treat a
trait as an object, and not just a simple string.

Another alternative to the use of traits is to create a special ResourceClass
for each capability that has infinite inventory. In this approach, a request
for, say, SSD would "consume" a single SSD, but since the inventory is
infinite, it never runs out. This would have the advantage of not having to
create any new tables, and would only require small changes to existing classes
to make infinite inventory possible. It does suffer from a conceptual
disconnect, since we really aren't consuming anything. It would also make
querying for capabilities a bit more roundabout. The more explanation about
this idea is at blog `Simple Resource Provision`_.

One more alternative which inspired by above idea is about use
ResourceProviderTraits instead of ResourceClass. The reason is ResourceClass
and Traits are very similar, both of them are string. Actually we just need an
indication for the management of quantitative and qualitative. With this way,
we can achieve the goal of above alternative idea, and without the infinite
inventory. The more explanation about this is at mail-list `Use
ResourceProviderTraits instead of ResourceClass`_.

Data model impact
-----------------

The new table will be added to API Database. For the database schema, the
following tables would suffice::

  CREATE TABLE traits (
    id INT NOT NULL,
    name VARCHAR(255) NOT NULL,
    PRIMARY KEY (id),
    UNIQUE INDEX (name)
  );

  CREATE TABLE resource_provider_traits (
    resource_provider_id INT NOT NULL
    trait_id INT NOT NULL,
    PRIMARY KEY (resource_provider_id, trait_id),
  );


REST API impact
---------------

The Traits API is attached to the Placement API endpoint. The Traits API
includes two new REST resources: `/traits` and
`/resource_providers/{uuid}/traits`.

* `/traits`: This is used to manage the traits in the cloud, and this is also
  the only place to query the existing and associated traits in the cloud. It
  helps the traits be consistent across all the services in the cloud. The
  traits can be read by all users and can only be modified by admin users.
* `/resource_providers/{uuid}/traits`: This is used to query/edit the
  association between traits and resource_providers. This endpoint can only be
  used by admin and/or service users.

The generic json-schema of Trait object is as below::

  TRAIT = {
    "type": "string",
    'minLength': 1, 'maxLength': 255,
    "pattern": "^[A-Z0-9_]+$"
  }

The custom trait must prefixed with `CUSTOM_`, the json-schema is as below::

  CUSTOM_TRAIT = {
    "type": "string",
    'minLength': 1, 'maxLength': 255,
    "pattern": "^CUSTOM_[A-Z0-9_]+$"
  }

The added API endpoints are:

* `GET /traits` a list of all existing trait strings
* `GET /traits/{trait}` check whether a trait exists in the cloud
* `PUT /traits/{trait}` create a new custom trait to placement service
* `DELETE /traits/{trait}` remove a custom trait from placement service
* `GET /resource_providers/{rp_uuid}/traits` a list of traits associated with a
  specific resource provider
* `PUT /resource_providers/{rp_uuid}/traits` set all the traits for a specific
  resource provider
* `DELETE /resource_providers/{rp_uuid}/traits` remove any existing trait
  associations for a specific resource provider

Details of added endpoints are as follows:

`GET` /traits
*************

Return a list of valid trait strings according to parameters specified.

The body of the response must match the following JSONSchema document::

    {
        "type": "object",
        "properties": {
            "traits": {
                "type": "array",
                "items": TRAIT,
            }
        },
        'required': ['traits'],
        'additionalProperties': False
    }

The default action is to query all the standard and custom traits in
placement service::

    GET /traits

The response::

    200 OK
    Content-Type: application/json

    {
        "traits": [
            "HW_CPU_X86_3DNOW",
            "HW_CPU_X86_ABM",
            ...
            "CUSTOM_TRAIT_1",
            "CUSTOM_TRAIT_2"
        ]
    }

The following 3 sections specify the 3 different parameters of this GET
request.

`GET` /traits?name=starts_with:{prefix}
***************************************

To query the traits whose name begines with a specific prefix, use
`starts_with` operator with the query parameter `name`. For example, you can
query all the custom traits by filtering the traits with `CUSTOM` prefix.

Example::

    GET /traits?name=starts_with:CUSTOM

The response::

    200 OK
    Content-Type: application/json

    {
        "traits": [
            "CUSTOM_TRAIT_1",
            "CUSTOM_TRAIT_2"
        ]
    }

`GET` /traits?associated={True|False}
*************************************

To query the traits that have been associated with at least one resource
provider in the placement service, use the parameter `associated` to filter
them out.

`GET` /traits?name=in:a,b,c
***************************

Return the traits listed with the in: parameter that exist in this cloud.

For example, when admin-user creates flavor specifing trait strings, Nova can
get a list of which of these traits are defined in the deployment using the
example below::

    GET /traits?name=in:HW_CPU_X86_AVX,HW_CPU_X86_SSE,HW_CPU_X86_INVALID_FEATURE

Its response::

    200 OK
    Content-Type: application/json

    {
        "traits": [
            "HW_CPU_X86_AVX",
            "HW_CPU_X86_SSE"
        ]
    }

.. note::

    `HW_CPU_X86_INVALID_FEATURE` isn't a valid trait in the cloud, so it won't
    be included in the response. Nova can thus be aware of invalid traits and
    provide an informative response to users.

`GET` /traits/{trait_name}
**************************

This API is to check if a trait name exists in this cloud.

The returned response will be one of the following:

* `204 No Content` if the trait name exists.
* `404 Not Found` if the trait name does not exist.

`PUT` /traits/{trait_name}
**************************

This API is to insert a single custom trait without having to send the entire
trait list::

    PUT /traits/CUSTOM_TRAIT_1

Its response includes the new trait's URL in the `Location` header::

    Location: traits/CUSTOM_TRAIT_1

The returned response will be one of the following:

* `201 Created` if the insertion is successful.
* `204 No Content` if the trait already exists.
* `400 BadRequest` if trait name sn't prefixed with `CUSTOM_` prefix.
* `409 Conflict` if trait name conflicts with standard trait name.

`DELETE` /traits/{trait_name}
*****************************

This API is to delete the specified trait. Note that only custom traits can be
deleted.

The returned response will be one of the following:

* `204 No Content` if the removal is successful.
* `400 BadRequest` if the name to delete is standard trait.
* `404 Not Found` if no such trait exists.
* `409 Conflict` if the name to delete has associations with any
  ResourceProvider.

`GET` /resource_providers/{uuid}/traits
***************************************

Return the trait list provided by specific resource provider.

The response format is the similar with `GET /traits`, but with
`resource_provider_generation` in the body.

Example::

    200 OK
    Context-Type: application/json

    {
        "traits": [
            "HW_CPU_X86_3DNOW",
            "HW_CPU_X86_ABM",
            ...
            "CUSTOM_TRAIT_1",
            "CUSTOM_TRAIT_2"
        ],
        "resource_provider_generation": 3
    }

The returned response will be one of the following:

* `200 OK` if query is successful.
* `404 Not Found` if the resource provider identified by `{uuid}` is not found.

`PUT` /resource_providers/{uuid}/traits
***************************************

This API is to associate traits with specified resource provider. All the
associated traits will be replaced by the traits specified in the request body.
Nova-compute will report the compute node traits through this API.

The body of the request must match the following JSONSchema document::

    {
        "type": "object",
        "properties": {
            "traits": {
                "type": "array",
                "items": CUSTOM_TRAIT
            },
            "resource_provider_generation": {
                "type": "integer"
            }
        },
        'required': ['traits', 'resource_provider_generation'],
        'additionalProperties': False
    }

Example::

    PUT /resource_providers/508f3973-8e1a-4241-afec-ee3e21be0611/traits

    Content-type: application/json

    {
        "traits": [
            "CUSTOM_TRAIT_1",
            "CUSTOM_TRAIT_2"
        ],
        "resource_provider_generation": 112
    }

The successful HTTP will list the changed traits in the same format of GET
response. The returned response will be one of the following:

* `200 OK` if the update is successful.
* `400 Bad Request` if any of the specified traits are not valid. The valid
  traits can be queried by `GET /traits`.
* `404 Not Found` if the resource provider identified by `{uuid}` is not found.
* `409 Conflict` if the `resource_provider_generation` doesn't match with the
  server side.

`DELETE` /resource_providers/{uuid}/traits
******************************************

This API is to dissociate all the traits for the specific resource provider.

The returned response will be one of the following:

* `204 No Content` if the delete is successful.
* `404 Not Found` if the resource provider identified by `{uuid}` is not found.

Security impact
---------------

None

Notifications impact
--------------------

None

Other end user impact
---------------------

There will be a set of CLI commands for users to query and manage the Traits.

* openstack trait list [--starts-with {prefix}] [--name-in {name1},{name2}]
* openstack trait remove $TRAIT
* openstack trait add $TRAIT

Performance Impact
------------------

None

Other deployer impact
---------------------

* Deployers will need to set the traits for resources that aren't managed by
  OpenStack, such as the shared storage pools which used by compute node
  storage, as this will not be done automatically by any OpenStack service.
* Deployers will need to start using traits instead of aggregate metadata for
  managing qualitative information in anticipation of aggregate metadata being
  deprecated.
* The `os-traits` library in the placement service needs to be the latest
  version in the cloud, otherwise the new traits reported from other OpenStack
  services won't be recognized by Placement service. So when upgrade the cloud
  to involve the new traits, the `os-traits` library in the placement service
  need to be upgraded first.
* The deployer needs to run command `placement-manage os-trait sync` before
  starting the placement or new `os-traits` released to ensure the new traits
  are imported into the placement DB.

Developer impact
----------------

Only developers working on the Scheduler and/or Placement API will have to be
aware of these changes.

Implementation
==============

Assignee(s)
-----------

Primary assignee:
  Alex Xu <hejie.xu@intel.com>

Other contributors:
  Cheng, Yingxin <yingxin.cheng@intel.com>
  Jin, Yuntong <yuntong.jin@intel.com>
  Tan, Lin <lin.tan@intel.com>
  Ed Leafe <ed@leafe.com>

Work Items
----------

* Add DB Schema for Traits
* Refactor the ResourceClassCache to be utilized by Traits
* Add Traits related object
* Implement the API for managing custom traits
* Enable to attach traits to the resource provider in object
* Implement the API for setting traits on the resource providers
* Add new cmd `placement-manage os-traits sync`

Dependencies
============

This proposal also depends on the `os-traits` library. This proposal uses
`os-traits` to query standard traits.

Testing
=======

Unit and functional tests should be added to ensure the Traits API works.

Documentation Impact
====================

The API docs should be added for the Traits API. The
Administrator docs should be added to explain how to use Traits API
to manage capabilities.

References
==========

Maillist discussion:
http://lists.openstack.org/pipermail/openstack-dev/2016-July/099032.html

Tags API-WG guideline:
http://specs.openstack.org/openstack/api-wg/guidelines/tags.html

.. _Tags API-WG guideline: http://specs.openstack.org/openstack/api-wg/guidelines/tags.html

Simple Resource Provision:
https://anticdent.org/simple-resource-provision.html

.. _Simple Resource Provision: https://anticdent.org/simple-resource-provision.html

Use ResourceProviderTraits instead of ResourceClass
http://lists.openstack.org/pipermail/openstack-dev/2016-August/100634.html

.. _Use ResourceProviderTraits instead of ResourceClass: http://lists.openstack.org/pipermail/openstack-dev/2016-August/100634.html

.. _The concern of multiple version of os-traits library in the cloud: http://lists.openstack.org/pipermail/openstack-dev/2016-August/101637.html

History
=======

.. list-table:: Revisions
   :header-rows: 1

   * - Release Name
     - Description
   * - Ocata
     - Introduced
