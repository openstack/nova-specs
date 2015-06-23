..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

=====================================
Ironic: Multiple compute host support
=====================================

https://blueprints.launchpad.net/nova/+spec/ironic-multiple-compute-hosts

Today, the Ironic virt driver only supports a single nova-compute service.
This is clearly not viable for an environment of any interesting scale;
there's no HA, everything fails if the compute service goes down. Let's fix
that.


Problem description
===================

Computers are horrible things. They die sometimes. They crash processes at
random. Solar flares can make bad things happen. And so on and so forth.

Running only one instance of nova-compute for an entire Ironic environment
is going to be a bad time. The Ironic virt driver currently assumes that only
one nova-compute process can run at once. It exposes all resources from an
Ironic installation to the resource tracker, without the ability to split
those resources out into many compute services.

Use Cases
----------

This allows operators to avoid having a single nova-compute service for an
Ironic deployment, so that the deployment may continue to function if a
compute service goes down. Note that this assumes a single Ironic cluster
per Nova deployment; this is not unreasonable in most cases, as Ironic should
be able to scale to 10^5 nodes.


Proposed change
===============

In general, a nova-compute running the Ironic virt driver should expose
(total resources)/(number of compute services). This allows for resources to be
sharded across multiple compute services without over-reporting resources.
This compute daemon should only register as a single row in the
compute_nodes table, rather than many rows, accomplishing the goal of the
next paragraph.

Nova's scheduler should schedule only to a nova-compute host; the host will
choose an Ironic node itself, from the nodes that match the request (explained
further below).  Once an instance is placed on a given nova-compute service
host, that host will always manage other requests for that instance (delete,
etc). So the instance count scheduler filter can just be used here to equally
distribute instances between compute hosts. This reduces the failure domain to
failing actions for existing instances on a compute host, if a compute host
happens to fail.

The Ironic virt driver should be modified to call an Ironic endpoint with
the request spec for the instance. This endpoint will reserve a node, and
return that node. The virt driver will then deploy the instance to this node.
When the instance is destroyed, the reservation should also be destroyed.

This endpoint will take parameters related to the request spec, and is being
worked on the Ironic side here.[0] This has not yet been solidified, but it
will have, at a minimum, all fields in the flavor object. This might look
something like::

    {
        "memory_mb": 1024,
        "vcpus": 8,
        "vcpu_weight": null,
        "root_gb": 20,
        "ephemeral_gb": 10,
        "swap": 2,
        "rxtx_factor": 1.0,
        "extra_specs": {
            "capabilities": "supports_uefi,has_gpu",
        },
        "image": {
            "id": "some-uuid",
            "properties": {...},
        },
    }


We will report (total ironic capacity) into the resource tracker for each
compute host. This will end up over-reporting total available capacity to Nova,
however is the least wrong option here. Other (worse) options are:

* Report (total ironic capacity)/(number of compute hosts) from each compute
  host. This is more "right", but has the possibility of a compute host
  reporting (usage) > (max capacity), and therefore becoming unable to perform
  new build actions.

* Report some arbitrary incorrect number for total capacity, and try to make
  the scheduler ignore it. This reports numbers more incorrectly, and also
  takes more code and has more room for error.

Alternatives
------------

Do what we do today, with active/passive failover.

Doing active/passive failover well is not an easy task, and doesn't account for
all possible failures. This also does not follow Nova's prescribed model for
compute failure. Furthermore, the resource tracker initialization is slow
with many Ironic nodes, and so a cold failover could take minutes.

Resource providers[1] may be another viable alternative, but we shouldn't
have a hard dependency on that.

Data model impact
-----------------

None.

REST API impact
---------------

None.

Security impact
---------------

None.

Notifications impact
--------------------

None.

Other end user impact
---------------------

None.

Performance Impact
------------------

This should improve performance a bit. Currently the resource tracker is
responsible for every node in an Ironic deployment. This will make that group
smaller and improve the performance of the resource tracker loop.

Other deployer impact
---------------------

A version of Ironic that supports the reservation endpoint must be deployed
before a version of Nova with this change is deployed. If this is not the
case, the previous behavior should be used. We'll need to properly deprecate
the old behavior behind a config option, as deployers will need to configure
different scheduler filters and host managers than the current recommendation
for this to work correctly. We should investigate if this can be done
gracefully without a new config option, however I'm not sure it's possible.

Developer impact
----------------

None, though Ironic driver developers should be aware of the situation.


Implementation
==============

Assignee(s)
-----------

Primary assignee:
  jim-rollenhagen (jroll)

Other contributors:
  devananda
  jaypipes

Work Items
----------

* Change the Ironic driver to be a 1:1 host:node mapping.

* Change the Ironic driver to get reservations from Ironic.


Dependencies
============

This depends on a new endpoint in Ironic.[0]


Testing
=======

This should be tested by being the default configuration.


Documentation Impact
====================

Deployer documentation will need updates to specify how this works, since it
is different than most drivers.


References
==========

[0] https://review.openstack.org/#/c/204641/

[1] https://review.openstack.org/#/c/225546/


History
=======

None.
