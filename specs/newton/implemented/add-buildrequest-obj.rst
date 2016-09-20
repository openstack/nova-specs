..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

=========================
Add a BuildRequest object
=========================

https://blueprints.launchpad.net/nova/+spec/add-buildrequest-obj

In order to maintain the API contract when using cells we need to store enough
information to fulfill an instance show request.


Problem description
===================

When an API request is made to build an instance there is a certain response
contract that we need to honor.  This means that we need to have stored certain
information from the request such as image, flavor, name, uuid, etc...  In a
cellsv2 setup this poses a challenge because that would currently be stored in
the instance table, but we don't know which cell instance table to put it in
yet.


Use Cases
----------

* Operators want to partition their deployments into cells for scaling, failure
  domain, and buildout reasons.  When partitioned, we need to maintain the
  current API contract.


Proposed change
===============

A new object will be added which will have a RequestSpec object as a field, and
all additional details needed for an instance show as other fields.

A new table will be added to the api database to store the fields which are not
in the RequestSpec.

Alternatives
------------

The RequestSpec object could be expanded to hold all of this data.  That would
bloat an object whose purpose is to inform scheduling decisions with
unnecessary data for that task.

An instance table could be added to the api database.  This is similar to
what's being proposed here, but could lead to confusion because of its
temporary nature.  The BuildRequest object will look much like an instance, but
it will be clear that it's not actually *the* instance.

Data model impact
-----------------

A new table will be added to the 'nova_api' database for storing the
BuildRequest fields.  The table will need to store things like
availability_zone, power_state, task_state, uuid, key_name, metadata,
security_groups, etc...  These items will be stored as a versioned dict of the
fields necessary.

The table will look like:::

    CREATE TABLE `build_request` (
      `created_at` datetime DEFAULT NULL,
      `updated_at` datetime DEFAULT NULL,
      `id` int(11) NOT NULL AUTO_INCREMENT,
      `instance_uuid` varchar(36) NOT NULL,
      `project_id` varchar(255) NOT NULL,
      `request_obj` text NOT NULL
    )

instance_uuid and project_id would be indexed.

Once the instance has been written to a cell database this entry should be
deleted as the show request can then be fulfilled from the instance table.
This means that this data is short lived so future changes can be made with few
concerns about backwards compatibility.


REST API impact
---------------

None

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

An additional database write will be incurred.

Other deployer impact
---------------------

Instances that have not been scheduled yet will exist in this new table.
Deployers will need to be aware of this to aid proper debugging.

Developer impact
----------------

None


Implementation
==============

Assignee(s)
-----------

Primary assignee:
  alaski

Other contributors:
  None

Work Items
----------

 * Have nova-api write BuildRequest info to this table

 * Have nova-api respond to list/show requests with the BuildRequest object if
   the instance has not yet been mapped to a cell.

 * After the instance has been created in the cell database (covered in the
   scheduler interaction spec) remove this database row.

Dependencies
============

None


Testing
=======

Since this is designed to be an internal re-architecting of Nova with no user
visible changes the current suite of Tempest or functional tests should
suffice.  At some point we will want to look at how to test multiple cells or
potentially exposing the concept of a cell in the API and we will tackle
testing requirements then.


Documentation Impact
====================

Documentation will be written describing the flow of an instance build and how
this affects it.


References
==========

``https://etherpad.openstack.org/p/kilo-nova-cells``
``https://etherpad.openstack.org/p/nova-cells-scheduling-requirements``


History
=======

.. list-table:: Revisions
   :header-rows: 1

   * - Release Name
     - Description
   * - Liberty
     - Introduced
   * - Mitaka
     - partially implemented.
   * - Newton
     - Re-proposed.
