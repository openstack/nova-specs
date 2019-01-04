..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

=====================================
Enable Rebuild for Instances in cell0
=====================================
https://blueprints.launchpad.net/nova/+spec/enable-rebuild-for-instances-in-cell0

This spec summarizes the changes needed to enable the rebuilding of instances
that failed to be scheduled because there were not enough resources.

Problem description
===================

Presently, it is allowed to rebuild servers in ERROR state, as long as they
have successfully started up before. But if a user tries to rebuild an instance
that was never launched before because scheduler failed to find a valid host
due to the lack of available resources, the request fails with an exception of
type ``InstanceInvalidState``. We are not addressing the case were the server
was never launched due to exceeding the maximum number of build retries.

Use Cases
---------

#. As an operator I want to be able to perform corrective actions after a
   server fails to be scheduled because there were not enough resources (i.e.
   the instance ends up in PENDING state, if configured). Such actions could
   be adding more capacity or freeing up used resources. Following the
   execution of these actions I want to be able to rebuild the server that
   failed.

   NOTE::
   Adding the PENDING state as well as setting instances to it, are out of the
   scope of this spec, as they are being addressed by another change[1].

Proposed change
===============

The flow of the rebuild procedure for instances mapped in cell0 because of
scheduling failures caused by lack of resources would then be like this:

#. The nova-api, after identifying an instance as being in cell0, should create
   a new BuildRequest and update the instance mapping.

#. At this point the api should also delete the instance records from cell0 DB.
   If this is a soft delete, then after the successful completion of the
   operation, we would end up with one record of the instance in the new cell's
   DB and a record of the same instance in cell0 (deleted=True). A better
   approach, here, would be to hard delete the instance's information from
   cell0. While rebuilding the instance and before deleting it from cell0,
   a user could try to update it (i.e. its metadata, tags, etc). We, then,
   might end up in race and those changes end up not making it across to the
   new cell. Although, the window, for this, is really small, we have to metion
   it here.

#. Then the nova-api should make an RPC API call to the conductor's new method
   ``rebuild_instance_in_cell0``. This new method's purpose is almost (if not
   exactly) the same as the existing ``schedule_and_build_instances``. So we
   could either call to it internally or extract parts of it's functionality
   and reuse them.

#. Finally, an RPC API call is needed from the conductor to the compute
   service of the selected cell. The ``rebuild_instance`` method tries to
   destroy an existing instance and then re-create it. In this case and since
   the instance was in cell0, there is nothing to destroy and re-create. So,
   an RPC API call to the existing method ``build_and_run_instance`` seems
   appropriate.

The only problem is that when an instance fails during build, its network_info
field is empty. Currently there is no way to recover the requested networks
while trying to rebuild the instance. So the NetworkRequestList object
should be stored while building the server.

For this:

#. A reasonable change would be to extend the RequestSpec object to adding a
   requested_networks field, where the requested networks will be stored. Note
   here that the requested networks will be stored in the RequestSpec only when
   an instance fails during scheduling and is mapped to cell0. As soon as the
   rebuild procedure starts and the requested networks are retrieved, the new
   field will be set to None.

#. While building the server and when creating the request specification, we
   should add the list of requested networks in the RequestSpec's
   requested_networks field.

Alternatives
------------

None.

Data model impact
-----------------

Add a `requested_networks` field in the RequestSpec object that will contain a
NetworkRequestList object. Since the RequestSpec is stored as a blob
(mediumtext) in the database, no schema modification is needed.

REST API impact
---------------

A new API microversion is needed. Rebuilding an instance that is mapped to
cell0 will continue to fail for older microversions.

Security impact
---------------

None.

Notifications impact
--------------------

None.

Other end user impact
---------------------

Users will be allowed to rebuild instances that failed due to the lack of
resources.

Performance Impact
------------------

None.

Other deployer impact
---------------------

None.

Developer impact
----------------

None.

Upgrade impact
--------------

None.

Implementation
==============

Assignee(s)
-----------

Primary assignee:
  <ttsiouts>

Other contributors:
  <johnthetubaguy>
  <strigazi>
  <belmoreira>

Work Items
----------

See `Proposed change`_.

Dependencies
============

None.

Testing
=======

#. Unit and functional tests have to be added to verify the rebuilding of
   instances in cell0.

Documentation Impact
====================

We should update the documentation to state that the rebuild is allowed for
instances that have never booted before.

References
==========

[1] Add PENDING vm state

* https://review.openstack.org/#/c/554212/

Discussed at the Dublin PTG:

* https://etherpad.openstack.org/p/nova-ptg-rocky (#L459)

History
=======

.. list-table:: Revisions
   :header-rows: 1

   * - Release Name
     - Description
   * - Rocky
     - Introduced
   * - Stein
     - Re-proposed
