..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

===========================================================
XenAPI: Support Nova services independently from hypervisor
===========================================================

https://blueprints.launchpad.net/nova/+spec/xenapi-independent-nova

The ability to run Nova compute services independently from the
XenServer host which is running the virtual machines would enable more
flexible deployment and development models, and would significantly
lower the barrier to entry for XenAPI developers.

This spec makes the necessary changes to enable this independent mode
of deployment, where the Nova compute services could be running on an
entirely different machine


Problem description
===================

XenAPI's driver currently assumes that it is running on the hypervisor
which will also be housing the VMs.  While this is a very valid
deployment method, the requirement to run on the same hypervisor is
restricted to a few specific methods and the ability to run Nova
compute independently would be highly beneficial.

Use Cases
---------

* Developer wishes to test the XenAPI driver in their existing Linux
  environment, by running the nova compute services using DevStack but
  connecting to a XenServer hypervisor running as a virtual machine
  inside VirtualBox to deploy the tenant VMs.

* Deployer wishes to consolidate the Nova compute services to enable
  specialised Nova compute environments with individual VMs running
  the services independently of the hypervisor (1:1 relationship
  between nova compute process and hypervisor)

* Deployer wishes to consolidate the Nova compute services into docker
  containers running on a physical host, independently of the
  XenServer hypervisors while maintaining a 1:1 relationship between
  the nova compute process and the hypervisors they are controlling.

Proposed change
===============

The enforced link between XenAPI and the hypervisor all stem from a
single function which assumes that we can get a VM uuid which is
running the compute service.  In this case, this is
vm_utils.get_this_vm_uuid.  Some code inspection has been undertaken
to identify all callers (including indirect callers) of this function
and propose a specific fix for each of the callers.

This spec is not proposing to make all functionality work when running
nova independently of the XenServer host, therefore if
get_this_vm_uuid detects that we are not able to identify a VM we are
running on (so are running independently) it will check for
configuration options that cannot be supported and fail at startup
if any are present.  To simplify the changes, a variable
"independent_compute" will be added to XenAPI's driver and set at
startup.

Through code inspection, the following were identified as depending on
the get_this_vm_uuid function and therefore need a resolution as part
of this spec.

+------------------------------+-------------------------------------------+
|Function name                 | Proposed resolution                       |
+==============================+===========================================+
| vm_utils.get_this_vm_uuid    | Fix callers:vm_utils.get_this_vm_ref      |
|                              | pool._create_slave_info                   |
|                              | vm_utils.ensure_correct_host              |
+------------------------------+-------------------------------------------+
| vm_utils.get_this_vm_ref     | Fix callers:vm_utils.vdi_attached_here    |
|                              | vm_utils.cleanup_attached_vdis            |
+------------------------------+-------------------------------------------+
| vm_utils.vdi_attached_here   | Fix callers:vm_utils.auto_configure_disk  |
|                              | vm_utils._generate_disk                   |
|                              | vm_utils.generate_configdrive             |
|                              | vm_utils._fetch_disk_image                |
|                              | vm_utils.preconfigure_instance            |
|                              | vm_utils._copy_partition                  |
+------------------------------+-------------------------------------------+
| pool._create_slave_info      | Prevent joining an XS host aggregate if   |
|                              | independent_compute[1]                    |
+------------------------------+-------------------------------------------+
| vm_utils.ensure_correct_host | Startup config check: check_host          |
|                              | must be disabled if independent_compute   |
+------------------------------+-------------------------------------------+
| vm_utils.cleanup             | Skip cleanup if independent_compute as    |
|          attached_vdis       | no VDIs can be attached                   |
+------------------------------+-------------------------------------------+
| vm_utils.auto_configure_disk | Move to new partition_utils XAPI plugin   |
+------------------------------+-------------------------------------------+
| vm_utils._copy_partition     | Fix callers : vm_utils.resize_disk        |
+------------------------------+-------------------------------------------+
| vm_utils.resize_disk         | Fix callers : create_copy_vdi_and_resize  |
+------------------------------+-------------------------------------------+
| create_copy_vdi_and_resize   | Only used during resize down, which       |
|                              | raises in unsupported modes already, so   |
|                              | raise exception if resize down attempted  |
|                              | when using independent compute[2]         |
+------------------------------+-------------------------------------------+
| vm_utils._generate_disk      | Move to new partition_utils XAPI plugin   |
+------------------------------+-------------------------------------------+
| vm_utils.generate_configdrive| Build config drive as raw drive in the    |
|                              | compute then use XAPI's vdi-import API to |
|                              | import as a disk                          |
+------------------------------+-------------------------------------------+
| vm_utils._fetch_disk_image   | Fix callers:vm_utils._fetch_image         |
|                              | vm_utils._create_kernel_image             |
+------------------------------+-------------------------------------------+
| vm_utils._fetch_image        | Only support downloading of VHDs if       |
|                              | independent_compute.  Separate kernel /   |
|                              | initrd will raise an exception[3]         |
+------------------------------+-------------------------------------------+
| vm_utils._create_kernel_image| Only support downloading of VHDs if       |
|                              | independent_compute.  Separate kernel /   |
|                              | initrd will raise an exception[3]         |
+------------------------------+-------------------------------------------+
| vm_utils.preconfigure        | CONF.flat_injected must be disabled if    |
|          instance            | independent_compute[4]                    |
+------------------------------+-------------------------------------------+

[1] Pool host aggregates currently depend on restarting the VM running
the nova compute services during pool join to restart the nova compute
services, therefore it is tricky to make the two features work in
parallel.  The majority of deployments for the XenAPI driver do not
use pool host aggregates and therefore supporting the combination of
pool host aggregates with independent compute nodes may be covered by
a possible future blueprint.

[2] Resize down could have functionality moved to the new
'partition_utils' XAPI plugin, however there are efforts to reduce the
use of resize_down

[3] Supporting split images isn't believed necessary, and would either
need changes in the glance plugin (currently expecting to download
VHDs) or to download to Nova and then upload to XenServer.  Either
option could be added to a future spec if it were deemed necessary.

[4] This could also be implemented as a XenAPI plugin, but is not
believed to be a commonly set option, so will be deferred to a
possible future blueprint.

Alternatives
------------

Support for separate kernel / initrd images would be possible with the
xenapi-image-streaming blueprint, however as this blueprint is not yet
approved, this implementation will not add support for kernel / initrd
images in the independent compute case.

Data model impact
-----------------

None

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

Performance of the code will only have a minor impact, with an
additional call through to XenAPI to perform some partition-related
tasks.

Code to be moved to partition_utils is IO-bound, rather than
CPU-bound.  As the IO operations are routed through tapdisk in the
same way as when attached to a guest, there is no additional load as a
result of it running in dom0.


Other deployer impact
---------------------

None (Already mentioned): Additional deployment options may be
available (see Use Cases above)

Developer impact
----------------

None.


Implementation
==============

Assignee(s)
-----------

Primary assignee: bob-ball <bob.ball@citrix.com>

Work Items
----------

* 'partition_utils' plugin: Add plugin to move disk-focused
  functionality from DomU to Dom0

* Import config drive: Build config drive in DomU as a RAW disk then
  use API to import the raw into a VDI

* Complete support: Add check for independent compute in
  get_this_vm_uuid, add startup checks for incompatible options.

Dependencies
============

None

Testing
=======

The existing Nova Network CI will test the current Compute-as-a-VM
deployment model.
Citrix are developing a Neutron CI, which will be modified to test
this alternative independent compute deployment model.

Documentation Impact
====================

None

References
==========

None

History
=======

.. list-table:: Revisions
   :header-rows: 1

   * - Release Name
     - Description
   * - Newton
     - Introduced
