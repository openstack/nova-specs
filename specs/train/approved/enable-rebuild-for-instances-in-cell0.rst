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
type ``InstanceInvalidState`` [#]_. We are not addressing the case where the
server was never launched due to exceeding the maximum number of build retries.

Use Cases
---------

#. As an operator I want to be able to perform corrective actions after a
   server fails to be scheduled because there were not enough resources (i.e.
   the instance ends up in PENDING state, if configured). Such actions could
   be adding more capacity or freeing up used resources. Following the
   execution of these actions I want to be able to rebuild the server that
   failed.

.. note:: Adding the PENDING state as well as setting instances to it, are out
          of the scope of this spec, as they are being addressed by another
          change [#]_.

Proposed change
===============

The flow of the rebuild procedure for instances mapped in cell0 because of
scheduling failures caused by lack of resources would then be like this:

#. The nova-api, after identifying an instance as being in cell0, should create
   a new BuildRequest and update the instance mapping (cell_id=None).

#. At this point the api should also delete the instance records from cell0 DB.
   If this is a soft delete [#]_, then after the successful completion of the
   operation, we would end up with one record of the instance in the new cell's
   DB and a record of the same instance in cell0 (deleted=True). A better
   approach, here, would be to hard delete [#]_ the instance's information from
   cell0.

#. Then the nova-api should make an RPC API call to the conductor's new method
   ``rebuild_instance_in_cell0``. This new method's purpose is almost (if not
   exactly) the same as the existing ``schedule_and_build_instances``. So we
   could either call to it internally or extract parts of it's functionality
   and reuse them. The reason behind this is mainly to avoid calling schedule
   and build code in the super-conductor directly from rebuild code in the API.

#. Finally, an RPC API call is needed from the conductor to the compute
   service of the selected cell. The ``rebuild_instance`` method tries to
   destroy an existing instance and then re-create it. In this case and since
   the instance was in cell0, there is nothing to destroy and re-create. So,
   an RPC API call to the existing method ``build_and_run_instance`` seems
   appropriate.

Information provided by the user in the initial request such as keypair,
trusted_image_certificates, BDMs, tags and config_drive can be retrieved from
the instance buried in cell0.
Currently, there is no way to recover the requested networks while trying to
rebuild the instance. For this:

#. A reasonable change would be to extend the RequestSpec object to adding a
   requested_networks field, where the requested networks will be stored.

#. When scheduler fails to find a valid host for an instance and the VM goes to
   cell0, the list of requested networks will be stored in the RequestSpec.

#. As soon as the rebuild procedure starts and the requested networks are
   retrieved, the new field will be set to None.

The same applies for personality files, that can be provided during the initial
create request and since microversion 2.57 it is deprecated from the rebuild
API [#]_. Since the field is not persisted we have no way of retrieving them
during rebuild from cell0. For this we have a couple of alternatives:

#. Handle personality files as requested networks and persist them in the
   RequestSpec.

#. Document this as a limitation of the feature and that if people would like
   to use the new rebuild functionality they should not use personality files.

#. Another option would be to track in the ``system_metadata`` of the instance,
   if the instance was created with personality files. Then during rebuild from
   cell0, we could check and not accept the request for instances created with
   personality files.

There is an ongoing discussion on how to handle personality files in the
mailing list [#]_.

Quota Checks
------------

During the normal build flow, there are quota checks in the API level [#]_ as
well as in the conductor level [#]_. Consider the scenario where a user has
enough RAM quota for a new instance. As soon as the instance is created, it
ends up in cell0 because the scheduling failed.

There are two distinct cases when checking quota for instances, cores, ram:

#. Checking quota from Nova DB

   In this case, the instance's resources, although in cell0, will be
   aggregated since the instance records will be in the DB. There is though
   a slight window for a race condition when the instance gets hard deleted.

#. Checking quota from Placement [#]_

   When the instance is in cell0, there are no allocations to Placement for
   this consumer. Meaning that the instance's resources will not be aggregated
   during subsequent checks and there is no check in the API level when
   rebuilding.

Rechecking quota at the conductor level will make sure that user's quota is
enough before proceeding with the build procedure.

Between initial build and rebuild (from cell0) port usage might have changed.
In this case and since port quota is not checked when rebuilding from cell0, we
might fail late in the compute service trying to create the port. Although the
user will not get a quick failure from the API, this is acceptable because at
this point usage is already over limit and the server would not have booted
successfully.

Alternatives
------------

The user could delete the instance that failed and create a new one with the
same characteristics but not the same ID. The proposed functionality is the
dependency for supporting preemptible instances, where an external service
automatically rebuilds the failed server after taking corrective actions. In
the aforementioned feature maintaining the ID of the instance is of vital
importance. This is the main reason for which this cannot be considered as an
acceptable alternative solution.

Data model impact
-----------------

Add a ``requested_networks`` field in the RequestSpec object that will contain
a NetworkRequestList object. Since the RequestSpec is stored as a blob
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

In order to verify the validity of the functionality:

#. New unit tests have to be implmented and existing ones should be adapted.

#. New functional tests have to be implemented to verify the rebuilding of
   instances in cell0 and the handling of instance tags, keypairs,
   trusted_image_certificates etc.

#. The new tests should take into consideration BFV instances and the handling
   of BDMs.

Documentation Impact
====================

We should update the documentation to state that the rebuild is allowed for
instances that have never booted before.

References
==========

.. [#] https://github.com/openstack/nova/blob/d42a007425d9adb691134137e1e0b7dda356df62/nova/compute/api.py#L147

.. [#] https://review.openstack.org/#/c/648687/

.. [#] In this scope soft delete means a non-zero value is set to the
       ``deleted`` column.

.. [#] Hard delete means that the record is removed from the table.

.. [#] https://docs.openstack.org/nova/latest/reference/api-microversion-history.html#id52

.. [#] http://lists.openstack.org/pipermail/openstack-discuss/2019-April/004901.html

.. [#] https://github.com/openstack/nova/blob/fc3890667e4971e3f0f35ac921c2a6c25f72adec/nova/compute/api.py#L937

.. [#] https://github.com/openstack/nova/blob/fc3890667e4971e3f0f35ac921c2a6c25f72adec/nova/conductor/manager.py#L1422

.. [#] https://review.opendev.org/#/c/638073/

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
   * - Train
     - Re-proposed
