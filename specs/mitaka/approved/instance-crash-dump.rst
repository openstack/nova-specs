..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

=========================================
Support triggering crash dump in a server
=========================================

https://blueprints.launchpad.net/nova/+spec/instance-crash-dump

This spec adds a new API to trigger crash dump in a server (instance or
baremetal) by injecting a driver-specific signal to the server.

Problem description
===================
For now, we can not trigger crash dump in a server from nova. But users need
this functionality for some debug purpose.

If OS occurs a bug(kernel panic), it triggers the kernel crash dump by itself.
But if the OS is *stalling*, we need to trigger crash dump from hardware.
Different platforms could have different ways to trigger crash dump in a
server. And Nova drivers need to implement them.

For x86 platform, using NMI(Non-maskable Interruption) could trigger crash dump
in OS. User should configure the OS to trigger crash dump when it receives an
NMI. In Linux, it can be done by::

  $ echo 1 > /proc/sys/kernel/panic_on_io_nmi

Many hypervisors support injecting NMI to instance.

* Libvirt supports the command "virsh inject-nmi" [1].

* Ipmitool supports the command "ipmitool chassis power diag" [2].

* Hyper-V Cmdlets supports the command
  "Debug-VM -InjectNonMaskableInterrupt" [3].

So we should add an API to inject NMI to server in driver level. Libvirt driver
has implemented such an API [6]. And so will ironic driver for baremetal. And
then add an Nova API to trigger crash dump in server.

This should be optional for drivers.

Use Cases
---------
An end user needs an interface to trigger crash dump in his servers. By the
trigger, the kernel crash dump mechanism dumps the production memory image as
dump file, and reboot the kernel again. After that, the end user can get the
dump file in his server's disk, and investigate the problem reason based on the
file.

This spec only implement the process of triggering crash dump. Where the dump
file will be depends on how the user configures the dump mechanism in his
server. Take Linux as an example:

* If user configures kdump to store dump file on local disk, then user needs to
  reboot the server and access the dump file on local disk.
* If user configures kdump to copy dump file to NFS storage, then user could
  find the dump file on NFS storage without rebooting the server.

Proposed change
===============
* Add a libvirt driver API to inject NMI to an instance.
  (Already merged in Liberty. [6])

* Add an ironic driver API to inject NMI to a baremetal.

* Add a Nova API to trigger crash dump in server using the driver API
  introduced above. If the hypervisor doesn't support injecting NMI,
  NotImplementedError will be raised. This method does not modify instance's
  task_state or vm_state.

* A new instance action will be introduced.

Alternatives
------------
None

Data model impact
-----------------
None

REST API impact
---------------

* Specification for the method

  * A description of what the method does suitable for use in user
    documentation

    * Trigger crash dump in a server.

  * Method type

    * POST

  * Normal http response code

    * 202: Accepted

  * Expected error http response code

    * badRequest(400)

      * When RPC doesn't support this API, this error will be returned. If a
        driver does not implement the API, the error is handled by the new
        instance action because the API is asynchronous.

    * itemNotFound(404)

      * There is no instance or baremetal which has the specified uuid.

    * conflictingRequest(409)

      * The server status must be ACTIVE, PAUSED, RESCUED, RESIZED or ERROR.
        If not, this code is returned.

      * If the specified server is locked, this code is returned to a user
        without administrator privileges. When using the kernel dump
        mechanism, it causes a server reboot. So, only administrators can
        send an NMI to a locked server as other power actions.

  * URL for the resource

    * /v2.1/servers/{server_id}/action

  * Parameters which can be passed via the url

    * A server uuid is passed.

  * JSON schema definition for the body data

    ::

        {
            "trigger_crash_dump": null
        }

  * JSON schema definition for the response data

    * When the result is successful, no response body is returned.

    * When an error occurs, the response data includes the error message [5].

  * This REST API will require an API microversion.

Security impact
---------------
None

Notifications impact
--------------------
None

Other end user impact
---------------------

* A client API for this new API will be added to python-novaclient

* A CLI for the new API will be added to python-novaclient. ::

    nova trigger-crash <server>

Performance Impact
------------------
None

Other deployer impact
---------------------
The default policy for this API is for admin and owners by default.

Developer impact
----------------
This spec will implement the new API in libvirt driver, ironic driver, and
nova itself.

Implementation
==============

Assignee(s)
-----------

Primary assignee:
  Tang Chen (tangchen)

Other contributors:
  shiina-horonori (hshiina)

Work Items
----------
* Add a new REST API.

* Add a new driver API.

* Implement the API in libvirt driver.

* Implement the API in ironic driver.

Dependencies
============
This spec is related to the blueprint in ironic.

* https://blueprints.launchpad.net/ironic/+spec/enhance-power-interface-for-soft-reboot-and-nmi

Testing
=======
Unit tests will be added.

Documentation Impact
====================
* The new API should be added to the documentation.

* The support matrix below will be updated because this functionality is
  optional to drivers.
  http://docs.openstack.org/developer/nova/support-matrix.html

References
==========
[1] http://linux.die.net/man/1/virsh

[2] http://linux.die.net/man/1/ipmitool

[3] https://technet.microsoft.com/en-us/library/dn464280.aspx

[4] https://review.openstack.org/#/c/183456/

[5] http://docs.openstack.org/developer/nova/v2/faults.html

[6] https://review.openstack.org/#/c/202380/

History
=======

.. list-table:: Revisions
   :header-rows: 1

   * - Release Name
     - Description
   * - Liberty
     - Introduced
   * - Mitaka
     - Change API action name, and add ironic driver plan
