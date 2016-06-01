..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

=====================================================================
nova-api should return hypervisor.cpu_info as json object, not string
=====================================================================

https://blueprints.launchpad.net/nova/+spec/nova-api-hypervsor-cpu-info

Change hypervisor.cpu_info field in nova-api from string to regular
JSON object.

Problem description
===================

nova-api returns hypervisor's cpu_info in string, instead of regular
JSON-object:

::

 {
   "hypervisor": {
      "status":"enabled",
      "service":{
         "host":"host1",
         "disabled_reason":null,
         "id":5
      },
      "vcpus_used":1,
      "hypervisor_type":"QEMU",
      "local_gb_used":0,
      "vcpus":1,
      "hypervisor_hostname":"host1",
      "memory_mb_used":576,
      "memory_mb":3010,
      "current_workload":0,
      "state":"up",
      "host_ip":"192.168.122.121",
      "cpu_info":"{\"vendor\": \"Intel\", \"model\": \"cpu64-rhel6\",
                   \"arch\": \"x86_64\", \"features\": [\"pge\",
                   \"clflush\", \"sep\", \"syscall\", \"tsc\", \"vmx\",
                   \"cmov\", \"fpu\", \"pat\", \"lm\", \"msr\", \"nx\",
                   \"fxsr\", \"pae\", \"mmx\", \"cx8\", \"mce\", \"de\",
                   \"mca\", \"pse\", \"pni\", \"abm\", \"popcnt\", \"apic\",
                   \"sse\", \"lahf_lm\", \"sse2\", \"hypervisor\", \"cx16\",
                   \"pse36\", \"mtrr\", \"x2apic\"], \"topology\":
                   {\"cores\": 1, \"threads\": 1, \"sockets\": 1}}",
      "running_vms":1,
      "free_disk_gb":21,
      "hypervisor_version":2000000,
      "disk_available_least":14,
      "local_gb":21,
      "free_ram_mb":2434,
      "id":1
   }
 }

cpu_info is stored in DB as string, and that's OK. But in API such string is
unacceptable and should be changed to object. There is completely redundant
logic in python-novaclient, which exists only because of cpu_info field.


Use Cases
----------

This change helps to improve api, which is used by many modules/systems.
also refactoring could help to improve unit-tests quality in nova.

Project Priority
-----------------

None

Proposed change
===============

Add logic to deserialize cpu_info field from string to  objects.VirtCPUModel
after object is loaded from db.

Alternatives
------------

As alternative api could provide enum for cpu_info.model, cpu_info.vendor,
and cpu_info.features.name. This approach will add new data layer between
actual values from hypervisor and values returned with api response.
Also addition of new model and vendors into hypervisor causes API bump
every time.

Data model impact
-----------------

None

REST API impact
---------------

Change in should be added in a new API microversion:

`GET /v2.1/os-hypervisors/{hypervisor_id}`

Show hypervisor details
Shows details for a specified hypervisor.

Change in response data:

::

 cpu_info = {
     'type': 'object',
     'properties': {
         'vendor': {
             'type': 'string',
             'minLength': 1,
             'maxLength': 255
         },
         'model': {
             'type': 'string',
             'minLength': 1,
             'maxLength': 255
         },
         'features': {
             'type': 'array',
             'items': {
                 'type': 'string',
             }
         },
         'topology': {
             'type': 'object',
             'properties': {
                 'cores': {
                     'type': 'int',
                     'minimum': 1
                 },
                 'threads': {
                     'type': 'int',
                     'minimum': 1
                 },
                 'sockets': {
                     'type': 'int',
                     'minimum': 1
                 }
             }
         },
         'arch': {
             'type': 'string', 'enum': ['alpha', 'armv6', 'armv7l',
                                        'armv7b', 'aarch64', 'cris',
                                        'i686', 'ia64', 'lm32', 'm68k',
                                        'microblaze', 'microblazeel',
                                        'mips', 'mipsel', 'mips64',
                                        'mips64el', 'openrisc', 'parisc',
                                        'parisc64', 'ppc', 'ppcle', 'ppc64',
                                        'ppc64le', 'ppcemb', 's390',
                                        's390x', 'sh4', 'sh4eb', 'sparc',
                                        'sparc64', 'unicore32', 'x86_64',
                                        'xtensa', 'xtensaeb']
             'minLength': 1,
             'maxLength': 255
         }
     },
     'additionalProperties': False
 }

Response example:

::

  {
    "hypervisor": {
       "status": "enabled",
       "service": {
          "host": "host1",
          "disabled_reason": null,
          "id": 5
       },
       "vcpus_used": 1,
       "hypervisor_type": "QEMU",
       "local_gb_used": 0,
       "vcpus": 1,
       "hypervisor_hostname": "host1",
       "memory_mb_used": 576,
       "memory_mb": 3010,
       "current_workload": 0,
       "state": "up",
       "host_ip": "192.168.122.121",
       "cpu_info": {
          "vendor": "Intel",
          "model": "cpu64-rhel6",
          "arch": "x86_64",
          "features": ["sse2",
                       "cx16",
                       "pse36",
                       "mtrr",
                       "x2apic"],
          "topology": {
             "cores": 1,
             "threads": 1,
             "sockets": 1
          }
       },
       "running_vms": 1,
       "free_disk_gb": 21,
       "hypervisor_version": 2000000,
       "disk_available_least": 14,
       "local_gb": 21,
       "free_ram_mb": 2434,
       "id": 1
    }
 }


Security impact
---------------

None

Notifications impact
--------------------

None

Other end user impact
---------------------
python-novaclient should implement logic to work with new api microversion
If API microversion contains this change no attempts to deserialize cpu_info
in python-novaclient should happen.

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
  tdurakov

Work Items
----------

* Change cpu_info field in nova-api from string to regular JSON object.
* Change parsing logic in python-novaclient with respect to API microversion.


Dependencies
============

None

Testing
=======

Existing tests should be changed so they fits schema, provided above.

Documentation Impact
====================

REST-API documentation should be updated according to schema provided in spec

References
==========

None

