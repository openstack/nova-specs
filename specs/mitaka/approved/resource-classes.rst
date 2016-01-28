..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

===============================================
Resource providers - Introduce resource classes
===============================================

https://blueprints.launchpad.net/nova/+spec/resource-classes

This blueprint introduces a mechanism for representing the types of
quantitative resources that may be provided by the system.

Problem description
===================

The types of quantitative resources that are exposed in Nova are currently
hard-coded into various places in the code base. For instance, on the
`Instance` object, we store the amount of requested vCPUs in the `vcpus` field
and the amount of RAM in the `memory_mb` field. We have a separate
`instance_pci_devices` table in the database for PCI resource types. We store
the NUMA-related resource information in a field in a different table, etc.

Whenever we come up with a new class of resources that we wish to provide, we
end up creating either a new field in a table or a whole new database table for
this new resource type. Any time we make changes to the database schema, we
introduce some amount of downtime to the system. These changes, however, are
not necessary. We should be able to add new resource classes to the system
without changes to the database schema, and this series of blueprints lay the
groundwork for doing just that.

This work will also enable us to have a generic resource pool system that does
not hard-code resource classes into database field names. Instead of a system
where we have a table tracking just shared disk storage, we can have a database
table that can be used for tracking many different types of resources, and the
schema of this table will not need to change when we add support for more types
of shared resources.

Use Cases
---------

As a cloud deployer, I wish to reduce the downtime experienced by database
schema changes when a new type of resource (or a new way of handling an
existing type of resource) is added to the system.

Proposed change
===============

We propose to add a new Nova object field type called `ResourceClassField` that
derives from the `nova.objects.fields.EnumType` object. The `ALLOWED` values of
this field will be a set of agreed-upon constants. We do not propose adding
operator extensibility of this list of constants, because we do not want to
encourage situations where two OpenStack clouds have different definitions of
the same-named resource class.

Alternatives
------------

We could continue doing things the way we have been doing, adding new schema
fields or new schema tables each time we add a new class of resources that the
system provides.

Data model impact
-----------------

A new nova object field type for resource classes will be introduced.

Initially, however, we can populate the enum with the known resource classes
in the system:

* `VCPU`
* `MEMORY_MB`
* `DISK_GB`
* `PCI_DEVICE`
* `SRIOV_NET_VF`
* `NUMA_SOCKET`
* `NUMA_CORE`
* `NUMA_THREAD`
* `NUMA_MEMORY_MB`
* `IPV4_ADDRESS`

REST API impact
---------------

None at this time. In the future, we may wish to allow a cloud user to query
the resource classes via HTTP, but initially I don't believe this is necessary.

Security impact
---------------

None.

Notifications impact
--------------------

None.

Other end user impact
---------------------

Future work can introduce a `nova resource-class-list` command, however this is
not particularly important for this blueprint spec.

Performance Impact
------------------

None introduced in this blueprint since we are only adding a set of constants
in an Enum-like field type.

Other deployer impact
---------------------

None.

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

* Create new `nova.objects.fields.ResourceClassField` nova field

Dependencies
============

None.

Testing
=======

Unit testing should be sufficient for this small blueprint spec. Functional and
integration testing is more appropriate for the specs like
`generic-resource-pools` that build on top of this work.

Documentation Impact
====================

None.

References
==========

* `generic-resource-pools` specification:

  https://review.openstack.org/#/c/253187

History
=======

.. list-table:: Revisions
   :header-rows: 1

   * - Release Name
     - Description
   * - Mitaka
     - Introduced
