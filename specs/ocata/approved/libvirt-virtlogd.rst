..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

================================
Libvirt: Use the virtlogd deamon
================================

https://blueprints.launchpad.net/nova/+spec/libvirt-virtlogd

If the *serial console* feature is enabled on a compute node with
``[serial_console].enabled = True`` it deactivates the logging of the
boot messages. From a REST API perspective, this means that the two APIs
``os-getConsoleOutput`` and ``os-getSerialConsole`` are mutually exclusive.
Both APIs can be valuable for cloud operators in the case when something
goes wrong during the launch of an instance. This blueprint wants to lift
the XOR relationship between those two REST APIs.

Problem description
===================

The problem can be seen in the method ``_create_serial_console_devices``
in the libvirt driver. The simplified logic is::

    def _create_serial_console_devices(self, guest, instance, flavor,
                                       image_meta):
        if CONF.serial_console.enabled:
            console = vconfig.LibvirtConfigGuestSerial()
            console.type = "tcp"
            guest.add_device(console)
        else:
            consolelog = vconfig.LibvirtConfigGuestSerial()
            consolelog.type = "file"
            guest.add_device(consolelog)

This ``if-else`` establishes the XOR relationship between having a log of
the guest's boot messages or getting a handle to the guest's serial console.
From a driver point of view, this means getting valid return values for the
method ``get_serial_console`` or ``get_console_output`` which are used to
satisfy the two REST APIs ``os-getConsoleOutput`` and ``os-getSerialConsole``.

Use Cases
----------

From an end user point of view, this means that, with the current state, it
is possible to get the console output of an instance on host A (serial console
is not enabled) but after a rebuild on host B (serial console is enabled) it
is not possible to get the console output. As an end user is not aware of the
host's configuration, this could be a confusing experience. Written that down
I'm wondering why the serial console was designed with a compute node scope
and not with an instance scope, but that's another discussion I don't want to
do here.

After the implementation, deployers will have both means by hand if there is
something wrong during the launch of an instance. The persisted log in case
the instance crashed AND the serial console in case the instance launched but
has issues, for example a failed establishing of networking so that SSH access
is not possible. Also, they will be impacted with a new dependency on the
hosts (see `Dependencies`_).

Developers won't be impacted.


Proposed change
===============

I'd like to switch from the log file to the ``virtlogd`` deamon. This logging
deamon was announced on the libvirt ML [1] and is available with libvirt
version 1.3.3 and Qemu 2.7.0. This logging deamon handles the output from the
guest's console and writes it into the file
``/var/log/libvirt/qemu/guestname-serial0.log`` on the host but
truncates/rotates that log so that it doesn't exhaust the hosts disk space
(this would solve an old bug [3]).

Nova would generate::

    <serial type="tcp">
      <source mode="connect" host="0.0.0.0" service="2445"/>
      <log file="/var/log/libvirt/qemu/guestname-serial0.log" append="on"/>
      <protocol type="raw"/>
      <target port="1"/>
    </serial>

For providing the console log data, nova would need to read the console
log file from disk directly. As the log file gets rotated automatically
we have to ensure that all necessary rotated log files get read to satisfy
the upper limit of the ``get_console_output`` driver API contract.


FAQ
---

#. How is the migration/rebuild handled? The 4 cases which are possible
   (based on the node's patch level):

       #. ``N -> N``: Neither source nor target node is patched. That's what
          we have today. Nothing to do.

       #. ``N -> N+1``: The target node is patched, which means it can make
          use of the output from *virtlogd*. Can we "import" the existing log
          of the source node into the *virtlogd* logs of the target node?

          A: The guest will keep its configuration from the source host
          and don't make use of the *virtlogd* service until it gets rebuilt.

       #. ``N+1 -> N``: The source node is patched and the instance gets
          migrated to a target node which cannot utilize the *virtlogd*
          output. If the serial console is enable on the target node, do
          we throw away the log because we cannot update it on the target
          node

          A: In the case of migration to an old host, we try to copy the
          existing log file across, and configure the guest with the
          ``type=tcp`` backend. This provides ongoing support for interactive
          console. The log file will remain unchanged if possible. A failed
          copy operation should not prevent the migration of the guest.

       #. ``N+1 -> N+1``: Source and target node are patched. Will libvirt
          migrate the existing log from the source node too, which would
          solve another open bug [4].

#. Q: Could a stalling of the guest happen if *nova-compute* is reading the
   log file and *virtlogd* tries to write to the file but is blocked?

   A: No, *virtlogd* will ensure things are fully parallelized

#. Q: The *virtlogd* deamon has a ``1:1`` relationship to a compute node.
   It would be interesting how well it performs when, for example,
   hundreds of instances are running on one compute node.

   A: We could add a I/O rate limit to *virtlogd* so it refuses to read data
   too quickly from a single guest. This prevents a single guest DOS'ing
   the host.

#. Q: Are there architecture dependencies? Right now, a nova-compute node on a
   s390 architecture depends on the *serial console* feature because it
   cannot provide the other console types (VNC, SPICE, RDP). Which means it
   would benefit from having both.

   A: No architecture dependencies.

#. Q: How are restarts of the *virtlogd* deamon handled? Do we lose
   information in the timeframe between stop and start?

   A: The *virtlogd* daemon will be able to re-exec() itself while keeping
   file handles open. This will ensure no data loss during restart of
   *virtlogd*.

#. Q: Do we need a version check of libvirt to detect if the *virtlodg* is
   available on the host? Or is it sufficient to check if the folder
   ``/var/log/virtlogd/`` is present?

   A: We will do a version number check on libvirt to figure out if it is
   capable to use it.

Alternatives
------------

#. In case where the *serial console* is enabled, we could establish a
   connection to the guest with it and execute ``tail /var/log/dmesg.log``
   and return that output in the driver's ``get_console_output`` method which
   is used to satisfy the ``os-getConsoleOutput`` REST API.

   **Counter-arguments:** We would need to save the authentication data to
   the guest, which would not be technically challenging but the customers
   could be unhappy that Nova can access their guests at any time. A second
   argument is, that the serial console access is blocking, which means
   if user A uses the serial console of an instance, user B is not able to do
   the same.

#. We could remove the ``if-else`` and create both devices.

   **Counter-arguments:** This was tried in [2] and stopped because this could
   introduce a backwards incompatibility which could prevent the rebuild
   of an instance. The root cause for this was, that there is an upper bound
   of 4 serial devices on a guest, and this upper bound could be exceeded if
   an instance which already has 4 serial devices gets rebuilt on a compute
   node which would have patch [2].


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

* The *virtlogd* service has to run for this functionality and should be
  monitored.
* This would also solve a long-running bug which can cause a host disc space
  exhaustion (see [3]).

Developer impact
----------------

None


Implementation
==============

Assignee(s)
-----------

Primary assignee:
  Markus Zoeller (https://launchpad.net/~mzoeller)


Work Items
----------

* (optional) get a gate job running which has the *serial console* activated
* add version check if libvirt supports the *virtlogd* functionality
* add "happy path" which creates a guest device which uses *virtlogd*
* ensure "rebuild" uses the new functionality when migrated from an old host
* add reconfiguration of the guest when migrating from N+1 -> N hosts
  to keep backwards compatibility


Dependencies
============

* Libvirt 1.3.3 which brings the *libvirt virtlod logging deamon* as
  described in [1].
* Qemu 2.7.0


Testing
=======

The tempest tests which are annotated with
``CONF.compute_feature_enabled.console_output`` will have to work with
a setup which

* has the dependency to the *virtlogd deamon* resolved.
* AND has the serial console feature enabled (AFAIK there is not job right
  now which has this enabled)

* A new functional test for the live-migration case has to be added

Documentation Impact
====================

None

References
==========

[1] libvirt ML, "[libvirt] RFC: Building a virtlogd daemon":
    http://www.redhat.com/archives/libvir-list/2015-January/msg00762.html

[2] Gerrit; "libvirt: use log file and serial console at the same time":
    https://review.openstack.org/#/c/188058/

[3] Launchpad; " console.log grows indefinitely ":
    https://bugs.launchpad.net/nova/+bug/832507

[4] Launchpad; "live block migration results in loss of console log":
    https://bugs.launchpad.net/nova/+bug/1203193

[5] A set of patches on the libvirt/qemu ML:

* [PATCH 0/5] Initial patches to introduce a virtlogd daemon
* [PATCH 1/5] util: add API for writing to rotating files
* [PATCH 2/5] Import stripped down virtlockd code as basis of virtlogd
* [PATCH 3/5] logging: introduce log handling protocol
* [PATCH 4/5] logging: add client for virtlogd daemon
* [PATCH 5/5] qemu: add support for sending QEMU stdout/stderr to virtlogd

[6] libvirt ML, "[libvirt] [PATCH v2 00/13] Introduce a virtlogd daemon":
    https://www.redhat.com/archives/libvir-list/2015-November/msg00412.html

History
=======

.. list-table:: Revisions
   :header-rows: 1

   * - Release Name
     - Description
   * - Newton
     - Proposed and approved but blocked by https://bugs.launchpad.net/qemu/+bug/1599214
   * - Ocata
     - Re-proposed.
