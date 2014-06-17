..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

==========================================
Return hypervisor node status
==========================================

https://blueprints.launchpad.net/nova/+spec/return-status-for-hypervisor-node

Problem description
===================

Currently when user show or list the hypervisor, it will have no idea of the
status, possibly it's down or disabled already. Sometimes it will cause
confusion like in bug https://bugs.launchpad.net/nova/+bug/1285259 .

Proposed change
===============

Propose to return the service state/status when showing the hypervisor node.
For v2 api, an extra extension is added. When the extension is loaded, we will
return the service state/status. For a later microversion of v2.1 api, we will
always return the state/status.

When the service is disabled, add the disabled reason in the service
information in the details/show endpoint.

Alternatives
------------

There are several other options:

* User first get the service information from hypervisor
  node and then show the service status. But I think showing the hypervisor
  status directly will be more straight forward. For example, like in
  https://bugs.launchpad.net/nova/+bug/1285259 , user may trying to figure
  out the instances in a compute node and didn't realize the node is disabled
  already and the information is useless.

* Currently the os-hypervisors extension already returns the service
  information like host and service id. We can extend that field to include
  all service state/status/disabled_reason information. However, it may be
  better to  add the state/status to the list endpoint and only
  disabled_reason to the service information.

Data model impact
-----------------

No change on data model.

REST API impact
---------------

* For V2 API, a new extension will be added as:
  alias: os-hypervisor-status
  name: HypervisorStatus
  namespace: http://docs.openstack.org/compute/ext/hypervisor_status/api/v1.1

  When the new extension "os-hypervisor-status" is loaded, a new field 'status'
  will be added to the os-hypervisor API.

* For a later microversion of v2.1 API, no new extension needed, the
  existing hypervisor REST API will be updated to return the status.


* URL: existed hypervisors extension as:
       * /v2/{tenant_id}/os-hypervisors:
       * /v2.1/os-hypervisors:

  JSON response body::

    {
        "hypervisor": [
        {
            "state": "enabled",
            "status": "up",
            "id": 1,
            "hypervisor_hostname": "otccloud06"
         }]
     }

  The 'status' and 'state' are the new added fields, and are same as
  service API.

* URL: existed hypervisors extension as:
       * /v2/{tenant_id}/os-hypervisors/{id}
       * /v2.1/os-hypervisors/{id}

  JSON response body::

    {"hypervisor": {
            "state": "enabled",
            "status": "up",
            "os-pci:pci_stats": [],
            "service":
            {
                "host": "otccloud06",
                "id": 3,
                "disabled_reason": ""
            },
            "vcpus_used": 0,
            "hypervisor_type": "QEMU",
            "local_gb_used": 0,
            "host_ip": "172.25.110.34",
            "hypervisor_hostname": "otccloud06",
            "memory_mb_used": 512,
            "memory_mb": 128956,
            "current_workload": 0,
            "vcpus": 32,
            "cpu_info": {"vendor": "Intel}
            "running_vms": 0,
            "free_disk_gb": 469,
            "hypervisor_version": 1000000,
            "disk_available_least": 408,
            "local_gb": 469,
            "free_ram_mb": 128444,
            "id": 1}
    }

  The 'status', 'disabled_reason' and 'state' are the new added fields, and
  are same as service API.

Security impact
---------------

No

Notifications impact
--------------------

No

Other end user impact
---------------------

Yes, this will impact the python-novaclient. novaclient should show the status
on the 'nova hypervisor list'.

Performance Impact
------------------

No

Other deployer impact
---------------------

For V2 api, the extension should be added.

Developer impact
----------------

No

Implementation
==============

Assignee(s)
-----------

Primary assignee:
    yunhong-jiang

Work Items
----------

* Changes to V2 API
* Changes to V3 API


Dependencies
============

No

Testing
=======

Both unit and Tempest tests will be created to ensure the correct
implementation.

Documentation Impact
====================

Document the change to the REST API.

References
==========
No
