..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

===================================
Convert EC2 API to use nova objects
===================================

https://blueprints.launchpad.net/nova/+spec/ec2-api-objects

This blueprint covers updating EC2 API and related functions
to use the Nova object model for all database interaction,
like implementation in compute manager & nova-network now.

Problem description
===================

Currently EC2 API use original raw db APIs to fetch data from the database.

Proposed change
===============

The files need to be modified include:

* nova/api/ec2/cloud.py
* nova/api/ec2/ec2utils.py
* nova/tests/api/ec2/test_cinder_cloud.py
* nova/tests/api/ec2/test_cloud.py
* nova/tests/api/ec2/test_ec2_validate.py


Alternatives
------------

None


Data model impact
-----------------

Four parts are included,
EC2SnapshotIdMapping, EC2VolumeIdMapping, EC2S3Image, EC2InstanceIdMapping.

All of them need to be modified to make use of the object
instead of using the db API directly for managing UUID to EC2 ID.

* Now 'EC2VolumeMapping' & 'EC2InstanceMapping' need to co-ordinate work
  with russellb working on objects.
* 'EC2SnapshotIdMapping' & 'EC2S3Image' object
  need to be added and implemented in nova/objects.ec2.py later.

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

None


Developer impact
----------------

None


Implementation
==============

Assignee(s)
-----------

Primary assignee:
  wingwj

Other contributors:
  russellb

Work Items
----------

* Add 'EC2VolumeMapping' object - (needs to co-ordinate work with russellb)

* Add 'EC2InstanceMapping' object - (needs to co-ordinate work with russellb)

* Add 'EC2SnapshotIdMapping' & 'EC2S3Image' object in /nova/objects/ec2.py

* Use 'EC2VolumeMapping' in EC2 API & related tests

* Use 'EC2InstanceMapping' in EC2 API & related tests

* Use 'EC2SnapshotIdMapping' in EC2 API & related tests

* Use 'EC2S3Image' in EC2 API & related tests


Dependencies
============

None


Testing
=======

The original unit tests also need to rewrite using nova objects.
After the modifications, all changed APIs will be verified together.

Documentation Impact
====================

None


References
==========

None