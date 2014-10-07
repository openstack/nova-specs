..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

======================================
Storage Policy Based Management (SPBM)
======================================

https://blueprints.launchpad.net/nova/+spec/vmware-spbm-support

The feature will enable an OpenStack environment to take advantage of
backend storage policies to provide differential services to tenants.

Problem description
===================

Enable administrators and tenants to take advantage of backend storage
policies. The storage admin first creates storage profiles in VC based
on the storage vendor provided capabilities and/or tag based capabilities
of the underlying storage infrastructure. Refer to
http://pubs.vmware.com/vsphere-55/topic/com.vmware.vsphere.storage.doc/GUID-A8BA9141-31F1-4555-A554-4B5B04D75E54.html
to learn more about storage profiles on VC.

The disk(s) of the virtual machine will be placed on the storage that
matches the storage policy. This can for example provide preferential
services to the user. For example the user will have an option of
selecting 'gold', 'silver' or 'bronze' storage. 'gold' can be for
applications that require fast and reliable results. 'bronze' can be
for a background VM running in the evening doing maintenance.

The spawn method currently selects the ‘best’ datastore to use. The
administrator is able to select one or more datastores for selection
by configuring a datastore regular expression. This logic will not
be required if the instance flavor contain extra spec information
that is relevant to the SPBM. That is, the SPBM information will be
used for the datastore selection.

Use Cases
---------

Enable cloud admin to provide differential services for instance images.

Project Priority
----------------

None

Proposed change
===============

In order for Nova to provide SPBM we will need to address the following:

* Enabling the tenant to make use of storage policies. The goal here
  will be to provide the administrator with the necessary tools to
  provide differential storage services to the tenant. More specifically
  the administrator will be able to leverage capabilities provided by the
  storage infrastructure. There are two parts:

  * Configuration. The admin will need to do the following:

    * Configure a default SPBM policy

    * Create a flavor(s) for the tenants that will enable them to make use
      of the various storage policies.

  * Tenant usage. The tenant will be able to select a flavor that has
    a storage policy.

* Driver support for the storage policies.

  * This entails using the information passed by the tenant to the driver.
    More specifically the storage policy will be passed as flavor metadata.

The driver will need to make use of a different endpoint to access the storage
policies on the VC. This will require a new configuration variable, that is,
the PBM WSDL location will need to be defined.

NOTE: all of the nodes will share the same storage so there will not be any
issues regarding rescheduling.

The change will not affect the cached images. This is only where the disk
for the VM will be placed.

The flavor extra spec ‘image:storage_policy’ will drive the datastore
selection. In the event that this flag is not present and the pbm_enabled
is set in the configuration file then we will make use of a configured default
policy. That is, if this is present then it will be used to get the list of
datastores that can be used for selection. If not then we will use the list of
datastores that can be accessed by the cluster.

If this exists then we will validate that the policy exists.
If not then an exception will be thrown. We will then proceed to get the moref
and datastore of the datastore that is relevant to this policy

pseudo code::
        profile_ids = pbmServiceContent.profileManager.pbmQueryProfile()
        profiles = pbmRetrieveContent(profile_ids)
        profiles.find(name=profile_name)

Query Matching ‘datastore’ entities for the profile. API :-
pbmQueryMatchingHub

If this does not exist then we will proceed to the select the datastore as
before.

The list of datastores will be processed by the existing code to select the
best fit.

Alternatives
------------

At the moment there is no way that a administrator can provide differential
storage services to a tenant.

Data model impact
-----------------

There are no data model changes. The information is passed from the tenant to
the driver via flavor metadata (extraspecs). The driver in turn will use this
information to assign the correct storage.

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

The cloud provider will provide a flavor to the tenant that will enable them
to have preferential storage capabilities.

Performance Impact
------------------

None

Other deployer impact
---------------------

There are 3 new configuration variables (both in the vmware section):
* pbm_wsdl_location - PBM service WSDL file location URL. e.g.
file:///opt/SDK/spbm/wsdl/pbmService.wsdl. This will be optional. This
value is a string. The default is None (not set).
* pbm_enabled - status of storage policy based placement of instances.
This value is a boolean. Default is False.
* pbm_default_policy - The PBM default policy. If pbm_enabled
is set and there is no defined storage policy for the specific request
then this policy will be used. This value is a string. The default policy
is defined out of band by the administrator on the Virtual Center. The
default is None (not set).

An admin user will create a new flavor either via the dashboard or the CLI.
The flavor extra spec will have a key ‘image:storage_policy’. The admin
will associate this this a predfined storage policy on the VC.

Developer impact
----------------

None

Implementation
==============

None

Assignee(s)
-----------

Primary assignee:
    garyk
    smurugesan

Other contributors:
    rgerganov

Work Items
----------

Code was posted in the Icehouse cycle:
* SPBM support (part of oslo integration)
* Add support for default pbm policy
* Get storage policy from flavor
* Use storage policy in datastore selection
* Associate instance with storage policy

Dependencies
============

None

Testing
=======

This requires 3rd party testing. It is not possible to be tested by the current
gate.


Documentation Impact
====================

Configuration variables and their usage need to be documented.
Flavor creation and management should be discussed too. That is, the flavor
extra spec will need to contain the policy. The key will be:
'image:storage_policy' and the values can be for example 'gold', 'silver',
etc.

References
==========

https://docs.google.com/document/d/14Fr76WsFxBPfQJHRdy389IxlxZHXq-Kr83PeCXgDP1M/edit
