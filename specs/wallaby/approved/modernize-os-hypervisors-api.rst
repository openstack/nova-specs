..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

=======================================================
Remove resource information from ``os-hypervisors`` API
=======================================================

https://blueprints.launchpad.net/nova/+spec/modernize-os-hypervisors-api

The ``os-hypervisors`` API is around since the early days of nova. Back in
those halcyon days, it provided a nice way to get a quick summary of the
resource usage of individual compute nodes in your deployment. Today, however,
it's a shell of itself. The more detailed information it returns is
hypervisor-specific and frequently wrong, especially with advanced features
like CPU pinning or file-based memory. With the elevation of placement to its
rightful place as lord of (almost) all things resource'y, the ``os-hypervisor``
API needs to slim down significantly.

Problem description
===================

Consider the output of a typical ``GET /os-hypervisors/detail`` call, as taken
from the API ref [1]_:

.. code-block:: json

    {
        "hypervisors": [
            {
                "cpu_info": {
                    "arch": "x86_64",
                    "model": "Nehalem",
                    "vendor": "Intel",
                    "features": [
                        "pge",
                        "clflush"
                    ],
                    "topology": {
                        "cores": 1,
                        "threads": 1,
                        "sockets": 4
                    }
                },
                "current_workload": 0,
                "status": "enabled",
                "state": "up",
                "disk_available_least": 0,
                "host_ip": "1.1.1.1",
                "free_disk_gb": 1028,
                "free_ram_mb": 7680,
                "hypervisor_hostname": "host1",
                "hypervisor_type": "fake",
                "hypervisor_version": 1000,
                "id": 2,
                "local_gb": 1028,
                "local_gb_used": 0,
                "memory_mb": 8192,
                "memory_mb_used": 512,
                "running_vms": 0,
                "service": {
                    "host": "host1",
                    "id": 6,
                    "disabled_reason": null
                },
                "vcpus": 2,
                "vcpus_used": 0
            }
        ],
        "hypervisors_links": [
            {
                "href": "http://openstack.example.com/v2.1/6f70656e737461636b20342065766572/os-hypervisors/detail?limit=1&marker=2",
                "rel": "next"
            }
        ]
    }

The fields here broadly fall into three categories: useful but duplicated in
the summary (non-detailed) view, useful and unique to the detailed view, and
not useful. First, the useful but duplicated fields. These should remain:

- ``id``
- ``status``
- ``state``
- ``hypervisor_hostname``

Next, the useful fields unique to the detailed view. These should also remain:

- ``host_ip``
- ``hypervisor_type``
- ``hypervisor_version``
- ``service``

Finally, the useless fields. There are varied reasons their uselessness,
described below, but all should be removed:

- ``current_workload``

  This tracks "the number of tasks the hypervisor is responsible for" and it
  "will be equal or greater than the number of active VMs on the system (it can
  be greater when VMs are being deleted and the hypervisor is still cleaning
  up)" [2]_. This information is easily calculated by listing active and
  deleted instances.

- ``cpu_info``

  Useful at face value but the only thing relevant for scheduling purposes are
  the CPU architecture and CPU features, all of which are already handled by
  placement trait requests. The topology field is an oddity that should likely
  never have been added. It's not usable in scheduling and is possibly wrong,
  given it doesn't reflect offline CPUs or those not available to nova due to
  configuration, and it doesn't handle non-uniform CPU topologies where there
  are e.g. more cores on one socket than another. If the operator wants this
  information, they can simply inspect the host like they would have to do to
  identify e.g. the specifics of PCI devices or storage devices.

- ``free_disk_gb``, ``local_gb``, ``local_gb_used``

  💩 Almost always wrong if shared storage is in use and doesn't take
  overcommit into account. Use placement.

- ``disk_available_least``

  Reflects the estimated available disk space on the hypervisor if all
  instances on the host were to use all their allocated disk. This can go
  negative if disk overcommit is enabled or if an instance is force migrated to
  a host, bypassing the scheduler. This value is hard to use and frequently
  misunderstood by end-users.

- ``free_ram_mb``, ``memory_mb``, ``memory_mb_used``

  Doesn't take overcommit or non-default pagesizes into account. Use placement.

- ``vcpus``, ``vcpus_used``

  Doesn't take overcommit or PCPU inventory into account. Use placement.

- ``running_vms``

  Easily figured out by filtering running instances by host (admin-only, like
  this API).

While we can remove the useless fields, the useful ones are still limited in
their usefulness owing to the restrictive policy in place for this API. We can
improve this by allowing users with the ``PROJECT_ADMIN`` role to list all
hypervisors their project is allowed to access.

.. [1] https://docs.openstack.org/api-ref/compute/?expanded=list-hypervisors-details-detail,show-hypervisor-details-detail
.. [2] https://docs.openstack.org/api-ref/compute/?expanded=list-hypervisors-details-detail#id298

Use Cases
---------

As a user, I don't want to see misleading information reported from my API.

Proposed change
===============

Remove the resource-related fields from the output of the
``/os-hypervisors/detail`` API and remove the ``/os-hypervisors/statistics``
API in its entirety. Modify the default policy used for ``GET /os-hypervisors``
from ``SYSTEM_READER`` to ``SYSTEM_READER_OR_PROJECT_ADMIN`` to allow users
with the ``SYSTEM_READER`` role to see all hypervisors and users with the
``PROJECT_ADMIN`` role to see only the hypervisors that their project is
allowed to access, based on aggregate metadata.

Alternatives
------------

We could document the incorrect nature of these APIs. This is less desirable
since people don't read documentation.

Data model impact
-----------------

None.

REST API impact
---------------

Starting from the new API microversion, the ``/os-hypervisors/detail`` API will
no longer include the following fields in its response: ``cpu_info``,
``free_disk_gb``, ``local_gb``, ``local_gb_used``, ``disk_available_least``,
``free_ram_mb``, ``memory_mb``, ``memory_mb_used``, ``vcpus``, ``vcpus_used``,
and ``running_vms``.

In addition, the ``/os-hypervisors/statistics`` API will be removed entirely
and will return a HTTP 410 (Gone).

Finally, change the policy used for the ``/os-hypervisors`` API from
``SYSTEM_READER`` to ``SYSTEM_READER_OR_PROJECT_ADMIN``, allowing users with
the ``PROJECT_ADMIN`` role to see all hypervisors their project is allowed
access to. The other hypervisor-related APIs will not have their policies
modified.

Security impact
---------------

None.

Notifications impact
--------------------

None.

Other end user impact
---------------------

The clients will need to be updated. Documentation referencing these APIs will
need to be updated with recommendations to look at placement or other APIs
instead. Specifically:

- The ``free_disk_gb``, ``local_gb``, ``local_gb_used``, ``free_ram_mb``,
  ``memory_mb``, ``memory_mb_used``, ``vcpus`` and ``vcpus_used`` values can be
  identified using a combination of ``openstack resource provider inventory
  list`` and ``openstack resource provider usage show``. For example::

      $ openstack hypervisor show devstack-1 \
          -c local_gb -c local_gb_used -c free_disk_gb \
          -c memory_mb -c memory_mb_used -c free_ram_mb \
          -c vcpus -c vcpus_used
      +----------------+-------+
      | Field          | Value |
      +----------------+-------+
      | local_gb       | 18    |
      | local_gb_used  | 1     |
      | free_disk_gb   | 19    |
      | memory_mb      | 16035 |
      | memory_mb_used | 1024  |
      | free_ram_mb    | 15011 |
      | vcpus          | 12    |
      | vcpus_used     | 1     |
      +----------------+-------+

      $ openstack resource provider inventory list bde27f9d-1249-446f-ae14-45f6ff3e63d5
      +----------------+------------------+----------+----------+----------+-----------+-------+
      | resource_class | allocation_ratio | min_unit | max_unit | reserved | step_size | total |
      +----------------+------------------+----------+----------+----------+-----------+-------+
      | VCPU           |             16.0 |        1 |       12 |        0 |         1 |    12 |
      | MEMORY_MB      |              1.5 |        1 |    16035 |      512 |         1 | 16035 |
      | DISK_GB        |              1.0 |        1 |       19 |        0 |         1 |    19 |
      +----------------+------------------+----------+----------+----------+-----------+-------+

      $ openstack resource provider usage show bde27f9d-1249-446f-ae14-45f6ff3e63d5
      +----------------+-------+
      | resource_class | usage |
      +----------------+-------+
      | VCPU           |     1 |
      | MEMORY_MB      |   512 |
      | DISK_GB        |     1 |
      +----------------+-------

- The ``running_vms`` value can be identified using by filter instances by host
  using ``openstack server list --host <HOST>``. For example::

      $ openstack hypervisor show devstack-1 -c running_vms
      +-------------+-------+
      | Field       | Value |
      +-------------+-------+
      | running_vms | 1     |
      +-------------+-------+

      $ openstack server list --host devstack-1 -c ID -f yaml | wc -l
      1

  .. note::

     This is not a 1:1 replacement since the ``running_vms`` setting will track
     all VMs running on the hypervisor, including those not managed by nova.
     However, having VMs not managed by nova on a hypervisor is considered a
     misconfiguration and is irrelevant for scheduling purposes.

- The ``cpu_info.arch`` and ``cpu_info.features`` values are published as
  traits and can be inspected using ``openstack resource provider trait list``.
  For example::

      $ openstack hypervisor show devstack-1 -f yaml -c cpu_info
      cpu_info: '{"arch": "x86_64", "model": "IvyBridge-IBRS", "vendor": "Intel", "topology":
        {"cells": 2, "sockets": 1, "cores": 3, "threads": 2}, "features": ["xsaveopt", "erms",
        "ssbd", "arch-capabilities", "nx", "cx16", "ht", "mca", "tsc-deadline", "amd-ssbd",
        "pcid", "pse", "ss", "syscall", "md-clear", "tsc_adjust", "mmx", "rdtscp", "f16c",
        "fxsr", "lahf_lm", "spec-ctrl", "smep", "pse36", "vme", "de", "sse", "xsave", "clflush",
        "cmov", "msr", "pat", "aes", "hypervisor", "mtrr", "sep", "fsgsbase", "tsc", "sse2",
        "apic", "pdpe1gb", "cx8", "umip", "vmx", "pae", "skip-l1dfl-vmentry", "popcnt",
        "ssse3", "avx", "pclmuldq", "x2apic", "lm", "stibp", "fpu", "ibpb", "rdrand", "sse4.1",
        "pni", "pge", "sse4.2", "pschange-mc-no", "mce", "arat"]}'

      $ openstack --os-placement-api-version 1.8 \
          resource provider trait list bde27f9d-1249-446f-ae14-45f6ff3e63d5 | grep CPU
      | HW_CPU_X86_AMD_SVM                    |
      | HW_CPU_X86_SSE2                       |
      | HW_CPU_X86_SSE                        |
      | HW_CPU_X86_SVM                        |
      | HW_CPU_HYPERTHREADING                 |
      | HW_CPU_X86_MMX                        |

- The ``disk_available_least``, ``cpu_info.model``, ``cpu_info.vendor`` and
  ``cpu_info.topology`` values are not relevant for scheduling and therefore
  have no direct replacement in placement or another API. They can, however, be
  identified through inspection of the host.

Horizon will need to be updated to talk to placement or use this API with an
older microversion.

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
  stephenfinucane

Other contributors:
  None

Feature Liaison
---------------

None.


Work Items
----------

- Update the APIs in a new microversion.
- Update the documentation to remove references to these deprecated APIs.
- Update the clients to reflect the deprecations.

Dependencies
============

None.

Testing
=======

Unit and functional tests. Tempest tests will need to be updated to cap against
the latest microversion to support these APIs.

Documentation Impact
====================

References to the APIs will need to be removed or updated.

References
==========

None.

History
=======

.. list-table:: Revisions
   :header-rows: 1

   * - Release Name
     - Description
   * - Wallaby
     - Introduced
