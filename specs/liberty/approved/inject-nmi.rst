..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

==========================================
Inject NMI to an instance
==========================================

https://blueprints.launchpad.net/nova/+spec//inject-nmi

This spec adds a new API which injects an NMI(Non-maskable Interruption) to an
instance for triggering a special function such as the kernel crash dump
mechanism.

Problem description
===================
NMI(Non-maskable Interruption) is used to trigger a special function. For
example, in the mission critical area, it is necessary to trigger the kernel
crash dump mechanism.

The kernel crash dump can be triggered by the hand using the following
command::

  $ echo c > /proc/sysrq-trigger

And if the kernel faces its bug(kernel panic), it triggers the
kernel crash dump by itself.
The reason/merit of NMI is we can trigger the kernel crash dump against a
*stalling* instance.

Although hypervisors support functions to inject an NMI to an instance, Nova
doesn't have an API to inject an NMI.

* Virsh supports the command "virsh inject-nmi" [1].

* Ipmitool supports the command "ipmitool chassis power diag" [2].

* Hyper-V Cmdlets supports the command
  "Debug-VM -InjectNonMaskableInterrupt" [3]

Use Cases
----------
An end user who utilizing a function triggered by an NMI on his/her instances
requires an API to send an NMI to an instance.

By the trigger, the kernel crash dump mechanism dumps the production memory
image as dump file, and reboot the kernel again. After that, the end user can
get the dump file which is stored into his instance and investigate the
problem reason based on the file.

Project Priority
-----------------
None

Proposed change
===============
This spec proposes adding an new API for injecting an NMI and implementing a
method to inject an NMI on drivers. After receiving the NMI, the instance
acts as configured by the end user.

Alternatives
------------
None

Data model impact
-----------------
None

REST API impact
---------------

* Specification for the method

  * A description of what the method does suitable for use in
    user documentation

    * Injects an NMI to a server.

  * Method type

    * PUT

  * Normal http response code

    * 202: Accepted

  * Expected error http response code

    * badRequest(400)

      * When a driver doesn't implement the API, this code is used with an
        error message, following the guideline [4].

      * When a hypervisor fails to send an NMI, this code is used with an
        error message including a reason.

    * itemNotFound(404)

      * There is no instance which has the specified uuid.

    * conflictingRequest(409)

      * The server status must be ACTIVE or ERROR. If not, this code is
        returned.

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
            "inject_nmi": null
        }

  * JSON schema definition for the response data

    * When the result is successful, no response body is returned.

    * When an error occurs, the response data includes the error message [5].

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

    nova inject-nmi <server>

Performance Impact
------------------
None

Other deployer impact
---------------------
The default policy for this API is for admin and owners by default.

Developer impact
----------------
This change adds a new API to the driver.
This spec will implement the new API  on the libvirt driver.

Implementation
==============

Assignee(s)
-----------

Primary assignee:
  shiina-horonori (hshiina)

Other contributors:
  None

Work Items
----------
* Add a new REST API.

* Add a new driver API.

* Implement the API on the libvirt driver.

Dependencies
============
This spec is related to the blueprint in ironic.

* https://blueprints.launchpad.net/ironic/+spec/enhance-power-interface-for-soft-reboot-and-nmi

When the blueprint is approved, the ironic driver will implement the API with
another blueprint.

Testing
=======
Unit tests will be added.

Documentation Impact
====================
The new API should be added to the documentation.

References
==========
[1] http://linux.die.net/man/1/virsh

[2] http://linux.die.net/man/1/ipmitool

[3] https://technet.microsoft.com/en-us/library/dn464280.aspx

[4] https://review.openstack.org/#/c/183456

[5] http://docs.openstack.org/developer/nova/v2/faults.html

History
=======

.. list-table:: Revisions
   :header-rows: 1

   * - Release Name
     - Description
   * - Liberty
     - Introduced


