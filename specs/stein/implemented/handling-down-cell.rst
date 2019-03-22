..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

==========================================
Handling a down cell
==========================================

https://blueprints.launchpad.net/nova/+spec/handling-down-cell

This spec aims at addressing the behavioural changes that are required to
support some of the basic nova operations like listing of instances and
services when a cell goes down.

Problem description
===================

Currently in nova when a cell goes down (for instance if the cell DB is not
reachable) basic functionalities like ``nova list`` and ``nova service-list``
do not work and return an API error message. However a single cell going down
should not stop these operations from working for the end users and operators.
Another issue is while calculating quotas during VM creations, the resources
of the down cell are not taken into account and the ``nova boot`` operation is
permitted into the cells which are up. This may result in incorrect quota
reporting for a particular project during boot time which may have implications
when the down cell comes back.

Use Cases
---------

The specific use cases that are being addressed in the spec include:

#. ``nova list`` should work even if a cell goes down. This can be partitioned
   into two use cases:

   #. The user has no instances in the down cell: Expected behaviour would be
      for everything to work as normal. This has been fixed through
      `smart server listing`_ if used with the right config options.
   #. The user has instances in the down cell: This needs to be gracefully
      handled which can be split into two stages:

      #. We just skip the down cell and return results from the cells that are
         available instead of returning a 500 which has been fixed through
         `resilient server listing`_.
      #. Instead of skipping the down cell, we build on (modify) the existing
         API response to return a minimalistic construct. This will be fixed in
         this spec.

#. ``nova show`` should also return a minimalistic construct for instances in
   the down cell similar to ``nova list``.

#. ``nova service-list`` should work even if a cell goes down. The solution can
   be split into two stages:

   #. We skip the down cell and end up displaying all the services from the
      other cells as was in cells_v1 setup. This has been fixed through
      `resilient service listing`_.
   #. We handle this gracefully for the down cell. This will be fixed through
      this spec by creating a minimalistic construct.

#. ``nova boot`` should not succeed if that project has any living VMs in the
   down cell until an all-cell-iteration independent solution for quota
   calculation is implemented through `quotas using placement`_.

Proposed change
===============

This spec proposes to add a new ``queued_for_delete`` column in the
``nova_api.instance_mappings`` table as discussed in the
`cells summary in Dublin PTG`_. This column would be of type Boolean which by
default will be False and upon the deletion (normal/local/soft) of the
respective instance, will be set to True. In the case of soft delete, if the
instance is restored, then the value of the column will be set to False again.
The corresponding ``queued_for_delete`` field will be added in the
InstanceMapping object.

Listing of instances and services from the down cell will return a
`did_not_respond_sentinel`_ object from the scatter-gather utility. Using this
response we can know if a cell is down or not and accordingly modify the
listing commands to work in the following manner for those records which are
from the down cell:

#. ``nova list`` should return a minimalistic construct from the available
   information in the API DB which would include:

   #. created_at, instance_uuid and project_id from the instance_mapping table.
   #. status of the instance would be "UNKNOWN" which would be the major
      indication that the record for this instance is partial.
   #. rest of the field keys will be missing.

   See the `Edge Cases`_ section for more info on running this command with
   filters, marker, sorting and paging.

#. ``nova show`` should return a minimalistic construct from the available
   information in the API DB which would be similar to ``nova list``. If
   ``GET /servers/{id}`` cannot reach the cell DB, we can look into the
   instance_mapping and request_spec table for the instance details which would
   include:

   #. instance_uuid, created_at and project_id from the instance_mapping table.
   #. status of the instance would be "UNKNOWN" which would be the major
      indication that the record for this instance is partial.
   #. user_id, flavor, image and availability_zone from the request_spec table.
   #. power_state is set to NOSTATE.
   #. rest of the field keys will be missing.

#. ``nova service-list`` should return a minimalistic construct from the
   available information in the API DB which would include:

   #. host and binary from the host_mapping table for the compute services.
   #. rest of the field keys will be missing.

   Note that if cell0 goes down the controller services will not be listed.

#. ``nova boot`` should not succeed if the requesting project has living VMs in
   the down cell. So if the scatter-gather utility returns a
   did_not_respond_sentinel while calculating quotas, we have to go and check
   if this project has living instances in the down cell from the
   instance_mapping table and prevent the boot request if it has. However it
   might not be desirable to block VM creation for users having VMs in multiple
   cells if a single cell goes down. Hence a new policy rule
   ``os_compute_api:servers:create:cell_down`` which defaults to
   ``rule:admin_api`` can be added by which the ability to create instances
   when a project has instances in a down cell can be controlled between
   users/admin. Using this deployments can configure their setup in whichever
   way they desire.

For the 1st, 2nd and 4th operations to work when a cell is down, we need to
have the information regarding if an instance is in SOFT_DELETED/DELETED state
in the API DB so that the living instances can be distinguished from the
deleted ones which is why we add the new column ``queued_for_delete``.

In order to prevent the client side from complaining about missing keys, we
would need a new microversion that would accept the above stated minimal
constructs for the servers in the down cells into the same list of full
constructs of the servers in the up cells. In future we could use a caching
mechanism to have the ability to fill in the down cell instances information.

Note that all other non-listing operations like create and delete will simply
not work for the servers in the down cell since one cannot clearly do anything
about it if the cell database is not reachable. They will continue to return
500 as is the present scenario.

Edge Cases
----------

* Filters: If the user is listing servers using filters the results from the
  down cell will be skipped and no minimalistic construct will be provided
  since there is no way of validating the filtered results from the down cell
  if the value of the filter key itself is missing. Note that by default
  ``nova list`` uses the ``deleted=False`` and   ``project_id=tenant_id``
  filters and since we know both of these values from the instance_mapping
  table, they will be the only allowed filters. Hence only doing ``nova list``
  and ``nova list --minimal`` will show minimalistic results for the down cell.
  Other filters like ``nova list --deleted`` or ``nova list --host xx`` will
  skip the results for the down cell.

* Marker: If the user does ``nova list --marker`` it will fail with a 500 if
  the marker is in the down cell.

* Sorting: We ignore the down cell just like we do for filters since there is
  no way of obtaining valid results from the down cell with missing key info.

* Paging: We ignore the down cell. For instance if we have three cells A (up),
  B (down) and C (up) and if the marker is half way in A, we would get the
  rest half of the results from A, all the results from C and ignore cell B.

Alternatives
------------

* An alternative to adding the new column in the instance_mappings table is to
  have the deleted information in the respective RequestSpec record, however it
  was decided at the PTG to go ahead with adding the new column in the
  instance_mappings table as it is more appropriate. For the main logic there
  is no alternative solution other than having the deleted info in the API DB
  if the listing operations have to work when a cell goes down.

* Without a new microversion, include 'shell' servers in the response when
  listing over down cells which would have UNKNOWN values for those keys
  whose information is missing. However the client side would not be able to
  digest the response with "UNKNOWN" values. Also it is not possible to assign
  "UNKNOWN" to all the fields since not all of them are of string types.

* With a new microversion include the set of server uuids in the down cells
  in a new top level API response key called ``unavailable_servers`` and treat
  the two lists (one for the servers from the up cells and other for the
  servers from the down cells) separately. See `POC for unavailable_servers`_
  for more details.

* Using searchlight to backfill when there are down cells. Check
  `listing instances using Searchlight`_ for more details.

* Adding backup DBs for each cell database which would act as read-only copies
  of the original DB in times of crisis, however this would need massive
  syncing and may fetch stale results.

Data model impact
-----------------

A nova_api DB schema change will be required for adding the
``queued_for_delete`` column of type Boolean to the
``nova_api.instance_mappings`` table. This column will be set to False by
default.

Also, the ``InstanceMapping`` object will have a new field called
``queued_for_delete``. An online data migration tool will be added to populate
this field for existing instance_mappings. This tool would basically go over
the instance records in all the cells, and if the vm_state of the instance is
either DELETED or SOFT_DELETED, it will update the ``queued_for_delete`` to
True else leave it at its default value.

REST API impact
---------------

When a cell is down, we currently skip that cell and this spec aims at
giving partial info for ``GET /servers``, ``GET /os-services``,
``GET /servers/detail`` and ``GET /servers/{server_id}`` REST APIs.
There will be a new microversion for the client to recognise missing keys and
NULL values for certain keys in the response.

An example server response for ``GET /servers/detail`` is given below which
includes one available server and one unavailable server.

JSON response body example::

    {
        "servers": [
            {
                "OS-EXT-STS:task_state": null,
                "addresses": {
                    "public": [
                        {
                            "OS-EXT-IPS-MAC:mac_addr": "fa:xx:xx:xx:xx:1a",
                            "version": 4,
                            "addr": "1xx.xx.xx.xx3",
                            "OS-EXT-IPS:type": "fixed"
                        },
                        {
                            "OS-EXT-IPS-MAC:mac_addr": "fa:xx:xx:xx:xx:1a",
                            "version": 6,
                            "addr": "2sss:sss::s",
                            "OS-EXT-IPS:type": "fixed"
                        }
                    ]
                },
                "links": [
                    {
                        "href": "http://1xxx.xxx.xxx.xxx/compute/v2.1/servers/b546af1e-3893-44ea-a660-c6b998a64ba7",
                        "rel": "self"
                    },
                    {
                        "href": "http://1xx.xxx.xxx.xxx/compute/servers/b546af1e-3893-44ea-a660-c6b998a64ba7",
                        "rel": "bookmark"
                    }
                ],
                "image": {
                    "id": "9da3b809-2998-4ada-8cc6-f24bc0b6dd7f",
                    "links": [
                        {
                            "href": "http://1xx.xxx.xxx.xxx/compute/images/9da3b809-2998-4ada-8cc6-f24bc0b6dd7f",
                            "rel": "bookmark"
                        }
                    ]
                },
                "OS-EXT-SRV-ATTR:user_data": null,
                "OS-EXT-STS:vm_state": "active",
                "OS-EXT-SRV-ATTR:instance_name": "instance-00000001",
                "OS-EXT-SRV-ATTR:root_device_name": "/dev/vda",
                "OS-SRV-USG:launched_at": "2018-06-29T15:07:39.000000",
                "flavor": {
                    "ephemeral": 0,
                    "ram": 64,
                    "original_name": "m1.nano",
                    "vcpus": 1,
                    "extra_specs": {},
                    "swap": 0,
                    "disk": 0
                },
                "id": "b546af1e-3893-44ea-a660-c6b998a64ba7",
                "security_groups": [
                    {
                        "name": "default"
                    }
                ],
                "OS-SRV-USG:terminated_at": null,
                "os-extended-volumes:volumes_attached": [],
                "user_id": "187160b0afe041368258c0b195ab9822",
                "OS-EXT-SRV-ATTR:hostname": "surya-probes-001",
                "OS-DCF:diskConfig": "MANUAL",
                "accessIPv4": "",
                "accessIPv6": "",
                "OS-EXT-SRV-ATTR:reservation_id": "r-uxbso3q4",
                "progress": 0,
                "OS-EXT-STS:power_state": 1,
                "OS-EXT-AZ:availability_zone": "nova",
                "config_drive": "",
                "status": "ACTIVE",
                "OS-EXT-SRV-ATTR:ramdisk_id": "",
                "updated": "2018-06-29T15:07:39Z",
                "hostId": "e8dcf7ab9762810efdec4307e6219f85a53d5dfe642747c75a87db06",
                "OS-EXT-SRV-ATTR:host": "cn1",
                "description": null,
                "tags": [],
                "key_name": null,
                "OS-EXT-SRV-ATTR:kernel_id": "",
                "OS-EXT-SRV-ATTR:hypervisor_hostname": "cn1",
                "locked": false,
                "name": "surya-probes-001",
                "OS-EXT-SRV-ATTR:launch_index": 0,
                "created": "2018-06-29T15:07:29Z",
                "tenant_id": "940f47b984034c7f8f9624ab28f5643c",
                "host_status": "UP",
                "trusted_image_certificates": null,
                "metadata": {}
            },
            {
                "created": "2018-06-29T15:07:29Z",
                "status": "UNKNOWN",
                "tenant_id": "940f47b984034c7f8f9624ab28f5643c",
                "id": "bcc6c6dd-3d0a-4633-9586-60878fd68edb",
            }
        ]
    }

Security impact
---------------

None.

Notifications impact
--------------------

None.

Other end user impact
---------------------

When a cell DB cannot be connected, ``nova list``, ``nova show`` and
``nova service-list`` will work with the records from the down cell not having
all the information. When these commands are used with filters/sorting/paging,
the output will totally skip the down cell and return only information from the
up cells. As per default policy ``nova boot`` will not work if that tenant_id
has any living instances in the down cell.

Performance Impact
------------------

There will not be any major impact on performance in normal situations. However
when a cell is down, during show/list/boot time there will be a slight
performance impact because of the extra check into the instance_mapping and/or
request_spec tables and the time required for the construction of a
minimalistic record in case a did_not_respond_sentinel is received from the
scatter-gather utility.

Other deployer impact
---------------------

None.

Developer impact
----------------

None.

Upgrade impact
--------------

Since there will be a change in the api DB schema, the ``nova-manage api_db
sync`` command will have to be run to update the instance_mappings table. The
new online data migration tool that will be added to populate the new column
will have to be run.

Implementation
==============

Assignee(s)
-----------

Primary assignee:
  <tssurya>

Other contributors:
  <belmoreira>

Work Items
----------

#. Add a new column ``queued_for_delete`` to nova_api.instance_mappings table.
#. Add a new field ``queued_for_delete`` to InstanceMapping object.
#. Add a new online migration tool for populating ``queued_for_delete`` of
   existing instance_mappings.
#. Handle ``nova list`` gracefully on receiving a timeout from a cell `here`_.
#. Handle ``nova service-list`` gracefully on receiving a timeout from a cell.
#. Handle ``nova boot`` during quota calculation in `quota calculation code`_
   when the result is a did_not_respond_sentinel or raised_exception_sentinel.
   Implement the extra check into the instance_mapping table to see if the
   requesting project has any living instances in the down cell and block the
   request accordingly.

Dependencies
============

None.

Testing
=======

Unit and functional tests for verifying the working when a
did_not_respond_sentinel is received.


Documentation Impact
====================

Update the description of the Compute API reference with regards to these
commands to include the meaning of UNKNOWN records.

References
==========

.. _smart server listing: https://review.openstack.org/#/c/509003/

.. _resilient server listing: https://review.openstack.org/#/c/575734/

.. _resilient service listing: https://review.openstack.org/#/c/568271/

.. _quotas using placement: https://review.openstack.org/#/c/509042/

.. _cells summary in Dublin PTG: http://lists.openstack.org/pipermail/openstack-dev/2018-March/128304.html

.. _did_not_respond_sentinel: https://github.com/openstack/nova/blob/f902e0d/nova/context.py#L464

.. _POC for unavailable_servers: https://review.openstack.org/#/c/575996/

.. _listing instances using Searchlight: https://specs.openstack.org/openstack/nova-specs/specs/pike/approved/list-instances-using-searchlight.html

.. _here: https://github.com/openstack/nova/blob/f902e0d/nova/compute/multi_cell_list.py#L246

.. _quota calculation code: https://github.com/openstack/nova/blob/f902e0d/nova/quota.py#L1317

History
=======

.. list-table:: Revisions
   :header-rows: 1

   * - Release Name
     - Description
   * - Rocky
     - Introduced
   * - Stein
     - Reproposed
