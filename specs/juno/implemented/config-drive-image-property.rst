..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

==========================================
Config drive based on image property
==========================================

https://blueprints.launchpad.net/nova/+spec/config-drive-image-property

When creating an instance, check the image property to decide if a config
drive should be created.

Problem description
===================

Currently Nova decides if config drive is created for a server
based on:

a) If the user specifies the config-drive option in server create API
   request, or,

b) If the server is scheduled to a compute node with force_config_drive
   option set.

But we need consider the image requirement also. Some images may explicitly
require config drive.

Proposed change
===============

* Add an image property as "img_config_drive", the value of the
  img_config_drive can be:

  * img_config_drive=mandatory|optional

  where these mean:

  * mandatory == instance must always have a config drive

  * optional == instance can use a config drive, but can still work if missing

  Any other value will be treated as error. If no option specified, the default
  value is optional.

  In future, this property may be extended to include more choices like
  'disable' to disable config_drive. A mechanism should be presented at that
  time to make sure the 'disable' option is not treated as error.

* The rule of config drive decision is described as followed table. A config
  drive will be created whenever user specified in API, required in image
  property or compute node configuration option specified it.

    +-----------+------------------------+----------------+-----------+
    |   API     |  Image Property        | Compute Config | Result    |
    +===========+========================+================+===========+
    |    No     |  Mandatory             | Set or Unset   | Yes       |
    +-----------+------------------------+----------------+-----------+
    |    No     |  Optional              | Set            | Yes       |
    +-----------+------------------------+----------------+-----------+
    |    No     |  Optional              | Unset          | No        |
    +-----------+------------------------+----------------+-----------+
    | Specified |  Mandatory or Optional | Set or Unset   | Yes       |
    +-----------+------------------------+----------------+-----------+


Alternatives
------------

Another option is to combine the API option and image property into one
instance property in the API layer, but this is not clean IMHO.

Data model impact
-----------------

No

REST API impact
---------------

No

Security impact
---------------

No

Notifications impact
--------------------

No

Other end user impact
---------------------

This BP will add one more image property, so user should be aware of that.

Performance Impact
------------------

There will be no performance impact.

Other deployer impact
---------------------

It's recommended that deployers update all compute nodes before they add the
config drive property to any images. Otherwise, the image property is not
checked by compute node w/o this features.

Developer impact
----------------

No

Implementation
==============

Assignee(s)
-----------

Primary assignee:
  yunhong-jiang

Work Items
----------

* Change the virt/configdrive.py to check image property also.

Dependencies
============

There are some discussion of the enhancement of image property as in
https://blueprints.launchpad.net/nova/+spec/convert-image-meta-into-nova-object
and the discussion is on-going.

This proposal is not conflict with that proposal, we just need make sure the
new config drive property will be defined in the VirtProperties. It will be a
small effort no matter which proposal lands firstly.

Testing
=======

Tempest tests will be added so that we can make sure the image config drive
property is treated correctly.

Documentation Impact
====================

Document change needed for the new image property.

References
==========
No
