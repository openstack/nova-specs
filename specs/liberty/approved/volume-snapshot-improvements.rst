..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

==========================================
Volume snapshot improvements
==========================================

https://blueprints.launchpad.net/nova/+spec/volume-snapshot-improvements

This spec covers a few updates to the volume snapshot create and delete
operations in the libvirt volume driver.  These are needed to fix up
some issues in Nova/Cinder related to volume file format handling and
API cleanup.


Problem description
===================

Nova does not currently pass enough information back to Cinder when
manipulating snapshot files.  Cinder needs to keep track of the format
of each file (raw, qcow2, vhd, etc.) to maintain security and data
integrity.  Currently it has to guess about the outcome of a snapshot
operation for this information.

Nova currently sends a hard-coded '90%' progress value to indicate a
state transition at the end of a snapshot operation.  This should be
replaced with something more generic that does not overload the
progress field.


Use Cases
----------

Deployer: Currently if a user writes a qcow2 header into a volume on
certain Cinder volume drives, the volume may be marked as unusable.  This
work will fix things so that Cinder can avoid having to invalidate
volumes in this scenario.

Deployer: Increased (theoretical) security since Cinder doesn't have
to use heuristics for the above check.

Developer: API between Cinder and Nova becomes more clear (no magic
progress value)


Project Priority
-----------------

None. This is primarily a maintainablity/reliability issue.

Proposed change
===============

File format tracking
--------------------

Each time a volume snapshot create or delete operation occurs,
add file format information about the changed files to the status
update sent back to Cinder.  (This is currently only used in the
libvirt volume driver for file-based volume drivers but nothing
prevents it from being more general.)

For the libvirt volume driver, this information can be obtained by
querying the instance VM's disk backing chain information via
the domain.XMLDesc() output.

For snapshot_create, determine the format of the new file, return
this from _volume_snapshot_create() and add a dict such as::
'file_format': { 'volume-1234.snapshot-abcd': 'qcow2' }
to the _volume_update_snapshot_status() call.

For snapshot_delete, determine the format of merge_target_file,
or if that is None, file_to_merge, after the snapshot delete,
and add that information to the _volume_update_snapshot_status()
call::
'file_format': { 'volume-1234': 'qcow2' }

There may be some cases with old versions of libvirt where this
information isn't explicitly given in the domain information.  We
can make assumptions in these cases for what format to return based
on knowing that performing a blockCommit results in the format of
the file being committed to, and a blockRebase results in the format
of the file being pulled to.

Progress Updating
-----------------
For Liberty, continue to send the 'progress': '90%' flag in
update_snapshot_status for compatibility.  (Can be removed in the future.)

Send a new status of 'creating_compute_complete' to indicate that
the compute service is done with its portion of the create process.
Cinder will translate this to a relevant volume state transition
on its side.

Same as above for deleting, with 'delete_compute_complete'.

This allows Cinder to distinguish whether Nova is currently processing
information or whether Cinder has control of that snapshot again.

Alternatives
------------

Leave things as they are (not really desirable).

Data model impact
-----------------

None

REST API impact
---------------

None

Security impact
---------------

There was a security issue in the Juno timeframe in this area which
was patched up enough to make it safe.  This completes that effort
by making the system fully robust rather than just patched up.
[ref OSSA 2014-033]

This will bring Nova and Cinder to always track and use knowledge of
the file format of each volume/snapshot file.


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

None

Developer impact
----------------

None


Implementation
==============

Assignee(s)
-----------

Primary assignee:
  deepakcs

Other contributors:
  None

Work Items
----------

* Add new file format querying and reporting to libvirt snapshot code
* Add new statuses to libvirt snapshot create/delete operations
* Test with Cinder (where most of this change really has an effect)


Dependencies
============

* Cinder changes (format): https://review.openstack.org/#/c/165393/
* Cinder changes (status): https://review.openstack.org/#/c/172373/

Testing
=======

This change most directly impacts the Cinder GlusterFS, NFS, and SMBFS
drivers for Liberty.  These will have CI running tempest for Liberty, which
will validate this work.



Documentation Impact
====================

None


References
==========

* OSSA 2014-033 https://bugs.launchpad.net/cinder/+bug/1350504
* Cinder changes (format): https://review.openstack.org/#/c/165393/
* Cinder changes (status): https://review.openstack.org/#/c/172373/
