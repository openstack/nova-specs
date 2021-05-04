..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

===================================
Smartnic Management Overall Design
===================================

https://blueprints.launchpad.net/nova/+spec/sriov-smartnic-support

This spec proposes an overall design for smartnic management which will involve
Nova, Neutron and Cyborg changes. In this spec, we will introduce how to manage
the smartnic's lifecycle, and how to attach a smartnic to the VM.
This spec aims at supporting VF management, the PF management is out-of-scope.


Problem description
===================

Nowadays, various devices are made to run specific workloads which will free up
CPU resources. Smart-nic is a network device that can be used to offload the
network-related workload. It goes beyond simple connectivity and implements
network traffic processing on the NIC that would necessarily be performed by
the CPU in the case of a conventional NIC.

In the current design, OpenStack can not manage and schedule a smart-nic in
terms of supported features and readable traits automatically.


Use Cases
---------
* Users want to boot up a VM with a specific port which is associated with a
  smartnic resource managed by Cyborg.
* Users want to boot vms that leverage pre-programmed functionality to offload
  their workload to a smart-nic.

Proposed change
===============

There are multiple projects(Nova, Neutron, Cyborg, and Placement) involved in
this feature.

Workflow
--------
This workflow describes the basic operation to boot a VM with pre-programmed
nic.
The workflow can be divided into two parts:

* Device discovery and report.
* Interaction when booting a VM.


Device discovery
^^^^^^^^^^^^^^^^
Cyborg should implement a driver that the cyborg-agent can invoke periodically
to discover the smartnic resources. We will explain this part in detail in
Cyborg spec, please refer to https://review.opendev.org/#/c/759545/.


Device information report
^^^^^^^^^^^^^^^^^^^^^^^^^

How to report physnet trait
:::::::::::::::::::::::::::

As we know, Neutron has a config option physical_device_mappings indicating the
mapping relation between physical_network and network_device. Admin need to
maintain another configuration file (Please refer to 1 in the flowchart) that
contains the device's name and the physical network name this device associate
to.
In this way, the Cyborg driver can directly read from this file and add a
physical network as a trait when reporting to Placement. The admin is
responsible to keep Cyborg's and Neutron's config file consistent, otherwise,
there will be a configuration conflict.

Co-existence with Neutron's Guaranteed Minimum Bandwidth [1]_ Feature
:::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::

According to Wallaby PTG discussion [2]_ and the following discussions [3]_
in the community, we propose to not support co-existence with Neutron's
Guaranteed Minimum Bandwidth Feature for the same physical device at the
first step, which means that one physical device can only be configured by
Cyborg or by Neutron's QoS feature if it is enabled.


The following flowchart illustrates the workflow during device discovery and
report::

    +----------------+
    |   cyborg-api   |
    +--------+-------+
             |
             |                      +-------------+        +-------------+
  +----------|---------+            |             |        |             |
  |  cyborg-conductor  |----------->|  Placement  |<-------|   Neutron   |
  +----------|---------+     |      |             |        |             |
             |               |      +-------------+        +-------------+
             |               |       +------------+
             |               +------>|  Cyborg DB |
    +--------|-------+               +------------+
    |  cyborg-agent  |
    +--------|-------+
             |
             |
             |                   +----------------+
    +--------|-------+     1     |                |
    | device-driver  |<----------|  device.conf   |
    +----------------+           |                |
                                 +----------------+



Interaction when booting the VM
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Currently, Nova can interact with Cyborg to boot up a VM with an accelerator
like FPGA, GPU. And other operations such as hard/soft reboot, pause/unpause
are also supported. But there is no mechanism to let Nova boot up a VM with a
nic associated with a specific network. To implement this, it requires
Nova, Cyborg, and Neutron change. And this spec also covers the scenario about
reboot/pause/stop/start and other operations.

Here we take the "boot a VM" scenario as an example. Assuming that Cyborg has
reported the nic resources and related traits correctly.
The workflow is proposed as the following::

  +-----------+      +-----------+ +-----------+   +-----------+   +---------+
  |   admin   |      |  Neutron  | |   Nova    |   | Placement |   |  Cyborg |
  +-----|-----+      +-----|-----+ +-----|-----+   +-----|-----+   +-------+-+
        |                  |             |               |                 |
        |    1.create device profile     |               |                 |
        |----------------------------------------------------------------->|
                           |             |               |                 |
                           |             |               |                 |
                           |             |               |                 |
                           |             |               |                 |
 +-----------+             |             |               |                 |
 |  end user |             |             |               |                 |
 +-----|-----+             |             |               |                 |
       |  2. create port   |             |               |                 |
       |------------------>|             |               |                 |
       | 3. create server with port      |               |                 |
       |-------------------------------->|               |                 |
                        4.get port details and physnet trait               |

                           |<------------|               |                 |
                                                  5. get device profile
                           |             |<------------------------------->|
                           |             |  6.sheduling  |                 |
                           |             |<------------->|                 |
                           |             |               |                 |
                           |             |               |                 |
                           |             |7.bind device and return PCI info|
                           |             |<------------------------------->|
                           |8.update port|               |                 |
                           |<------------|               |                 |
                           | binding info|               |                 |
                           |             |-----+         |                 |
                           |             |     |         |                 |
                           |             |     | 9. insert SRIOV VIF info  |
                           |             |     | to libvirt XML section    |
                           |             |     |         |                 |
                           |             |<----+         |                 |
                           |             |               |                 |


1. Firstly, admin needs to create a device profile that contains the smartnic's
description such as resource class, and traits. The CLI are already supported
as the following:

`GRP="[{"resources:CUSTOM_NIC": "1","trait:CUSTOM_GTV1":"required"}]"
openstack accelerator device profile create sriov_dp1 $GRP`

2. Secondly, user needs to create a port by passing device profile as a
parameter. Related API needs to be added to operate this. And also,
Neutron need to add a new vnic-type for the nic managed by Cyborg, we can name
it "accelerator-direct" here. For example, we can create a port by: `openstack
port create --network providernet --vnic-type accelerator-direct
--device-profile sriov-dp1 sriov_port1` in which `sriov-dp1` is the device
profile created at the first step. Please notice that the device profile used
by a port should only have one device resource required, otherwise an exception
will be thrown out during the VM boot up process.

The request body is the following:

.. code-block::

    {
       "port": {
            "name": "sriov-port1",
            "network_id": "a87cc70a-3e15-4acf-8205-9b711a3531b7",
            "vnic_type":"accelerator-direct",
            "device_profile": "sriov_dp1" # new extension contains device profile
        }
    }


3. Thirdly, user can boot up a VM by:
`openstack server create --image image-uuid -flavor flavor-name  --nic
port-id=sriov_port1 test_vm1`.
(If the device profile used in the port contains multiple devices, this
API requests will fail with a 400 Error code.)

4. Nova interacts with Neutron to get port’s details, including vnic type,
neutwork_id, physical network, etc.

5. If the vnic type is "accelerator-direct", then Nova need to extract the
"device_profile" extension of sriov_port1, and call Cyborg API to get details
of this device_profile [4]_, the ARQ creation is also in this step.

6. In step 4, Nova has fetched the physical network from Neutron, now Nova need
to convert it into Placement's trait format and save it in port's resource
request field if vnic type is "accelerator-direct". Then Nova need to merge the
resource class/trait obtained from Cyborg’s device profile and the port
resource request into a one single request group. And this request group will
be merged into request_spec which will be used in reboot/pause/start/stop and
other supported operations. After that, Nova schedules the VM to an available
compute node who matches all requested resources.

7. After scheduling, Nova needs to call Cyborg to bind the ARQ with instance
uuid and return attach_handle which contains the device's info such as PCI
address. An async binding job starts in Cyborg and Cyborg will send back a
notification once the binding operation finished.

8. Nova waits for the notification from Cyborg.

9. Once Nova got the notification from Cyborg which indicates the binding
   operation succeed, Nova needs to tell Neutron to update the port binding’s
   info.

10. Libvirt driver need to insert SRIOV nic info to the XML section.


API calls
^^^^^^^^^

1. Nova calls Neutron to get port details.

* request URL: /v2.0/ports/{port_id}
* Method: GET
* response example(the new extension `device_profile` should be returned):

  .. code-block::

      {
        "port": {
            ...
            "binding_profile": {},
            "name": "sriov-port",
            "network_id": "a87cc70a-3e15-4acf-8205-9b711a3531b7",
            "qos_network_policy_id": "174dd0c1-a4eb-49d4-a807-ae80246d82f4",
            "qos_policy_id": "29d5e02e-d5ab-4929-bee4-4a9fc12e22ae",
            "device_profile":"sriov-dp1" # new extension
            ...
        }
       }

2. Nova calls Cyborg to get device profile's details. [5]_

3. Nova calls Cyborg to create and bind ARQs.

* Create ARQ [6]_
* Bind ARQ [7]_
* Wait for "binding success" notification from Cyborg.

4. Nova call Neutron to update port binding profile with interface info. [8]_

Neutron
-------

In Neutron side, a new vnic type "accelerator-direct" need to be added, as well
as a new port extension "device_profile". Please refer to Neutron's RFE [9]_
for details.

The proposed change includes:

* Add a new vnic type "accelerator-direct" indicating the port associated with
  device managed by Cyborg.

* Define device profile extension for port in neutorn lib.

* Implement device profile extension for port in Neutron.

* From DB side, we need to add a new table to store the mapping relation
  between port and device_profile::

    +---------------------------------------+------------------------+
    | port_uuid                             | device_profile         |
    +=======================================+========================+
    | 20f78856-0f73-4cf4-bcd0-1389086eb038  | sriov_dev_profile      |
    +---------------------------------------+------------------------+


Please refer to:

* Port resource request definition [10]_
* neutron-lib port-resource-request Commits [11]_
* neutron plugin port-resource-request Commits [12]_

Nova
----
* Nova API: Nova calls Neutron API to get port details, including vnic type,
  physical network etc.
  "device_profile" should be returned as the return value.
* Nova API: Nova need to check if vnic type is "accelerator-direct". If so,
  Nova will get the device profile's name from neutron port and call Cyborg
  API to get the details of this device profile. Meanwhile, Nova need to
  generate a trait for physical network, for example, Nova get "physnet1" as
  the physical network from Neutorn, the trait should looks like
  "CUSTOM_PHYSNET_PHYSNET1", which is consistent with what Cyborg reports.
* Nova API: Once Nova gets all resource classes and traits, Nova should check
  if a RequestGroup is created with port_resource_request, if so, we should add
  resource and traits to this request group, if not, we should generate a new
  resource group. Nova should have one single request_group to schedule to a
  single nic resource provider [13]_. This request_group store the requested
  resource information used by the scheduler, and other operations, such as
  reboot/pause/unpause/start/stop, will use this request_group to do the
  scheduling as well.
* Nova Compute: Nova should update port binding profile with sriov nic's info
  (such as pci adderess etc), so that libvirt driver can generete related xml
  section.

Cyborg
------

* A new driver needs to be added in Cyborg in order to discover, program and
  bind the device. More details is in the Cyborg spec.
* Cyborg needs to implement a device config file to configure the nic's
  name, pci address, physnet name, etc, which are used for Cyborg driver to
  generate resource provider, trait, etc.

  .. code-block:: RST

    [dev-type]
    physical_device_mappings = physnet1:eth2|eth3
    function_device_mappings = GTPv1:eth3|eth2


Alternatives
------------

Who reports physnet trait
^^^^^^^^^^^^^^^^^^^^^^^^^
* Placement CLI to add trait.

  Admin need to add physnet trait to resource provider manually, this will be
  done after Cyborg reports resource to Placement. It will cause redundant
  Placement API call as well.

* Neutron report trait for the resource provider created by Cyborg.

  In this way, Neutron should firstly get a resource provider created by Cyborg
  by Placement API, and Neutron also need to find the right physnet tratis
  according to nic's resource, which requires more changes in Neutron.

* Let Neutron create RP and physnet trait.

  As we know, Neutron will create RP and related traits when minimum bandwidth
  QoS is configured. We propose that Neutron could always report RP and physnet
  traits all the time, no matter the bandwidth qos configured or not. In this
  way, Cyborg will just find the RP created by Neutron by using some name
  convention, and add accelerator-related traits to this RP.

  But we should consider how the RP tree structure look like when Neutron
  report it, should it be directly under compute node RP, or still under Agent
  RP like bandwidth qos feature does.


How Nova generate request_spec with request device
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
* Neutron calls Cyborg API to get device profile details and merge all RC and
  trait into port_resource_request, then return to Nova.
  By retriving the device profile in neutron from Cyborg, this allows Neutron
  to validate the device profile contains only 1 device request. This check
  will instead be enforced by Nova.

  It requires Neutron changes to interact with Cyborg, which seems that Cyborg
  is a sub-component for Neutron. It's better to let Nova interact with Cyborg
  and Neutron equally.

* Implement a new DeviceProfileRequest to store the device profile's request
  group, and pass it as a new parameter when Nova generates request_spec.

  It seems to be redundant to have a new request object.

Others
^^^^^^
* Cyborg provides its own SRIOV ML2 driver for the NICs it supports.

  Cyborg maintains a Neutron plugin driver that exceeds Cyborg project's scope.

* ARQ's consumer could be a port instead of instance uuid.

  During ARQ binding, Nova wait for an external event from Cyborg which is
  queried by instance uuid. We need keep it same as the workflow for the
  request from flavor.extra_specs.

Data model impact
-----------------
New table `device_profile` needs to be added in Neutron DB.


REST API impact
---------------
* A new extension 'device_profile' will be added in Neutron port, Neutron API
  need changes. Neutron API should also forbid user to modify 'device_profile'
  field once the port is bound with one instance(Neutorn API need to check the
  binding:host-id before updating the 'device profile' field.). This
  modification is only allowed when the port is unbound.
* Change Nova APIs for more operation supports. We plan to support
  create/delete, start/stop, pause/unpause, rebuild, reboot, lock/unlock,
  rescue/unrescue for a VM having an "accelerator-direct" vnic type port,
* Since neutron port can not be associated to multiple NICs, only the device
  profile with one device group is accepted to a port. Otherwise an exception
  will be raised with HTTP 400 Error.
* If the operation is not supported, it will be rejected with an HTTP 400
  Error.
  Case 1: If there are compute nodes with old service versions not support this
  feature, the lifecycle operations of server with ports with device_profile
  need to be rejected with HTTP 400 Error.
  Case 2: For the operation we don't support, such as evacuate, resize,
  migration, shelve/unshelve operations for a VM having an "accelerator-direct"
  vnic type port, and attac/detach an "accelerator-direct" vnic type port
  to/from a VM, an HTTP 400 Error will be returned as well.

Security impact
---------------
None


Notifications impact
--------------------

None


Other end user impact
---------------------
None


Other deployer impact
---------------------
None


Developer impact
----------------
None


Performance Impact
------------------
None


Upgrade impact
--------------
* Nova needs to adapt to the new Neutron API extension introducing the
  device_profile in the port.
* Nova compute service version needs to be bumped and server lifecycle
  operations on server with ports with device_profile needs to be rejected if
  the minimun version of all compute services not satisfy the lowest
  requirement.


Implementation
==============

Assignee(s)
-----------
Yongli He(yongli.he@intel.com)

Xinran Wang(xin-ran.wang@intel.com)


Feature Liaison
---------------
None


Work Items
----------
* Add new port extension in Neutron.
* Implement a new driver for specific nic in Cyborg.
* Add a configuration file in Cyborg to handle physnet.
* Parse and merge request into request spec in Nova.
* Bind ARQ to instance uuid and update port binding profile.
* Re-use the current sriov nic xml generation code.

Dependencies
============

None


Testing
=======

* Need to add UT in the involved project.
* Functional test in Nova.
* Tempest test in Nova if necessary.
* Tempest test in cyborg-tempest-plugin.


Documentation Impact
====================
Need to add documentation.

References
==========

.. [1] https://docs.openstack.org/neutron/latest/admin/config-qos-min-bw.html
.. [2] https://etherpad.opendev.org/p/nova-wallaby-ptg
.. [3] http://eavesdrop.openstack.org/irclogs/%23openstack-nova/%23openstack-nova.2020-11-09.log.html#t2020-11-09T05:48:48
.. [4] https://docs.openstack.org/api-ref/accelerator/v2/index.html?expanded=#list-device-profiles
.. [5] https://docs.openstack.org/api-ref/accelerator/v2/index.html#list-device-profiles
.. [6] https://docs.openstack.org/api-ref/accelerator/v2/index.html#create-accelerator-requests
.. [7] https://docs.openstack.org/api-ref/accelerator/v2/index.html#update-accelerator-requests
.. [8] https://docs.openstack.org/api-ref/network/v2/#update-port
.. [9] https://bugs.launchpad.net/neutron/+bug/1906603
.. [10] https://review.opendev.org/#/c/508149/14/specs/rocky/minimum-bandwidth-allocation-placement-api.rst
.. [11] https://github.com/openstack/neutron-lib/search?q=port-resource-request&type=Commits
.. [12] https://github.com/openstack/neutron/search?q=port-resource-request&type=Commits
.. [13] https://docs.openstack.org/placement/latest/user/provider-tree.html#granular-resource-requests

History
=======

.. list-table:: Revisions
   :header-rows: 1

   * - Release Name
     - Description
   * - Wallaby
     - Approved
   * - Xena
     - Reproposed
