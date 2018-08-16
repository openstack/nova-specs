..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

==========================================
Support disabling a cell
==========================================

https://blueprints.launchpad.net/nova/+spec/cell-disable

It would be useful to have a mechanism by which we could totally stop
scheduling to a particular cell or a group of cells by supporting the concept
of disabling cells. Given that we do not have any existing means to disable a
cell, this spec proposes a simple solution to support this new feature in nova.

Problem description
===================

Currently we have a number of ways to pre-select cells into which we want the
VMs to be scheduled into, like using host aggregates or scheduler filters.
These mechanisms however are white listing and selecting suitable hosts by
which we are indirectly able to pre-select a cell. So although we have ways to
remove undesired hosts from being selected for scheduling, large deployments
may not always want to engage on a host-level. If they want to just stop
scheduling to a set of cells, presently they would somehow have to exclude all
the hosts in those cells from being considered by the scheduler since there is
no way to simply black list those set of cells.

So the problem that this spec is trying to address is the fact that there is
no elegant way to block scheduling to a group of cells.

Use Cases
---------

As an operator, I wish to disable a group of cells (like during failures or
interventions when new instances should not be spawned) so as to stop
scheduling to them without having to deal with the individual compute nodes
(micromanagement).

Proposed change
===============

This spec aims to make a change in the ``nova_api.cell_mappings`` table schema
and add a new field to the ``CellMapping`` object through which the
host_manager of the scheduler will become aware of the cells which are
disabled and there by not query for those compute nodes and services which
belong to the disabled cells while getting the host states of the hosts
returned by placement to the scheduler. A detailed procedure of how this is
aimed to be implemented is explained below:

#. Add a new column ``disabled`` to the nova_api.cell_mappings table which can
   be set to either True or False for each record. Setting it to True means
   that cell is disabled; and so by default this value will be set to False.
#. Add a new field ``disabled`` to the CellMapping object which will represent
   the value of the newly added column in the cell_mappings table.
#. Add a query method to CellMappingList object, to query for only the enabled
   cells.
#. Presently the scheduler calls the host_manager to get_host_states_by_uuids
   and the host_manager queries for the compute_nodes and services in the cells
   by calling _get_computes_for_cells from get_host_states_by_uuids function.
   While loading the cells in the get_host_states_by_uuids function, the
   disabled cells will be filtered out and only the enabled cells will be
   passed to the _get_computes_for_cells function by using the new query added
   to CellMappingList. Hence only the states of hosts in the enabled cells will
   be passed back to the filter scheduler so that no scheduling happens to the
   disabled cells.
#. Since the list of cells are currently cached globally (better performance)
   after every enabling/disabling action of any cell, this cache will be
   refreshed so that the new changes are reflected. The refreshing will be done
   using a "SIGHUP" handler that will be created in the scheduler and a signal
   to this handler will be made during the change to disabled column.

Since we have the nova-manage utility for the operators the nova-manage
command to update the fields in the cell_mappings table can be reused in the
following manner, thus allowing the operator to enable/disable a cell.

* Add new flags to ``nova-manage cell_v2 update_cell`` command -

  * ``nova-manage cell_v2 --update_cell --cell_uuid <cell_uuid> [--disable]``
      which will disable an enabled cell, meaning set the ``disabled`` field of
      this cell's cell_mapping record in the api DB to 1.
  * ``nova-manage cell_v2 --update_cell --cell_uuid <cell_uuid> [--enable]``
      which will enable a disabled cell, meaning set the ``disabled`` field of
      this cell_mapping record back to 0.

When creating a new cell, by default the cell will be in enabled state, however
an option ``disabled`` will be added to the ``nova-manage cell_v2 create_cell``
command by which the users will be able to create pre-disabled cells which can
be enabled later whenever needed.

Also the disabled column will be added to the list of columns to be displayed
using the ``nova-manage cell_v2 list_cells`` command since it will be useful
for the operators.

The scope of this spec is limited to considering the scenario of using a filter
scheduler since that is the maintained scheduler. Also note that this spec only
focuses on stopping new scheduling to the disabled cells and does not hamper
any user operations for existing VMs in the disabled cells like resizing. For
example, even if the RequestSpec.request_destination.cell is set to a disabled
cell this operation will not be blocked.

Alternatives
------------

#. This could also be implemented as a post-placement filter enabled through
   a config boolean in the scheduler to filter out disabled cells, but since
   this would anyways still need a new field in cell_mappings, it would be more
   integrated if this is implemented through a simple change in query in the
   host_manager.
#. Another alternative would be loop through all the compute services in that
   cell and enable/disable them, but this may not be ideal in cases of cells
   having large number of computes.

Data model impact
-----------------

A nova_api DB schema change will be required for adding the ``disabled`` column
of type Boolean to the ``nova_api.cell_mappings`` table. An api_migration will
be required. This column will be set to False by default.

Also, the ``CellMapping`` object will need to gain a new field called
``disabled``.

REST API impact
---------------

None.

Security impact
---------------

None.

Notifications impact
--------------------

None.

Other end user impact
---------------------

Users will gain two new options to the existing ``nova-manage cell_v2
update_cell`` command called ``disable`` and ``enable`` plus a new option
``disabled`` to the existing ``nova-manage cell_v2 create_cell`` command. The
documentation will be updated to benefit the users.

Performance Impact
------------------

There will not be any major impact on performance. Instead of the scheduler
querying for all the cells to get the host states it will query for only
enabled cells.

Other deployer impact
---------------------

There will not be any impact on the deployer operations since by default all
the cells will be enabled and scheduling will work normally. Supporting cell
disable will only make it more agile since the deployer can now block
scheduling to a group of cells, rather than involving in micromanagement of
services, meaning individually tend to each service in those cells by filtering
them out or disabling each compute service in that cell.

Developer impact
----------------

None

Upgrade impact
--------------

Since there will be a change in the api DB schema, the ``nova-manage api_db
sync`` command will have to be run to update the cell_mappings table.

Implementation
==============

Assignee(s)
-----------

Primary assignee:
  <tssurya>

Other contributors:
  <belmoreira>

Work Items
----------

#. Add a new column ``disabled`` to nova_api.cell_mappings table.
#. Add a new field ``disabled`` to CellMapping object.
#. Add a query method to CellMappingList to obtain all the cell mapping
   records of enabled cells.
#. Change the method of querying for the host states in the host_manager to
   only query in the enabled cells and add a SIGHUP handler.
#. Add the new flags to the nova-manage cell_v2 update_cell command.
#. Add the new flag to the nova-manage cell_v2 create_cell command.
#. Modify the nova-manage cell_v2 list_cells command to print the new column.

Dependencies
============

None.


Testing
=======

#. Unit and functional tests for verifying the working of the disabling
   mechanism


Documentation Impact
====================

The nova-manage documentation for the users would be updated by documenting
the new flags for the ``nova-manage cell_v2 update_cell`` command and
``nova-manage cell_v2 create_cell`` command in nova-manage.rst file.

References
==========

None.

History
=======

.. list-table:: Revisions
   :header-rows: 1

   * - Release Name
     - Description
   * - Rocky
     - Introduced
