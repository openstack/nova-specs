..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

===================================
Restore standardised VM Diagnostics
===================================

https://blueprints.launchpad.net/nova/+spec/restore-vm-diagnostics

Currently there is no defined format for VM diagnostics. This BP will ensure
that all of the drivers that provide VM diagnostics will have a consistent
format.

**NOTE:** VM diagnostic spec was implemented in Juno but only for API v3 [1]_.
After that V3 API was removed. This spec will restore API part of VM
diagnostic BP. All other parts of BP (e.g. compute API part, virt drivers part)
weren't removed with v3 API.

Problem description
===================

Now VM diagnostics are a 'blob' of data returned by each hypervisor. The
goal here is to have a formal definition of what output should be returned, if
possible, by the drivers supporting the API.

Use Cases
---------

Diagnostic information from all virt drivers will have the same format.
It will help to use this information and it will help to get rid of need to
know from what virt driver you got diagnostic information.

Proposed change
===============

Add an API microversion that will standardise response of getting
VM diagnostics info request [2]_. This microversion is **admin-only** by
default. The access is driven by policy. The microversion will use a virt
driver method that returns a predefined structure. It was already
implemented::

  get_instance_diagnostics(self, instance)

This method returns information as an object class. A diagnostics
model class will be instantiated and populated by the virt drivers. A field
that is not populated by the driver will return a default value set in the
aforementioned class. After getting object class from the method we will build
a response in the API layer by getting fields from this object.

The table below has the key and the description of the value returned:

+------------------------+---------------------------------------------------+
| Key                    | Description                                       |
+========================+===================================================+
| state                  | A string enum denoting the current state of       |
|                        | the VM. Possible values are: 'pending', 'running',|
|                        | 'paused', 'shutdown', 'crashed', 'suspended'      |
|                        | (String)                                          |
+------------------------+---------------------------------------------------+
| driver                 | A string denoting the driver on which the VM is   |
|                        | running. Examples may be: 'libvirt', 'xenapi',    |
|                        | 'hyperv' and 'vmwareapi' (String)                 |
+------------------------+---------------------------------------------------+
| hypervisor             | A string denoting the hypervisor on which the VM  |
|                        | is running. Examples for libvirt driver may be:   |
|                        | 'qemu', 'kvm' or 'xen'. (String)                  |
+------------------------+---------------------------------------------------+
| hypervisor_os          | A string denoting the hypervisor OS (String)      |
+------------------------+---------------------------------------------------+
| uptime                 | The amount of time in seconds that the VM has     |
|                        | been running (Integer)                            |
+------------------------+---------------------------------------------------+
| num_cpus               | The number of vCPUs (Integer)                     |
+------------------------+---------------------------------------------------+
| num_nics               | The number of vNICS (Integer)                     |
+------------------------+---------------------------------------------------+
| num_disks              | The number of disks (Integer)                     |
+------------------------+---------------------------------------------------+
| cpu_details            | An array of details (a dictionary) per vCPU (see  |
|                        | below)                                            |
+------------------------+---------------------------------------------------+
| nic_details            | An array of details (a dictionary) per vNIC (see  |
|                        | below)                                            |
+------------------------+---------------------------------------------------+
| disk_details           | An array of details (a dictionary) per disk (see  |
|                        | below)                                            |
+------------------------+---------------------------------------------------+
| memory_details         | A dictionary of memory details (see below)        |
+------------------------+---------------------------------------------------+
| config_drive           | Indicates if the config drive is supported on     |
|                        | the instance (Boolean)                            |
+------------------------+---------------------------------------------------+

Note: If the virt driver is unable to provide a specific field then this field
will be reported as 'None' in the diagnostics.

The cpu details is an array of dictionaries per each virtual CPU.

+------------------------+---------------------------------------------------+
| Key                    | Description                                       |
+========================+===================================================+
| id                     | CPU ID (String)                                   |
+------------------------+---------------------------------------------------+
| time                   | CPU Time in nano seconds (Integer)                |
+------------------------+---------------------------------------------------+

The network details is an array of dictionaries per each virtual NIC.

+------------------------+---------------------------------------------------+
| Key                    | Description                                       |
+========================+===================================================+
| mac_address            | Mac address of the interface (String)             |
+------------------------+---------------------------------------------------+
| rx_octets              | Received octets (Integer)                         |
+------------------------+---------------------------------------------------+
| rx_errors              | Received errors (Integer)                         |
+------------------------+---------------------------------------------------+
| rx_drop                | Received packets dropped (Integer)                |
+------------------------+---------------------------------------------------+
| rx_packets             | Received packets (Integer)                        |
+------------------------+---------------------------------------------------+
| tx_octets              | Transmitted Octets (Integer)                      |
+------------------------+---------------------------------------------------+
| tx_errors              | Transmit errors (Integer)                         |
+------------------------+---------------------------------------------------+
| tx_drop                | Transmit dropped packets (Integer)                |
+------------------------+---------------------------------------------------+
| tx_packets             | Transmit packets (Integer)                        |
+------------------------+---------------------------------------------------+

The disk details is an array of dictionaries per each virtual disk.

+------------------------+---------------------------------------------------+
| Key                    | Description                                       |
+========================+===================================================+
| read_bytes             | Disk reads in bytes (Integer)                     |
+------------------------+---------------------------------------------------+
| read_requests          | Read requests (Integer)                           |
+------------------------+---------------------------------------------------+
| write_bytes            | Disk writes in bytes (Integer)                    |
+------------------------+---------------------------------------------------+
| write_requests         | Write requests (Integer)                          |
+------------------------+---------------------------------------------------+
| errors_count           | Disk errors (Integer)                             |
+------------------------+---------------------------------------------------+

The memory details is a dictionary.

+------------------------+---------------------------------------------------+
| Key                    | Description                                       |
+========================+===================================================+
| maximum                | Amount of memory provisioned for the VM in MB     |
|                        | (Integer)                                         |
+------------------------+---------------------------------------------------+
| used                   | Amount of memory that is currently used by the    |
|                        | guest operating system and its applications in MB |
|                        | (Integer)                                         |
+------------------------+---------------------------------------------------+

Below is an example of the dictionary data returned by the fake driver::

           {'state': 'running',
            'driver': 'fake-driver',
            'hypervisor_os': 'fake-os',
            'hypervisor': 'fake-hypervisor',
            'uptime': 7,
            'num_cpus': 1,
            'num_vnics': 1,
            'num_disks': 1,
            'cpu_details': [{'id': '0',
                             'time': 1024}],
            'nic_details': [{'mac_address': '00:00:00:00:00:00',
                             'rx_octets': 0,
                             'rx_errors': 0,
                             'rx_drop': 0,
                             'rx_packets': 0,
                             'tx_octets': 0,
                             'tx_errors': 0,
                             'tx_drop': 0,
                             'tx_packets': 0}],
            'disk_details': [{'read_bytes':0,
                              'read_requests': 0,
                              'write_bytes': 0,
                              'write_requests': 0,
                              'errors_count': 0}],
            'memory_details': {'maximum': 512, 'used': 256}}

Alternatives
------------

Continue with the same format that the current API has. This is problematic as
we are unable to build common user interface that can query VM states,
for example in tempest.

Data model impact
-----------------

None

REST API impact
---------------

A new microversion will be added which will use already merged parts of VM
diagnostic BP. This microversion will change response of getting
VM diagnostics info request [2]_. This microversion is **admin-only** by
default. The access is driven by policy.

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

None

Other deployer impact
---------------------

It will make life easier - deployers will be able to get better insight into
the state of VM and be able to troubleshoot.

Developer impact
----------------

None


Implementation
==============

Assignee(s)
-----------

Primary assignee:
  Sergey Nikitin - snikitin

Work Items
----------

Most of virt drivers support get_instance_diagnostics() method:

* libvirt support (Done)

* XenAPI support (Partially)

* VMware support (Partially)

* Hyper-V support (In progress) [3]_

* Ironic support (Not started)

The work items in this case will be:

* Complete XenAPI support

* Complete VMware support

* Add VM diagnostics microversion API

* Restore and modify existing tempest tests

* Add support for the python-novaclient

Dependencies
============

None

Testing
=======

Tempest already has tests for VM diagnostics, but they are skipped because
API part of this spec was removed from Nova with V3 API [4]_. These tests
should be restored and modified.

Documentation Impact
====================

Docs needed for new API microversion. These docs will describe new output
of getting VM diagnostics info response.

References
==========

.. [1] https://specs.openstack.org/openstack/nova-specs/specs/juno/implemented/v3-diagnostics.html
.. [2] http://developer.openstack.org/api-ref/compute/#show-server-diagnostics
.. [3] https://blueprints.launchpad.net/nova/+spec/hyperv-vm-diagnostics
.. [4] https://bugs.launchpad.net/nova/+bug/1240043
