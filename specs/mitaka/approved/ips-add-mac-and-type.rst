..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

=================================
Add mac and type into API for ips
=================================


https://blueprints.launchpad.net/nova/+spec/ips-add-mac-and-type


Problem description
===================

When doing v2.1 API enablement [1], in order to backward compatiblility,
nova removed output OS-EXT-IPS-MAC:mac_addr and OS-EXT-IPS:type by using
old viewbuilder.

Use Cases
---------

As an user, I want to know network info besides existing name and ip
range, I want to know mac addr and type.

Proposed change
===============

Use microversion to add those info into the output.

Alternatives
------------

None

Data model impact
-----------------

None

REST API impact
---------------

::

  GET /v2.1/{project_id}/servers/{server_id}/ips returns following now

  {
    "addresses": {
      "private": [
        {
          "version": 4,
          "addr": "10.0.0.2"
        }
      ]
    }
  }

  if will be changed to return
  {
    "addresses": {
      "private": [
        {
          "version": 4,
          "addr": "10.0.0.2",
          "type": "fixed",
          "mac_addr": "00:00:00:00:00:00"
        }
      ]
    }
  }

  this is also applied to
  /v2.1/{tenant_id}/servers/{server_id}/ips/{network_label}

Security impact
---------------

None

Notifications impact
--------------------

None

Other end user impact
---------------------

python-novaclient need change to show the new data if microversion higher
then the version introduce the feature.

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
  jichenjc

Work Items
----------

one microversion to include the output


Dependencies
============

None

Testing
=======

unit test and functional test.

Documentation Impact
====================

Microversion document will be updated to include this.

References
==========

* https://github.com/openstack/nova/blob/master/nova/api/openstack/compute/ips.py#L31

History
=======

.. list-table:: Revisions
   :header-rows: 1

   * - Release Name
     - Description
   * - Mitaka
     - Introduced
