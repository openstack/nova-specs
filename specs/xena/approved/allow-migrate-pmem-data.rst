..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

===================================
Allow migrating PMEM's data
===================================

https://blueprints.launchpad.net/nova/+spec/allow-migrate-pmem-data

This spec proposes an method for migrating PMEM Namespace's data of instance
when cold migrating or resizing instance.

Problem description
===================

Currently, cold migrate or resize instance will always select a new pmem
namespace on the destination host. But the data of the instance in the PMEM
device will be lost. To ensure the integrity of instance data， we would like
to migrate PMEM's data of the instance when migrate or resize an instance.

PMEM devices can be used as a large pool of low latency high bandwidth memory
where they could store data for computation. This can improve the performance
of the instance.

Since copying pmem data will take a lot more time and network bandwidth, a new
"copy_pmem_devices" argument is added to decide whether to copy pmem data.


Use Cases
---------
* As an user, I would like to migrate the PMEM namespace's data if the instance
  migrate or resize to another host to ensure data integrity.

Proposed change
===============
Add a new microversion migrate / resize API, introducing "copy_pmem_devices"
field.

When migrating or resizing intance, we can get the old PMEM device and the new
PMEM device from `instance.migration_context`. So we can copy the data from old
PMEM device to new PMEM device.

Given or Assuming, the instance use /dev/dax0.0 PMEM Namespace on the source
host, and we want to migrate or resize it to other host, and migrating or
resizing the instance, will use the /dev/dax0.1 PMEM namepsace on the target
host.
Then nova will migrate the PMEM namepace's data of the instance from
/dev/dax0.0 to /dev/dax0.1 using the daxio utility over an ssh tunnel.

Workflow
--------
cold migrating or resizing instance workflow as following:

1. prep_resize validates that there is a pmem device free and claims it as
   part of the move_claim process.The claimed device is stored in the
   instance.migration_context which can be retrieved later.

2. The resize_instance operation is on source_compute, free the network volume
   etc. resources. We can get the source compute, dest compute from migration,
   and get the new PMEM device, old PMEM device from
   instance.migration_context. Copy the PMEM data from old PMEM device to new
   PMEM device at migtate_disk_and_power_off. If the copy operation is failed,
   cleanup the PMEM data on dest_compute, and make the instance ACTIVE again
   on the source compute. Copy the PMEM data can use "daxio" and "ssh".

3. The finish_resize operation is on dest_compute, launching a new instance
   with resources in step1. If launching new instance failed, will terminate
   the operation, cleanup the PMEM data on dest_compute, and make the instance
   ACTIVE again on the source compute.

4. The confirm_migration will cleanup PMEM data on source compute, alternitivly
   revert_resize will cleanup PMEM data on dest compute and  make the instance
   ACTIVE again on the source compute.

Alternatives
------------
None


Data model impact
-----------------
None


REST API impact
---------------
Add a new microversion migrate / resize API with "copy_pmem_devices" field.

* POST /servers/{server_id}/action
  {

      "resize" : {
          "flavorRef" : "2",
          "OS-DCF:diskConfig": "AUTO",
          "copy_pmem_devices": "true"

      }

  }

  {

      "migrate": {
          "host": "host1",
          "copy_pmem_devices": "true"

    }

  }

The value of "copy_pmem_devices" default "false", dosen't copy pmem data.
"true", the data in virtual persistent memory is copied.

If the copy_pmem_devices=true and the old microverion return a 400. Cross cell
resize/cold migrate, will return 400.

Security impact
---------------
The pmem data will be transfered over ssh using the daxio utility to read and
write the data, e.g. daxio -ouput /dev/dax0.0 | ssh <dest_compute_ip> "daxio
-input /dev/dax0.1" This will reuse the exising ssh_execute function used to
implement the ssh remote fs driver.

Notifications impact
--------------------

None


Other end user impact
---------------------
PMEM data will not be copied if performing a cross cell resize/migration.


Other deployer impact
---------------------
None


Developer impact
----------------
None


Performance Impact
------------------
A cold migrate / resize operation will take a lot more time and network
bandwidth than before as it needs to copy the content of the pmem between
compute hosts.


Upgrade impact
--------------
This change will impact host the nova-compute service will behave during
migration / resize so the compute service version needs to be bumped. Also
resize and migration with pmem copy will only work with new enough compute
services so a compute service version check should be implemented for these
operations.

If the copy_pmem_devices=false or the old microverion we proceed with the old
behavior of not copying the data. If the copy_pmem_devices=true and the old
microverion return a 400.

Implementation
==============

Assignee(s)
-----------
QIU FOSSEN(qiujunting@inspur.com)



Feature Liaison
---------------
None


Work Items
----------


Dependencies
============

None


Testing
=======
Add related unit test for negative scenarios.
Add related functional test (API samples).

Documentation Impact
====================
Update the related documents and add some description of this change

References
==========
[1] https://docs.openstack.org/nova/latest/admin/virtual-persistent-memory.html

History
=======

.. list-table:: Revisions
   :header-rows: 1

   * - Release Name
     - Description
   * - Xena
     - Reproposed
