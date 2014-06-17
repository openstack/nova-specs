..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

==================================
CreateVM supports subnet specified
==================================

https://blueprints.launchpad.net/nova/+spec/selecting-subnet-when-creating-vm

Currently the network info specified as part of server creation is limited to
network-id, port-id, and ip address. When a network has multiple subnets
then we need to also be able to specify a subnet-id.


Problem description
===================

Currently the network info specified as part of server creation is limited to
network-id, port-id, and ip address.

So if an network has multiple subnets in it, it's impossible to select
which of the possible subnets a VM should be created in.
You only could choose an ip address in one subnet and then create an instance.
But this is not a convenient way. Moreover, this method is also not available
for bulk instances creation.


Proposed change
===============

1. Add one optional param 'subnet-id' in networking structure of 'spawn'.

2. This parameter will affect in 'allocate_for_instance()'
   in nova/network/neutronv2/api.py.

3. Bulk instances creation with 'subnet-id' will be supported,
   as the 'net-uuid' is specified.

Alternatives
------------

None

Data model impact
-----------------

None

REST API impact
---------------

The new 'spawn' rest API in v2::
 /v2/{project_id}/servers

    {
        'server':{
        ...
        'networks': [
        {
        'subnet-id': '892b9731-044a-4c87-b003-1e75869028c0'
        }
        ...
        ]
        ...
        }

    }

and in v3 it is like::
 /v3/servers

{
    'server':{
    ...
    'networks': [
    {
    'subnet-id': '892b9731-044a-4c87-b003-1e75869028c0'
    }
    ...
    ]
    ...
    }

}

* Here, the <string> 'subnet-id' means the subnet your instances
  want to be created in. No default value.

* If 'subnet-id' is not a string or uuid-like, a BadRequest exception
  will be raised.(HTTP 400)

* The status code will be HTTP 202 when the request succeeded as usual,
  and the response body won't be changed.

In the current implement in Nova, the network info specified is limited to
network-id, port-id, and ip address, and port-id has the highest priority.
So, we also need to point the priority during server creation.

* The 'port' parameter still has the highest priority here.

  That means, if both 'port' & 'subnet-id' are specified, 'port' will be used
  and the 'subnet-id' won't effect here.

* The 'subnet-id' has the same priority with 'v4-fixed-ip'/'v6-fixed-ip'.

  That means, if both 'subnet-id' & 'v4-fixed-ip'/'v6-fixed-ip' are specified,
  compatibility validation of these two arguments will be executed.
  * If it passed, the ip address you assigned will be used as usual.
  * If not, a BadRequest exception will be raised.(HTTP 400)

* The 'net-uuid' parameter still has the lowest priority like before.

  That means, if both 'subnet-id' & 'net-id' are specified, 'subnet-id'
  will effect here and 'net-uuid' will be ignored like port specified.


Security impact
---------------

None

Notifications impact
--------------------

None

Other end user impact
---------------------

The related works in python-novaclient will also be added.
After this modification, user could create instances with 'subnet-id' specified
like 'net-uuid' does via CLI.

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

Assignee: wingwj <wingwj@gmail.com>

Work Items
----------

In nova:

  * Add 'subnet-id' to 'create' in API layer

  * Use 'subnet-id' for 'allocate_for_instance()'
    in nova/network/neutronv2/api.py

  * Add related tests both API & nova-compute

In python-novaclient:

  * Add 'subnet-id' support in python-novaclient

  * Add related tests in python-novaclient

In tempest:

  * Related test-cases will definitely be added here

In doc:

  * The API modification will also be registered in openstack-doc


Dependencies
============

None


Testing
=======

The unit tests need to be added in each related projects like I described
in <Work Items> part. After the modifications, all changed methods above
will be verified together.


Documentation Impact
====================

The 'server creation' in API & CLI documentations will need to be updated to:

* Reflect the new 'subnet-id' parameter and explain its usage
* Explain the priority of network info during server creation


References
==========

None