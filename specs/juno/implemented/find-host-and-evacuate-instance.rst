
..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

===========================================
API: Evacuate instance to a scheduled host
===========================================

https://blueprints.launchpad.net/nova/+spec/find-host-and-evacuate-instance

The aim of this feature is to let operators evacuate instances without
selecting a target host manually. The scheduler will select the best
target instead.


Problem description
===================

In the event of a unrecoverable hardware failure (compute-node down),
Operators need to evacuate the instances by selecting a target
compute host.

This may work for temporary pre-selected failover-hosts, but if they
just want to evacuate/rebuild the instance without taking further
action, Operators must check each instance/flavor metadata and select
target hosts that match the specs individually for each evacuation.

In case of using external tools to trigger the evacuation, logic about
the compute-hosts has to be there to appropriately call the API.

It also make it consistent with migrate and live-migrate operations.


Proposed change
===============

Modify the current rebuild_instance flow to let the scheduler pick up the best
target host for the instance being evacuate.


Alternatives
------------

Something external to pick up the proper host when
nova can already do it.

Data model impact
-----------------
None

REST API impact
---------------

The current evacuate API v2/v3 will be modified to accept body data without
target host field and this change will be advertised through a new
extension ExtendedEvacuateFindHost in case of v2.
If the field is present but empty old behavior will be applied to be
able to determine if it's an missing due to input error or not.

* Evacuate an instance to another compute-host.
     * POST
     * Normal Response Code: 200
     * Expected error http response code(s)
           - 404: Compute host (if provided)/instance not found
           - 400: Compute service in use
           - 409: Invalid instance state
     * v2|v3/servers/id/action
     * Schema definition for V3::

        evacuate = {
        'type': 'object',
        'properties': {
            'evacuate': {
                'type': 'object',
                'properties': {
                    'on_shared_storage': parameter_types.boolean,
                    'admin_password': parameter_types.admin_password,
                },
                'required': ['on_shared_storage']
                'additionalProperties': False,
            },
        },
        'required': ['evacuate'],
        'additionalProperties': False,
        }

     * Sample request::

        { "evacuate": { "adminPass": "%(adminPass)s",
                        "onSharedStorage": "%(onSharedStorage)s" }}

     * Sample Response::

        {  "adminPass": "%(password)s" }}



Security impact
---------------
None

Notifications impact
--------------------
None

Other end user impact
---------------------

python-novaclient will be modified to have target_host argument as
optional.

The user can trigger this feature by:
nova evacuate my_server


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
  leandro-i-constantino

Other contributors:
  juan-m-olle


Work Items
----------

* Move rebuild instance to conductor task to unify rebuild/evacuate logic
* Add logic to select target host
* Add APIv2/v3
* Set target-host optional on nova-client
* Allow evacuating instances in an 'affinity' group, allowing the scheduler to
  pick the destination

Dependencies
============

For a complete use-case the following bp will be required
https://blueprints.launchpad.net/nova/+spec/validate-targethost-live-migration,
since we can retrieve the original scheduler hints from that a particular
instance and let the  scheduler select the best host based on that.
Until then, instances launched without any scheduler hint could still be
selected by the scheduler by using flavor specs.


Testing
=======

Tempest do not currently support multi-node tests, so it will be added
after CI can run those kind of tests.

Documentation Impact
====================

* Api Docs to reflect that host field is now optional. If not present
  in the body the new feature will be triggered.
* Client docs ( due to optional arg)
* Admin User Guide on evacuation topic.


References
==========
None
