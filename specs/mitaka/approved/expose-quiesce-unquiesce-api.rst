..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

=====================================================================
Expose Quiesce Unquiesce API
=====================================================================

https://blueprints.launchpad.net/nova/+spec/expose-quiesce-unquiesce-api

Provide quiesce unquiesce API from Nova, to make consistency snapshot of
an application, which consists of a group of VMs, for disaster recovery
purpose from another site.

Problem description
===================
Currently the Nova provides single VM snapshot API (createImage), which will
take a consistency snapshot of a VM and regarding volumes, and will quiesce
unquiesce VM automatily with guest agent support.This method is good
for single VM consistency snapshot, but no way to make consistency
snapshot for an application which othen consists of multiple VMs.

Use Cases
---------

In NFV scenario, a VNF (telecom application) often consists of a group
of VMs. To make it be able to restore in another site for catastrophic
failures happened, this group of VMs snapshot/backup/restore should be done
in a transaction way to guarantee the application level consistency but not
only on single VM level : for example, quiesce VM1, quiesce VM2, quiesce VM3,
snapshot VM1's volumes, snapshot VM2's volumes, snapshot VM3's volumes,
unquiesce VM3, unquiesce VM2, unquiesce VM1. For some telecom application,
the order is very important for a group of VMs with strong relationship.

Therefore the OPNFV multsite project expects Nova to provide quiesce
unquiesce API, to make consistency snapshot of a group of VMs in a transaction
way is possible (but not only one single VM instead).

The disater recovery process will work like this:

  1).DR(Geo site disaster recovery )software get the volumes for each VM
    in the VNF from Nova

  2).DR software call Nova quiesce API to quarantee quiecing VMs in desired
    order

  3).DR software takes snapshots of these volumes in Cinder (NOTE: Because
    storage often provides fast snapshot, so the duration between quiece and
    unquiece is a short interval)

  4).DR software call Nova unquiece API to unquiece VMs of the VNF in reverse
    order

  5).DR software create volumes from the snapshots just taken in Cinder

  6).DR software create backup (incremental) for these volumes to remote
    backup storage ( swift or ceph, or.. ) in Cinder

  7).if this site failed,

    7.1)DR software restore these backup volumes in remote Cinder in the
        backup site.

    7.2)DR software boot VMs from bootable volumes from the remote Cinder in
        the backup site and attach the regarding data volumes.

Note: It's up to the DR policy and VNF character how to use the API. Some
VNF may allow the standby of the VNF or member of the cluster to do
quiece/unquiece to avoid interfering the service provided by the VNF.
Some other VNF may afford short unavailable for DR purpose.

Not only a VNF (telecom application) can benefit from the API, but also it
should be usable by any other application for consistency snapshot on
application level.


Project Priority
----------------

None

Proposed change
===============

Expose 'quiesce' and 'unquiesce' admin API actions for DR software to make
application level consistency snapshot for application disater recovery
purpose.

'quiesce' and 'unquiesce' has already been implemented in VM createImage,
but no API exposed. It is only applied in single VM snapshot scenario.

The prerequisites of this feature is the hypervisor driver supports this
operation and with guest agent installed and enbaled.

This BP mainly focuses on Nova-API part to expose the API, nova.virt
driver.py has already provided the interface 'quiesce' 'unquiesce',  some
other hypervisor drivers may support this feature now or in the future, it
should be out of the scope of this BP.

The 'quiesce' and 'unquiesce' API should work in asyn. way, that means the
caller of the API should check to see whether the operation finished
successfully. And the DR software to guarantee the API calling order for
multiple VMs' quiescing unquiescing.

One vm_state 'quiesced'  will be added. Two task_state 'quiescing',
'unquiescing' will be added too.

Requirements for commands:
Command        Req.d VM States     Req.d Task States      Target State
quiesce        active              None                   quiesced
unquiesce      quiesced            None                   active

VM states and possible commands
VM State           Commands
quiesced           unquiesce

If the hypervisor does not support quiesce,unquiesce, the VM state should
be kept as active, and the task_state will be set to None, and use instance
action to tell user what happened.

If there is expecetion captured during the quiesce, unquiesce action, the
VM state will be set to error, and the exception will be saved to the DB
as other operation.

No matter in quiesced or ERROR state, the admin reset VM state action will
take the VM to desired state.

Alternatives
------------
1. Usually Nova API will manipulate one VM per action. One proposal is
   to expose quiesce, unquiesce single API action on multiple VMs in order,
   this will break Nova API fasion and leads to implementation complexity,
   especially under cells deployment.
2. Another proposal is to make quiesce, unquiesce API work in "sync." way
   due to the short execution time of the quiesce,unquiesce. "sync"
   implementation is not the fasion in web service and Nova API.

Data model impact
-----------------

None

REST API impact
---------------

* URL:
    * /v2/{tenant_id}/servers/{server_id}/action:
    * /v2.1/servers/{server_id}/action/{server_id}/action:

* Request method:
    * POST

* JSON request body for 'quiesce'::

        {
            "quiesce": null
        }

* JSON request body for 'unquiesce'::

        {
            "unquiesce": null
        }

* This operation does not return a response body

* Normal response code:
    * 202: Accepted

* Error response codes:
    * 409: Invalid instance state. Quiece expects the VM is in active state
      before the command to be executed, for unquiece, quiesced state is
      expected. The VM state other than the state mentioned above will lead
      to the 409 response.

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
While taking quiece, disk writes from the instance are blocked.

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
  joehuang

Work Items
----------

1. Add 'quiesce' and 'unquiesce' server admin actions APIs for Nova

Dependencies
============

None

Testing
=======

1. Live quiece/unquice of VMs with a guest booted with qemu-guest-agent should
   be added to scenario tests.
2. A tempest test should also be added for this.
3. Note that it requires environment with hypervisor supports the action.

Documentation Impact
====================

New REST APIs (server admin actions) should be added to the API documentation.
Also, need to document how to use this feature in the operation guide (which
currently recommends you use the fsfreeze tool manually, or invisible in VM
createImage action).

References
==========

nova-specs: 'Quiesce filesystems with QEMU guest agent during image snapshot':
`<https://review.openstack.org/#/c/126966/>`_

'quiesce' and 'unquiesce' methods for libvirt driver:
`<https://blueprints.launchpad.net/nova/+spec/quiesced-image-snapshots-with-qemu-guest-agen/atomic/async>`_

a VNF (telecom application) should, be able to restore in another site
for catastrophic failures happened
`<https://git.opnfv.org/cgit/multisite/tree/multisite-vnf-gr-requirement.rst>`_
