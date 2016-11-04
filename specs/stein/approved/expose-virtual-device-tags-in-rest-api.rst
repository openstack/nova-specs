..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

======================================
Expose virtual device tags in REST API
======================================

https://blueprints.launchpad.net/nova/+spec/expose-virtual-device-tags-in-rest-api

The 2.32 microversion allows creating a server with tagged block devices
and virtual interfaces (ports) and the 2.49 microversion allows specifying
a tag when attaching volumes and ports, but there is no way to get those
tags out of the REST API. This spec proposes to expose the block device
mapping and virtual interface tags in the REST API when listing volume
attachments and ports for a given server.


Problem description
===================

It is possible to attach volumes and ports to a server with tags but there
is nothing in the REST API that allows a user to read those back. The virtual
device tags are available *within* the guest VM via the config drive or
metadata API service, but not the front-end compute REST API.

Furthermore, correlating volume attachments to BlockDeviceMapping objects
via tag has come up in the `Remove device from volume attach requests`_ spec
as a way to replace reliance on the otherwise unused ``device`` field to
determine ordering of block devices within the guest.

Using volume attachment tags was also an option discussed in the
`Detach and attach boot volumes`_ spec as a way to indicate which volume
was the root volume attached to the server without relying on the
server ``OS-EXT-SRV-ATTR:root_device_name`` field.

.. _Remove device from volume attach requests: https://review.openstack.org/600628/
.. _Detach and attach boot volumes: https://review.openstack.org/600628/

Use Cases
---------

As a user, I want to correlate information, based on tags, to the volumes and
ports attached to my server.

Proposed change
===============

In a new microversion, expose virtual device tags in the REST API response
when showing volume attachments and attached ports.

See the `REST API impact`_ section for details on route and response changes.

**Technical / performance considerations**

When showing attached volume tags, there would really be no additional effort
in exposing the tag since we already query the database for a
BlockDeviceMappingList per instance.

However, the ``os-interface`` port tags present a different challenge. The
``GET /servers/{server_id}/os-interface`` and
``GET /servers/{server_id}/os-interface/{port_id}`` APIs are today simply
proxies to the neutron networking APIs to list ports attached to an instance
and show details about a port attached to an instance, respectively.

The device tag for a port attached to an instance is not stored in neutron,
it is stored in the nova cell database ``virtual_interfaces`` table. So the
problem we have is one of performance when listing ports attached to a server
and we want to show tags because we would have to query both the neutron API
to list ports and then the ``virtual_interfaces`` table for the instance to
get the tags. We have two options:

1. Accept that when listing ports for a single instance, doing one more DB
   query to get the tags is not that big of an issue.

2. Rather than proxy the calls to neutron, we could rely on the instance
   network info cache to provide the details. That might be OK except we
   currently do not store the tags in the info cache, so for any existing
   instance the tags would not be shown, unless we did a DB query to look
   for them and heal the cache.

Given the complications with option 2, this spec will just use option 1.

**Non-volume BDMs**

It should be noted that swap and ephemeral block devices can also have
tags when the server is created, however there is nothing in the API
today which exposes those types of BDMs; the API only exposes volume BDMs.
As such, this spec does not intend to expose non-volume block device mapping
tags. It is possible that in the future if a kind of
``GET /servers/{server_id}/disks`` API were added we could expose swap and
ephemeral block devices along with their tags, but that is out of scope
for this spec.

Alternatives
------------

In addition to showing the tags in the ``os-volume_attachments`` and
``os-interface`` APIs, we could also modify the server show/list view builder
to provide tags in the server resource ``os-extended-volumes:volumes_attached``
and ``addresses`` fields. This would be trivial to do for showing attached
volume tags since we already query the DB per instance to get the BDMs, but as
noted in the `Proposed change`_ section, it would be non-trivial for port tags
since those are not currently stored in the instance network info cache which
is used to build the ``addresses`` field response value. And it would be odd
to show the attached volume tags in the server response but not the virtual
interface tags. We could heal the network info cache over time, but that
seems unnecessarily complicated when the proposed change already provides a
way to get the tag information for all volumes/ports attached to a given
server resource.

We could also take this opportunity to expose other fields on the
BlockDeviceMapping which are inputs when creating a server, like
``boot_index``, ``volume_type``, ``source_type``, ``destination_type``,
``guest_format``, etc. For simplicity, that is omitted from the proposed
change since it's simpler to just focus on tag exposure for multiple types
of resources.

Data model impact
-----------------

None.

REST API impact
---------------

There are two API resource routes which would be changed. In all cases,
if the block device mapping or virtual interface record does not have a tag
specified, the response value for the ``tag`` key will be ``None``.

os-volume_attachments
~~~~~~~~~~~~~~~~~~~~~

A ``tag`` field will be added to the response for each of the following APIs.

* ``GET /servers/{server_id}/os-volume_attachments (list)``

  .. code-block:: json

     {
       "volumeAttachments": [{
         "device": "/dev/sdd",
         "id": "a26887c6-c47b-4654-abb5-dfadf7d3f803",
         "serverId": "4d8c3732-a248-40ed-bebc-539a6ffd25c0",
         "volumeId": "a26887c6-c47b-4654-abb5-dfadf7d3f803",
         "tag": "os"
       }]
     }

* ``GET /servers/{server_id}/os-volume_attachments/{volume_id} (show)``

  .. code-block:: json

     {
       "volumeAttachment": {
         "device": "/dev/sdd",
         "id": "a26887c6-c47b-4654-abb5-dfadf7d3f803",
         "serverId": "2390fb4d-1693-45d7-b309-e29c4af16538",
         "volumeId": "a26887c6-c47b-4654-abb5-dfadf7d3f803",
         "tag": "os"
       }
     }

* ``POST /servers/{server_id}/os-volume_attachments (attach)``

  .. code-block:: json

     {
       "volumeAttachment": {
         "device": "/dev/vdb",
         "id": "c996dd74-44a0-4fd1-a582-a14a4007cc94",
         "serverId": "2390fb4d-1693-45d7-b309-e29c4af16538",
         "volumeId": "c996dd74-44a0-4fd1-a582-a14a4007cc94",
         "tag": "data"
       }
     }


os-interface
~~~~~~~~~~~~

A ``tag`` field will be added to the response for each of the following APIs.

* ``GET /servers/{server_id}/os-interface (list)``

  .. code-block:: json

     {
       "interfaceAttachments": [{
         "fixed_ips": [{
           "ip_address": "192.168.1.3",
           "subnet_id": "f8a6e8f8-c2ec-497c-9f23-da9616de54ef"
         }],
         "mac_addr": "fa:16:3e:4c:2c:30",
         "net_id": "3cb9bc59-5699-4588-a4b1-b87f96708bc6",
         "port_id": "ce531f90-199f-48c0-816c-13e38010b442",
         "port_state": "ACTIVE",
         "tag": "public"
       }]
     }

* ``GET /servers/{server_id}/os-interface/{port_id} (show)``

  .. code-block:: json

     {
       "interfaceAttachment": {
         "fixed_ips": [{
           "ip_address": "192.168.1.3",
           "subnet_id": "f8a6e8f8-c2ec-497c-9f23-da9616de54ef"
         }],
         "mac_addr": "fa:16:3e:4c:2c:30",
         "net_id": "3cb9bc59-5699-4588-a4b1-b87f96708bc6",
         "port_id": "ce531f90-199f-48c0-816c-13e38010b442",
         "port_state": "ACTIVE",
         "tag": "public"
       }
     }

* ``POST /servers/{server_id}/os-interface (attach)``

  .. code-block:: json

     {
       "interfaceAttachment": {
         "fixed_ips": [{
           "ip_address": "192.168.1.4",
           "subnet_id": "f8a6e8f8-c2ec-497c-9f23-da9616de54ef"
         }],
         "mac_addr": "fa:16:3e:4c:2c:31",
         "net_id": "3cb9bc59-5699-4588-a4b1-b87f96708bc6",
         "port_id": "ce531f90-199f-48c0-816c-13e38010b443",
         "port_state": "ACTIVE",
         "tag": "management"
       }
     }


Security impact
---------------

None.

Notifications impact
--------------------

The ``BlockDevicePayload`` object already exposes BDM tags for
versioned notifications. The ``IpPayload`` object does not expose tags
since they are not in the instance network info cache, but these payloads
are only exposed via the ``InstancePayload`` and like the ``servers`` API
we will not make additional changes to try and show the tags for the resources
nested within the server (InstancePayload) body. This could be done in the
future if desired, potentially with a configuration option like
``[notifications]/bdms_in_notifications``, but it is out of scope for this
spec.

Other end user impact
---------------------

python-novaclient and python-openstackclient will be updated as necessary
to support the new microversion. This likely just means adding a new ``Tag``
column in CLI output when listing attached volumes and ports.

Performance Impact
------------------

There will be a new database query to the ``virtual_interfaces`` table when
showing device tags for ports attached to a server. This should have a minimal
impact to API response times though.

Other deployer impact
---------------------

None.

Developer impact
----------------

None.

Upgrade impact
--------------

None.


Implementation
==============

Assignee(s)
-----------

Primary assignee:
  Matt Riedemann <mriedem.os@gmail.com> (mriedem)

Work Items
----------

Implement a new microversion and use that to determine if a new ``tag``
field should be in the ``os-volume_attachments`` and ``os-interface`` API
responses when listing/showing/attaching volumes/ports to a server.


Dependencies
============

None.


Testing
=======

Functional API samples tests should be sufficient coverage of this feature.


Documentation Impact
====================

The compute API reference will be updated to note the ``tag`` field in the
response for the ``os-volume_attachments`` and ``os-interface`` APIs.

References
==========

This was originally discussed at the `Ocata summit`_. It came up again at the
`Rocky PTG`_.

Related specs:

* Remove ``device`` from volume attach API: https://review.openstack.org/452546/
* Detach/attach boot volume: https://review.openstack.org/600628/

.. _Ocata summit: https://etherpad.openstack.org/p/ocata-nova-summit-api
.. _Rocky PTG: https://etherpad.openstack.org/p/nova-ptg-rocky


History
=======

.. list-table:: Revisions
   :header-rows: 1

   * - Release Name
     - Description
   * - Pike
     - Originally proposed but abandoned
   * - Stein
     - Re-proposed
