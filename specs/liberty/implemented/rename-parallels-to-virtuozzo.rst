..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.
 http://creativecommons.org/licenses/by/3.0/legalcode

==========================================
Rename Parallels Cloud Server to Virtuozzo
==========================================

https://blueprints.launchpad.net/nova/+spec/rename-pcs-to-virtuozzo

Problem description
===================

Within Parallels company rebranding, Parallels Cloud Server product, whose
support was merged in Kilo, was renamed to Virtuozzo [1]_.
Moreover, Parallels Service provider business was renamed
and became Odin [2]_. Thus, there was no Parallels name left for this product.

We need to address this change in nova/libvirt driver accordingly to avoid
confusion of users and make things be actual.

It is worth noting though, that Virtuozzo is based on opensource and free
OpenVz project and supporting Virtuozzo means supporting OpenVz also.

Use Cases
----------


Project Priority
-----------------

No priority defined for this change yet.

Proposed change
===============

Libvirt section in nova.conf will change ``virt_type`` from ``parallels`` to
``vz``. We set minimal required version of libvirt to work with ``vz``
virt_type to 1.3.0 since it is the first version that supports 'vz' uri.
The code will hold both names: ``parallels`` and ``vz`` for next release
cycle. In ``M`` release cycle there should be left only ``vz``.

Alternatives
------------

We can leave it as is and have ``parallels`` virt_type but this approach
will leave confusion for user forever.

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

Deployer can use libvirt virt_type ``parallels`` in Liberty release cycle,
but will have to switch to ``vz`` in next ``M`` release. This action is
going to be fulfilled by Virtuozzo deployment system.

Developer impact
----------------

None

Implementation
==============

Assignee(s)
-----------

Primary assignee: Maxim Nestratov <mnestratov@parallels.com>

Work Items
----------

* Test cases.
  Implementation: https://review.openstack.org/#/c/184311/
* Documentation.

Dependencies
============

None.

Testing
=======

Unit test cases need to be updated.
Already addressed in pending implementation.

Documentation Impact
====================

* OpenStack Configuration Reference.
  http://docs.openstack.org/kilo/config-reference/content/compute-nova-conf.html
* OpenStack Configuration Reference.
  http://docs.openstack.org/kilo/config-reference/content/list-of-compute-config-options.html

References
==========
.. [1] http://www.odin.com/products/virtuozzo/#tab4
.. [2] http://www.odin.com/odin/

