..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

============================================================
libvirt supports composing cyborg owned vGPU into domain XML
============================================================

https://blueprints.launchpad.net/nova/+spec/cyborg-vgpu-support

This blueprint proposes to enable vGPU accelerator in nova and cyborg
interaction.

Problem description
===================

In order to allow operators to use cyborg to manage the lifecycle of vGPU,
cyborg needs to discover the vGPUs, reports them to placement, and instruct
nova to allocate a specific vgpu mdev to the instance. Cyborg managed vGPUs
will not replace nova's native vGPU capabilities [1]_ and will provide an
alternative management mechanism in parallel to the existing nova feature.

In the current cyborg-nova interaction [2]_, there is still a small gap in
allocating a cyborg owned vGPU to an instance. This spec proposes to support
composing cyborg owned vGPU into domain XML in nova libvirt driver.

For more information about cyborg side lifecycle management (discover, data
modeling etc.) of vGPU please refer to [3]_.

Use Cases
---------

As an operator, I want to use Cyborg to manage the lifecycle of vGPUs.

Proposed change
===============

1. Define the data model in arq to track a cyborg owned vGPU.

   This data model should provide attach_handle_type to distinguish from a
   PCI device accelerator, and attach_handle_uuid as the mdev UUID which is
   used to create a mdev device in the /sys/class/mdev_bus/..., as well as
   the asked vgpu type of this device. The format will be like:

   ::

       {
           'attach_handle_type': 'MDEV',
           'attach_handle_uuid': '91ac1606-427e-44bb-8233-f4ff4bf3d241',
       }

2. Nova virt driver merge the mdev info from arq into the XML of an instance.

   This will need to get mdevs form arq list and pass it to generate guest xml
   in nova/virt/libvirt/driver.py [4]_. Please be aware that the following is
   just the pseudocode to show the whole function and process.

   ::

       # Get mdevs accelerators from ARQ list.
       mdev_arq_list = [arq for arq in acc_info if arq['attach_handle_type'] == 'MDEV']
       mdevs.append(mdevs_accel)
       xml = self._get_guest_xml(context, instance, network_info,
                                 block_disk_info, image_meta,
                                 block_device_info=block_device_info,
                                 mdevs=mdevs)

       mdev_arq_list = [arq for arq in acc_info if arq['attach_handle_type'] == 'MDEV']
       self._guest_add_accel_mdev_devices(guest, mdev_arq_list)

       def _guest_add_accel_mdev_devices(self, guest, acc_info):
           """Adding mdev accelerators from ARQ list.
           """
           for arq in acc_info:
               self._guest_add_mdevs(guest, arq['attach_handle_uuid'])

3. Cyborg creates mdev device in the sys path

   In theory, if nova and cyborg both can support vGPU management, nova or
   cyborg should support create mdev in its own respective. Therefore, in the
   cyborg lifecycle management of vGPU, cyborg should creates mdev beforehead,
   nova virt driver uses it as an existed resousrce.

   * spawn instance interaction(arq interaction part):

     - nova-conductor requests cyborg to create and bind arq:

       + cyborg-api rpc.call the cyborg-agent to create a new mdev

       + cyborg-agent sucessfully created mdev and returns result

       + cyborg start bind arq

       + cyborg arq successfully bound and notify nova that ARQ bindings
         are resolved for a given instance

     - nova-compute receives bound notification and GET resolved arq

     - nova-compute calls virt driver to spawn an instance

   * reboot instance interaction: when nova-compute calls cyborg GET arq
     API, cyborg does the db lookup and returns the expected arq.

   * host reboot: cyborg-owned vGPU will be missing from the sys path after
     host reboot. The cyborg agent should create the mdevs for all bound arqs
     on start up. Ideally it would set the binding state to "provisioning" on
     start up also. And we would have anohter state "unknown" that cyborg-api
     would report if the cyborg agent misses its heart beat.
     So on start up, when nova compute tries to get accel_info and reboot all
     the instances, it would see 1 of 3 states, "bound" if the cyborg agent
     started first and already completed bininding, "unknown" if the cyborg
     agent has not heartbeat to the cyborg conductor yet, and "provisioning"
     if the agent is in the process of creating the mdev. Cyborg will send the
     same binding complete event notification when it change the status form
     "provisioning" to "bound" as it does during normal arq binding.

4. Avoid conflicts when cyborg vGPU management co-exists with nova
   vGPU management.

   * Use owner (nova, cyborg) trait in Placement when inventory is reported.

     - This will need to add a new namespace in os-traits: OWNER_*.
       Then nova/cyborg report owner trait OWNER_NOVA/OWNER_CYBORG
       as one of the trait when inventory is reported.

       + In the cyborg driver, it will report two traits for vGPU accelerator
         using the format below. For more details, pls refer to the driver
         spec [3]_.

         ::

           trait1: OWNER_CYBORG.
           trait2: CUSTOM_<VENDOR_NAME>_<PRODUCT_ID>_<Virtual_GPU_Type>.

       + In the nova side, it will need to report a new trait **OWNER_NOVA**
         for vGPU resources during inventory report.

     - When the end user makes a vGPU request, for a nova owned vGPU request,
       one can specify ``resources##:VGPU=1`` in flavor. For a cyborg owned
       vGPU, one need specify in pre-defined device profile, then add it to
       flavor.

   * In libvirt driver, use a mdev_tag to identify which vGPU is the current
     operation request(eg. spawn, reboot) going to land. If it is cyborg vGPU,
     tag will be 'ACCELERATOR', otherwise it is 'COMPUTE'.

     - This will need to add a new fuction _get_mdev_tag to identify this
       according to the given accel_info, and return a tag mdev_tag:'COMPUTE'
       or 'ACCELERATOR' to indicate this.

     ::

       def _get_mdev_tag(self, accel_info):
           """Identify which vGPU is the current request going to land.

              parameter: accel_info
              return: mdev_tag('COMPUTE' or 'ACCELERATOR')
           """

           if not accel_info:
               tag = 'COMPUTE'
           else:
               # here is just to show the logic specification
               if any arq in accel_info contains
                   {arq['attach_handle_type'] == 'MDEV',
                    arq['attach_handle_uuid']
                    and arq['attach_handle_info']['asked_type']}:
                       tag = 'ACCELERATOR'
               else:
                   tag = 'COMPUTE'
           return tag

     - And accordingly, we will also need new change in mdev_tag's consumer
       side, the nova operations side, such as hard_reboot and spawn.

Alternatives
------------

None

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

None

Other deployer impact
---------------------

Deployer should make sure the device in one pci address is not configured in
both Nova and Cyborg. If it is configured in both Cyborg and Nova should be
able to raise this as an conflict exception.
If the deployer configure same device in both Cyborg and Nova, they may report
same data to Placement at the same time, we can raise conflict exception at
Placement side, and return to Cyborg or Nova, and warn the deployer about
the conflict device.

Developer impact
----------------

None

Upgrade impact
--------------

For those who want to upgrade from nova-owned vGPU to cyborg-owned vGPU,
one can resize directly from a flavor with a nova managed gpu
(resouces:vgpu=1 in the flavor) to a flavor with a cyborg managed vgpu
(accel:device-profile=cyborg-vgpu-device-profile-name).

Implementation
==============

Assignee(s)
-----------

Primary assignee:
  Wenping Song <songwenping@inspur.com>

Other contributors:
  yumeng-bao

Feature Liaison
---------------

Feature liaison:
  Brin Zhang <zhangbailin@inspur.com>

Work Items
----------

* Schedule vGPU resources by device profile

* Create vGPU mdev when spawn guest

* Unit test and function test to be added

Dependencies
============

None

Testing
=======

* New unit test should be added

Documentation Impact
====================

* Document need to be changed to describe this feature

References
==========

.. [1] https://docs.openstack.org/nova/ussuri/admin/virtual-gpu.html
.. [2] https://specs.openstack.org/openstack/nova-specs/specs/ussuri/implemented/nova-cyborg-interaction.html
.. [3] https://review.opendev.org/#/c/758925/
.. [4] https://github.com/openstack/nova/blob/master/nova/virt/libvirt/driver.py#L6139

History
=======

.. list-table:: Revisions
   :header-rows: 1

   * - Release Name
     - Description
   * - Wallaby
     - Introduced
