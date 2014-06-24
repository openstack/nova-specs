..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

==============================
V3 Diagnostics - common output
==============================

https://blueprints.launchpad.net/nova/+spec/v3-diagnostics

Currently there is no defined format for VM diagnostics. This BP will ensure
that all of the drivers that provide VM diagnostics will have a consistent
format.

**NOTE:** this cannot be used for V2 as there may be existing deployments that
parse the current output of the V2 diagnostics.

Problem description
===================

In V2 the VM diagnostics are a 'blob' of data returned by each hypervisor. The
goal here is to have a formal definition of what output should be returned, if
possible, by the drivers supporting the API. In additition to this a driver
will be able to return additional data if they choose.

Proposed change
===============

Introduce a new driver method that will return a predefined structure:
get_instance_diagnostics(self, context, instance)

This is a new driver method. The reason for this is that it is much cleaner
to have a new method instead of having if's which indicate if it is new or
legacy. We should also consider deprecating get_diagnostics. This should be
documented in the virt driver API.

The proposal is to have the drivers return the following information in a
object class. A diagnostics Model() class will be introduced. This will
be instantiated and populated by the virt drivers. The class will have a
method to serialize to JSON so that the API interface can return a JSON
format to the user. A field that is not populated by the driver will return
a default value set in the aforementioned class.

The table below has the key and a description of the value returned:

+------------------------+---------------------------------------------------+
| Key                    | Description                                       |
+========================+===================================================+
| state                  | The current state of the VM. Example values       |
|                        | are: 'pending', 'running', 'paused', 'shutdown',  |
|                        | 'crashed', 'suspended' and 'building' (String)    |
+------------------------+---------------------------------------------------+
| driver                 | A string denoting the driver on which the VM is   |
|                        | running. Examples may be: 'libvirt', 'xenapi',    |
|                        | 'hyperv' and 'vmwareapi' (String) [Admin only -   |
|                        | key will not appear if non admin]                 |
+------------------------+---------------------------------------------------+
| hypervisor_os          | A string denoting the hypervisor OS (String)      |
|                        | [Admin only - key will not appear if non admin]   |
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
| driver_private_data    | A dictionary of private data from the driver.     |
|                        | This is driver specific and each driver can       |
|                        | return information valuable for diagnosing VM     |
|                        | issues. The raw data should versioned.            |
+------------------------+---------------------------------------------------+

Note: A number of the above details are common to all drivers. These values
will be filled in by the Nova compute manager prior to invoking the driver
call. The ones that are virt driver specific will be filled, if possible, by
the virt driver. If the virt driver is unable to provide a spcific field
then that field will not be reported in the diagnostics.

For example::

    def get_instance_diagnostics(self, context, instance):
        """Retrieve diagnostics for an instance on this host."""
        current_power_state = self._get_power_state(context, instance)
        if current_power_state == power_state.RUNNING:
            LOG.audit(_("Retrieving diagnostics"), context=context,
                      instance=instance)
            diagnostics = {}
            diagnostics['state'] = instance.vm_state
            ...
            driver_diags = self.driver.get_instance_diagnostics(instance)
            diagnostics.update(driver_diags)
            return diagnostics

The cpu details will be an array of dictionaries per each virtual CPU.

+------------------------+---------------------------------------------------+
| Key                    | Description                                       |
+========================+===================================================+
| time                   | CPU Time in nano seconds (Integer)                |
+------------------------+---------------------------------------------------+

The network details will be an array of dictionaries per each virtual NIC.

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

The disk details will be an array of dictionaries per each virtual disk.

+------------------------+---------------------------------------------------+
| Key                    | Description                                       |
+========================+===================================================+
| id                     | Disk ID (String)                                  |
+------------------------+---------------------------------------------------+
| read_bytes             | Disk reads in bytes(Integer)                      |
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
| used                   | Amount of memory used by the VM in MB (Integer)   |
+------------------------+---------------------------------------------------+

Below is an example of the dictionary data returned by the fake driver::

           {'state': 'running',
            'driver': 'fake-driver',
            'hypervisor_os': 'fake-os',
            'uptime': 7,
            'num_cpus': 1,
            'num_vnics': 1,
            'num_disks': 1,
            'cpu_details': [{'time': 1024}]
            'nic_details': [{'rx_octets': 0,
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
            'memory_details': {'maximum': 512, 'used': 256},
            'driver_private_data': {'version': 1,
                                    'memory': {'actual': 220160,
                                               'rss': 200164}}

Alternatives
------------

Continue with the same format that the V2 has. This is problematic as
we are unable to build common user interface that can query VM states,
for example in tempest.

We can add an extension to the V2 API that will enable us to return
the information defined in this spec.

Data model impact
-----------------

None

REST API impact
---------------

The V3 diagnostics API will no longer return data defined by the
driver but it will return common data defined in this spec.

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

We should consider adding this support for V2. In order to support backward
compatibility we can add a configuration flag. That is, we can
introduce a flag for the legacy format.

Developer impact
----------------

None


Implementation
==============

Assignee(s)
-----------

Primary assignee:
  Gary Kotton - garyk

Other contributors:
  Bob Ball - bob-ball

Work Items
----------

All work items were in review Icehouse. They were broken up as
follows:

* VM diagnostics (v3 API only)

* XenAPI

* libvirt

* VMware

Dependencies
============

None

Testing
=======

Once the code is approved we will add tests to Tempest that will do the
following for the V3 API (assuming that the underlying driver does
not return NotImplemented (501), which may be the case if the driver
does not support the method):

* Check that the returned driver is one of the supported ones in tree (at
  the moment only libvirt, vmware and xenapi support the v3 method).

* Check that the number of CPU's matches the flavor.

* Check that the disk data matches the flavor.

* Check that the memory matches the flavor.

* If a cinder volume has been attached then we check that there is the
  correct amount of disks attached.

* Check that the number of vNics matches the instance running.

* If the private data is present then check that this is a dictionary and
  has a key 'version'.

In addition to this, if there are tests that fail then we can use the V3
diagnostics to help debug. That is, we can get the diagnostics which may help
isolate problems.

Documentation Impact
====================

We can now at least document the fields that are returned and their meaning.

If we do decide to update the v2 support we will need to update:

Please also update:
http://docs.openstack.org/admin-guide-cloud/content/instance_usage_statistics.html
http://docs.openstack.org/user-guide/content/usage_statistics.html
http://docs.openstack.org/user-guide/content/novaclient_commands.html
http://docs.openstack.org/trunk/openstack-ops/content/lay_of_the_land.html#diagnose-compute

We will need to make sure that we update all of the equivalent v3 docs.
The information in the tables above will be what we add to the documentation.

References
==========

https://wiki.openstack.org/wiki/Nova_VM_Diagnostics
https://bugs.launchpad.net/nova/+bug/1240043
