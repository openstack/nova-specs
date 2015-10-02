..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

===============================
Libvirt Set Admin Root Password
===============================

https://blueprints.launchpad.net/nova/+spec/libvirt-set-admin-password

Nova provides an API to let users set an administrator password on a
virtual machine which is already active. The purpose of this spec is
to take advantage of the libvirt API set-user-password provided with
version 1.2.16 to implement that feature for Qemu/KVM users.

Problem description
===================

Nova provides API to let users set an administrator password but
Qemu/KVM users cannot take advantage of it.

Use Cases
----------

Users want the ability to reset administrator password of an instance
which is already active by using the command "nova root-password
<instance>"

Project Priority
-----------------

None.

Proposed change
===============

To be noted this feature requires that the image have the qemu guest
agent installed to function. Most of the change will be done in the
libvirt driver of Nova.

In order to support both unix-like (GNU/Linux) virtual machines and
Windows the default behavior will be to update password of username
"root" for unix-like virtual machines and "Administrator" for Windows.

To give more flexibility and provide a way for users to change
administrator password of a different username. A new image property
"os_admin_user" will be introduced to let users define who is the
administrator username to update.

Alternatives
------------

The use case for this API is to allow an admin to re-gain control over
an already running guest for which they have lost the password, or for
an admin to bulk change the passwords across all their running guests,
without having to login to the console of each guest
manually/individually. The inject password feature doesn't really
satisfy that.

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

* The end user will have to install a QEMU Guest Agent daemon program
  inside the image and set the image property 'hw_qemu_guest_agent'.
* If the image request a different username to be updated, end user
  will have to correctly set image property 'os_admin_user'.

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
  sahid-ferdjaoui

Work Items
----------

* Implement method set_admin_password
* Extend the method set_admin_password to read in image property for
  specific admin user

Dependencies
============

Libvirt 1.2.16

Testing
=======

* Unit tests will cover the new code
* The nova API is already covered by tests

Documentation Impact
====================

The new glance image property will need to be documented.

References
==========

* http://wiki.qemu.org/Features/QAPI/GuestAgent
