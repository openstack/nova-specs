..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

=====================================================
Add support for flavors with no local ephemeral disks
=====================================================

https://blueprints.launchpad.net/nova/+spec/flavor-root-disk-none

This feature adds the possibility to define a flavor,
that does not create any ephemeral disk locally on the hypervisor.
The proposal is to add a new flavor key ``local_disks``.
If ``local_disks`` is set to ``False``, no hypervisor-local root disk
or any other local ephemeral disk will be created.
A bootable volume needs to be created to launch an instance
from that flavor. All other additional disks can only be volume-based,
as well.

Problem description
===================

Currently there is no way to force root disk being on cinder and having
no hypervisor-local ephemeral disks at all.
Setting ``root_gb`` to 0 defaults in creating an ephemeral root disk
with the size of the glance image.

We do not want to have ephemeral disks locally on the hypervisor;
not on a local filesystem nor on a share mounted to /var/lib/nova/instances.
As these shares grow, they become unmaintainable and performance gets worse.
Storing the ephemeral root disk in the hypervisor's local filesystem is also
not a good idea, since consumer data on the root disk often cannot simply
be deleted.
Having more or less all block devices in cinder volumes gives us a unique
and flexible feature set for maintaining block storage of instances and
the instances themselves.

Use Cases
---------

The use case for End Users is to not create ephemeral (root) disks locally on
the hypervisor by accident.
When launching an instance from a flavor with disabled local disks,
the user will be informed to create a bootable volume in order to launch
the instance with that volume. The volume can be an existing one or a new
one, created upon the instance launch request via the block-device parameter.
The end user does not need to worry about disk placement; which impacts
instance migration, data persistence/loss, and/or shared storage performance.

The use case for deployers is to have the ability to prevent customers
from creating ephemeral (root) disks locally on the hypervisor. Deployers do
not have to worry to much about local HV filesystem sizing nor they do not
need to create one big share for /var/lib/nova/instances, which gets mounted on
all hypervisors. As that share grows it gets unmaintainable and performance is
gets worse. They do not have to deal with customer data loss on ephemeral
disks, stored on local hypervisor FS, in case of hypervisor outage.

Proposed change
===============

The scope of the change:

* new flavor key ``local_disks`` in the API
* new boolean column ``local_disks`` for table flavors
* default value for ``local_disks`` is True
* older microversions display value of 0 for ``root_gb``, ``ephemeral_gb`` and
  ``swap_gb``, if ``local_disks=False``
* newer microversions do not return the keys ``root_gb``, ``ephemeral_gb`` and
  ``swap_gb``, if ``local_disks=False``
* if ``local_disks=False`` is given ``root_gb``, ``ephemeral_gb`` and
  ``swap_gb`` are optional
* if ``local_disks=False`` is given ``root_gb``, ``ephemeral_gb`` and
  ``swap_gb`` are automatically set to 0, given values get ignored
* if ``local_disks`` is omitted or set to True, ``root_gb`` is mandatory again
* error, when flavor create request with ``local_disks=False`` and
  ``root_gb`` > 0 and/or ``emphemeral_gb`` > 0 and/or ``swap_gb`` > 0
* return descriptive exception, when flavor with ``local_disks=False`` and
  requested image larger than given blockdevice layout
* return descriptive exception, when flavor with ``local_disks=False`` and
  given block_device parameter includes ``dest_type`` 'local'
* return descriptive exception, when resizing instance from flavor with
  ``local_disks=True`` to flavor with ``local_disks=False``
* adjust api doc to include detailed description of ``local_disks`` key
* config-drive will not be touched by that change, config-drive will still
  reside on local HV disks, like libvirt.xml and console.log do

Alternatives
------------

The alternative is to always boot instances with the additional block_device
parameter and ``dest_type`` 'volume', to make sure (root) disks are on cinder
volumes and no hypervisor-local ephemeral disk gets created.
But this has the downside, that someone might forget it and ephemeral disks
get created locally on the HV.
There is no way to force users, that no ephemeral root disks are being created
on the hypervisor.

Data model impact
-----------------

* add new column ``local_disks`` type boolean to flavor table (default is True)

REST API impact
---------------

* introduce new api microversion which allows 'None' as disk value
* POST v2.1/<tenant_id>/flavors:

::

  {
      "flavor": {
          "name": "flavor_without_local_ephemeral_disks",
          "ram": 1024,
          "vcpus": 2,
          "local_disks": false,
      }
  }


* flavor show omits ``root_gb``, ``ephemeral_gb`` and ``swap_gb``,
  when ``local_disks=False``:

::

  {
      "flavor": {
          "OS-FLV-DISABLED:disabled": false,
          "local_disks": false,
          "os-flavor-access:is_public": true,
          "id": "1",
          "links": [
              {
                  "href": "http://openstack.example.com/v2.1/openstack/flavors/1",
                  "rel": "self"
              },
              {
                  "href": "http://openstack.example.com/openstack/flavors/1",
                  "rel": "bookmark"
              }
          ],
          "name": "m1.tiny",
          "ram": 512,
          "vcpus": 1
      }
  }


* with older microversions, ``root_gb``, ``ephemeral_gb`` and ``swap_gb`` will
  be returned with value 0, when ``local_disks=False``:

::

  {
      "flavor": {
          "OS-FLV-DISABLED:disabled": false,
          "local_disks": false,
          "disk": 0,
          "OS-FLV-EXT-DATA:ephemeral": 0,
          "os-flavor-access:is_public": true,
          "id": "1",
          "links": [
              {
                  "href": "http://openstack.example.com/v2.1/openstack/flavors/1",
                  "rel": "self"
              },
              {
                  "href": "http://openstack.example.com/openstack/flavors/1",
                  "rel": "bookmark"
              }
          ],
          "name": "m1.tiny",
          "ram": 512,
          "swap": 0,
          "vcpus": 1
      }
  }


* ``root_gb`` is no longer mandatory with ``local_disks=False``
* return 400 error when flavor has ``local_disks=False`` and no BD mapping
  given
* return 400 error when flavor has ``local_disks=False`` and ``dest_type``
  local given in BD mapping
* return 400 error when flavor has ``local_disks=True`` and instance resize to
  flavor ``local_disks=False`` requested
* return 400 error on flavor create, when ``local_disks=False`` and ``root_gb``
  and/or ``ephemeral_gb`` and/or ``swap_gb`` given

Security impact
---------------

None

Notifications impact
--------------------

None

Other end user impact
---------------------

End users need to provide a proper blockdevice mapping with ``dest_type``
volume, in order to use a flavor with ``local_disks=False``.

Performance Impact
------------------

None

Other deployer impact
---------------------

If a deployer doesn't want any ephemeral/local disk on the hypervisor nodes,
they just create flavors with ``local_disks=False`` and then all users of that
cloud have to provide a blockdevice mapping with ``dest_type`` 'volume' when
creating an instance.

Developer impact
----------------

None

Implementation
==============

Assignee(s)
-----------

Primary assignee:
  tpatzig

Work Items
----------

* create db column
* create api microversion with new key
* support ``local_disks=False`` for flavor show
* exception handling if ``local_disks=False`` in flavor and request contains
  local BD mapping
* adjust flavor unit test

Dependencies
============

None

Testing
=======

* Create flavor with ``local_disks=False``
* Boot instance with such flavor without volume
* Boot instance with such flavor with local BD mapping
* Boot instance with such flavor with volume

Documentation Impact
====================

http://docs.openstack.org/openstack-ops/content/flavors.html

API doc will be updated to include the new flavor option ``local_disks``.

References
==========

None

History
=======

.. list-table:: Revisions
   :header-rows: 1

   * - Release Name
     - Description
   * - Newton
     - Introduced
