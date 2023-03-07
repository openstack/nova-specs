..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

=============================================================================
Allow Manila shares to be directly attached to an instance when using libvirt
=============================================================================

https://blueprints.launchpad.net/nova/+spec/libvirt-virtiofs-attach-manila-shares

Manila is the OpenStack Shared Filesystems service. This spec will outline API,
database, compute and libvirt driver changes required in Nova to allow the
shares provided by Manila to be associated with and attached to instances.

Problem description
===================

At present users must manually connect to and mount shares provided by Manila
within their instances. As a result operators need to ensure that Manila
backend storage is routable from the guest subnets.

Use Cases
---------

- As an operator I want the Manila datapath to be separate to any tenant
  accessible networks.

- As a user I want to attach Manila shares directly to my instance and have a
  simple interface with which to mount them within the instance.

- As a user I want to detach a directly attached Manila share from my instance.

- As a user I want to track the Manila shares attached to my instance.

Proposed change
===============

This initial implementation will only provide support for attaching a share to
and later detaching a share from an existing ``SHUTOFF`` instance. The ability
to express attachments during the initial creation of an instance will not be
covered by this spec.

Support for move operations once a share is attached will also not
be covered by this spec, any requests to shelve, evacuate, resize, cold migrate
or live migrate an instance with a share attached will be rejected with a
HTTP409 response for the time being.

A new server ``shares`` API will be introduced under a new microversion. This
will list current shares, show their details and allow a share to be
attached or detached.

A new ``share_mapping`` database table and associated ``ShareMapping``
versioned objects will be introduced to capture details of the share
attachment. A base ShareMapping versioned object will be provided from which
virt driver and backend share specific objects can be derived providing
specific share attach and detach implementations.

.. note::

   One thing to note here is that no Manila state will be stored within Nova
   aside from export details used to initially attach the share. These details
   later being used when detaching the share. If the share is then reattached
   Nova will request fresh export details from Manila and store these in a
   new share attachment within Nova.

The libvirt driver will be extended to support the above with initial support
for cold attach and detach. Future work will aim to add live attach and detach
once `support lands in libvirt itself`__.

.. __: https://listman.redhat.com/archives/libvir-list/2021-October/msg00097.html

This initial libvirt support will target the basic NFS and slightly more
complex CephFS backends within Manila. Shares will be mapped through to the
underlying libvirt domains using ``virtio-fs``. This will require ``QEMU``
>=5.0 and ``libvirt`` >= 6.2 on the compute host and a kernel version of >= 5.4
within the instance guest OS.

Additionally this initial implementation will require that the associated
instances use `file backed memory`__ or `huge pages`__. This is a requirement
of `virtio-fs`__ as the ``virtiofsd`` service uses the `vhost-user`__ protocol
to communicate directly with the underlying guest.
(ref: `vhost-user documentation`__)

Two new compute capability traits and filters will be introduced to model an
individual compute's support for virtio-fs and file backed memory.
And while associating a share to an instance, a check will ensure the host
running the instance will support the

- ``COMPUTE_STORAGE_VIRTIO_FS`` trait

and either the

- ``COMPUTE_MEM_BACKING_FILE`` trait

or

that the instance is configured with ``hw:mem_page_size`` extra spec.

From an operator's point of view, it means
``COMPUTE_STORAGE_VIRTIO_FS`` support requires that
operators must upgrade all their compute nodes to the version supporting
shares using virtiofs.

``COMPUTE_MEM_BACKING_FILE`` support requires that operators configure one or
more hosts with file backed memory. Ensuring the instance will land on one of
these hosts can be achieved by creating an AZ englobing these hosts.
And then instruct users to deploy their instances in this AZ.
Alternatively, operators can guide the scheduler to choose a suitable host
by adding ``trait:COMPUTE_MEM_BACKING_FILE=required`` as an extra spec or
image property.

.. __: https://docs.openstack.org/nova/latest/admin/file-backed-memory.html
.. __: https://docs.openstack.org/nova/latest/admin/huge-pages.html
.. __: https://virtio-fs.gitlab.io/
.. __: https://libvirt.org/kbase/virtiofs.html#other-options-for-vhost-user-memory-setup
.. __: https://qemu-project.gitlab.io/qemu/interop/vhost-user.html

Users will be able to mount the attached shares using a mount tag, this is
either the share UUID from Manila or a string provided by the users with their
request to attach the share.

.. code-block:: shell

    user@instance $ mount -t virtiofs $tag /mnt/mount/path

A previously discussed ``os-share`` library will not be created with this
initial implementation but could be in the future if the logic required to
mount and track shares on the underlying host is also required by other
projects. For the time being `existing code within the libvirt driver`__ used
to track filesystem host mounts used by volumes hosted on ``remoteFS`` based
storage (such as NFS, SMB etc) will be reused as much as possible.

.. __: https://github.com/openstack/nova/blob/8f250f50446ca2d7aa84609d5144088aa4cded78/nova/virt/libvirt/volume/mount.py#L152-L174


Share mapping status::

                       +----------------------------------------------------+   Reboot VM
      Start VM         |                                                    | --------------+
      Share mounted    |                       active                       |               |
  +------------------> |                                                    | <-------------+
  |                    +----------------------------------------------------+
  |                      |                   |             |
  |                      | Stop VM           |             |
  |                      | Fail to umount    |             |
  |                      v                   |             |
  |                    +------------------+  |             |
  |                    |      error       | <+-------------+-------------------+
  |                    +------------------+  |             |                   |
  |                      |                   |             |                   |
  |                      | Detach share or   |             |                   |
  |                      | delete VM         | Delete VM   |                   |
  |                      v                   |             |                   |
  |                    +------------------+  |             |                   |
  |    +-------------> |        φ         | <+             |                   | Start VM
  |    |               +------------------+                |                   | Fail to mount
  |    |                 |                                 |                   |
  |    | Detach share    |                                 | Stop VM           |
  |    | or delete VM    | Attach share                    | Share unmounted   |
  |    |                 v                                 v                   |
  |    |               +----------------------------------------------------+  |
  |    +-------------- |                      inactive                      | -+
  |                    +----------------------------------------------------+
  |                      |
  +----------------------+


φ
  means no entry in the database. No association between a share and a server.

Attach share
  means POST /servers/{server_id}/shares

Detach share
  means DELETE /servers/{server_id}/shares

This chart describe the share mapping status (nova), this is independent from
the status of the Manila share.

Share attachment/detachment can only be done if the VM state is ``STOPPED``
or ``ERROR``.
These are operations only on the database, and no RPC calls will be required
to the compute API. This is an intentional design for this spec.
As a result, this could lead to situation where the VM start operation fails
as an underlying share attach fails.

Mount operation will be done when the share is not mounted on the compute host.
If a previous share would have been mounted on the compute host for another
server, then it will attempt to mount it and a warning will be logged that
the share was already mounted.

Umount operation will be really done when the share is mounted and not used
anymore by another server.

With the above mount and umount operation, the state is stored in memory and
do not require a lookup in the database.

The share will be mounted on the compute host using read/write mode.
Read-only will not be supported as a share could not be mounted read-only
and read/write at the same time. If the user wants to mount the share
read-only, it will have to do it in the VM fstab.

Manila share removal issue:

Despite a share being used by instances, it can be removed by the user.
As a result, the instances will lose access to the data and might cause
difficulties in removing the missing share and fixing the instance.
This is an identified issue that requires Manila modifications.
A solution was identified with the Manila team to attach metadata to the share
access-allow policy that will lock the share and prevent its deletion until
the lock is not removed.
If the above Manila change can land in the Zed cycle,
the proposal here is to use the lock mechanism in Nova.
Otherwise, clearly document the known issue as unsupported and warn users that
they should take care and avoid this pitfall.

Instance metadata:

Add instace shares in the instance metadata.
Extend DeviceMetadata with ShareMetadata object containing `shareId` and
`tag` used to mount the virtiofs on an instance by the user.
See :ref:`bobcat-other-end-user-impact`.

Alternatives
------------

The only alternative is to continue with the current situation where users must
mount the shares within their instances manually. The downside being that these
instances must have access to the storage network used by the Manila backends.

REST API impact
---------------

A new server level ``shares`` API will be introduced under a new microversion
with the following methods:

* GET ``/servers/{server_id}/shares``

List all shares attached to an instance.

Return Code(s): 200,400,401,403,404

.. code-block:: json

    {
        "shares": [
            {
                "shareId": "48c16a1a-183f-4052-9dac-0e4fc1e498ad",
                "status": "active",
                "tag": "foo"
            },
            {
                "shareId": "e8debdc0-447a-4376-a10a-4cd9122d7986",
                "status": "active",
                "tag": "bar"
            }
        ]
    }

* GET ``/servers/{server_id}/shares/{shareId}``

Show details of a specific share attached to an instance.

Return Code(s): 200,400,401,403,404

.. code-block:: json

    {
        "share": {
            "shareId": "e8debdc0-447a-4376-a10a-4cd9122d7986",
            "status": "active",
            "tag": "bar"
        }
    }

PROJECT_ADMIN will be able to see details of the attachment id and export
location stored within Nova:

.. code-block:: json

    {
        "share": {
            "attachmentId": "715335c1-7a00-4dfe-82df-9dc2a67bd8bf",
            "shareId": "e8debdc0-447a-4376-a10a-4cd9122d7986",
            "status": "active",
            "tag": "bar",
            "export_location": "server.com/nfs_mount,foo=bar"
        }
    }

* ``POST /servers/{server_id}/shares``

Attach a share to an instance.

Prerequisite(s):

- Instance much be in the ``SHUTOFF`` state.
- Instance should have the required capabilities to enable
  virtiofs (see above).

This is a synchronous API. As a result, the VM share attachement state
is defined in the database and set as inactive.
Then, power on the VM will do the required operations to attach the share and
set it as active if there are no errors.

Return Code(s): 202,400,401,403,404,409

Request body:

.. note::

   ``tag`` will be an optional request parameter in the request body, when not
   provided it will be the shareId(UUID) as always provided in the request.

   ``tag`` if povided by the user must be an ASCII string with a maximum
   lenght of 64 bytes.


.. code-block:: json

    {
        "share": {
            "shareId": "e8debdc0-447a-4376-a10a-4cd9122d7986"
        }
    }

Response body:

.. code-block:: json

    {
        "share": {
            "shareId": "e8debdc0-447a-4376-a10a-4cd9122d7986",
            "status": "active",
            "tag": "e8debdc0-447a-4376-a10a-4cd9122d7986"
        }
    }

* ``DELETE /servers/{server_id}/shares/{shareId}``

Detach a share from an instance.

Prerequisite(s): Instance much be in the ``SHUTOFF`` or ``ERROR`` state.

Return Code(s): 202,400,401,403,404,409

Data model impact
-----------------

A new ``share_mapping`` database table will be introduced.

* ``id`` - Primary key autoincrement

* ``uuid`` - Unique UUID to identify the particular share attachment

* ``instance_uuid`` - The UUID of the instance the share will be attached to

* ``share_id`` - The UUID of the share in Manila

* ``status`` - The status of the share attachment within Nova
  (``active``, ``inactive``, ``error``)

* ``tag`` - The device tag to be used by users to mount the share within
  the instance.

* ``export_location`` - The export location used to attach the share to the
  underlying host

* ``share_proto`` - The Shared File Systems protocol (``NFS``, ``CEPHFS``)

A new base ``ShareMapping`` versioned object will be introduced to encapsulate
the above database entries and to be used as the parent class of specific virt
driver implementations.

The database field `status` and `share_proto` values will not be enforced
using enums allowing future changes and avoid database migrations.
However, to make code more robust, enums will be defined on the object fields.

Fields containing text will use String and not Text type in the database schema
to limit the column width and be stored inline in the database.

This base ``ShareMapping`` object will provide stub ``attach`` and ``detach``
methods that will need to be implemented by any child objects.

New ``ShareMappingLibvirt``, ``ShareMappingLibvirtNFS`` and
``ShareMappingLibvirtCephFS`` objects will be introduced as part of the libvirt
implementation.

Security impact
---------------

The ``export_location`` JSON blob returned by Manila and used to mount the
share to the host and the host filesystem location should
not be logged by Nova and only accessible by default through the API by admins.

Notifications impact
--------------------

New notifications will be added:

* One to add new notifications for share attach and share detach.
* One to extend the instance update notification with the share mapping
  information.

Share mapping in the instance payload will be optional and controlled via the
``include_share_mapping`` notification configuration parameter. It will be
disabled by default.

Proposed payload for attached and detached notification will be the same as
the one returned by the show command with admin rights.

.. code-block:: json

  {
      "share": {
          "instance_uuid": "7754440a-1cb7-4d5b-b357-9b37151a4f2d",
          "attachmentId": "715335c1-7a00-4dfe-82df-9dc2a67bd8bf",
          "shareId": "e8debdc0-447a-4376-a10a-4cd9122d7986",
          "status": "active",
          "tag": "bar",
          "export_location": "server.com/nfs_mount,foo=bar"
      }
  }

Proposed instance payload for instance updade, will be the list of share
attached to this instance.

.. code-block:: json

  {
      "shares":
      [
          {
              "instance_uuid": "7754440a-1cb7-4d5b-b357-9b37151a4f2d",
              "attachmentId": "715335c1-7a00-4dfe-82df-9dc2a67bd8bf",
              "shareId": "e8debdc0-447a-4376-a10a-4cd9122d7986",
              "status": "active",
              "tag": "bar",
              "export_location": "server.com/nfs_mount,foo=bar"
          },
          {
              "instance_uuid": "7754440a-1cb7-4d5b-b357-9b37151a4f2d",
              "attachmentId": "715335c1-7a00-4dfe-82df-ffffffffffff",
              "shareId": "e8debdc0-447a-4376-a10a-4cd9122d7987",
              "status": "active",
              "tag": "baz",
              "export_location": "server2.com/nfs_mount,foo=bar"
          }
      ]
  }

.. _bobcat-other-end-user-impact:

Other end user impact
---------------------

Users will need to mount the shares within their guestOS using the returned
``tag``.

Users could use the instance metadata to discover and auto mount the share.

Performance Impact
------------------

Through the use of ``vhost-user`` ``virtio-fs`` should have near local
(mounted) file system performance within the guestOS.
While there will be near local performance between the vm and host,
the actual performance will be limited by the network performance of
the network file share protocol and hardware.

Other deployer impact
---------------------

None

Developer impact
----------------

None

Upgrade impact
--------------

A new compute service version and capability traits will be introduced to
ensure both the compute service and underlying virt stack are new enough to
support attaching a share via ``virtio-fs`` before the request is accepted.

Implementation
==============

Assignee(s)
-----------

Primary assignee:
  uggla (rene.ribaud)

Other contributors:
  lyarwood (initial contributor)

Feature Liaison
---------------

Feature liaison:
  uggla

Work Items
----------

- Add new capability traits within os-traits
- Add support within the libvirt driver for cold attach and detach
- Add new shares API and microversion

Dependencies
============

None

Testing
=======

- Functional libvirt driver and API tests
- Integration Tempest tests

Documentation Impact
====================

Extensive admin and user documentation will be provided.

References
==========

History
=======

.. list-table:: Revisions
   :header-rows: 1

   * - Release Name
     - Description
   * - Yoga
     - Introduced
   * - Zed
     - Reproposed
   * - Antelope
     - Reproposed
   * - Bobcat
     - Reproposed
