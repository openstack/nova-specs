..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

=========================
Pagination for hypervisor
=========================

https://blueprints.launchpad.net/nova/+spec/pagination-for-hypervisor

This spec is proposed to support pagination for hypervisor.

Problem description
===================

When there are thousands of compute nodes, it would be slow to get the
whole hypervisor list, and it is bad for user experience to display
thousands of items in a table in horizon.

Use Cases
----------

* Get paginated compute nodes list when there are too many items.

Proposed change
===============

Changes are going to be in the following places:

* New DB api `compute_node_get_all_by_filters` will be added with
  params filters, limit and marker, so other filter
  methods(compute_node_search_by_hypervisor, etc) also can be refactored
  to use this new db method.

* New compute node object `get_by_filters` method will be added which calls
  the new db api `compute_node_get_all_by_filters`.

* Compute api `compute_node_get_all` will be refactored.

* REST API microversion will be added for hypervisors list to accept
  pagination request.


Alternatives
------------

None

Data model impact
-----------------

None

REST API impact
---------------

New Hypervisors list API to support pagination:

  request::

      GET /v2.1/{tenant_id}/os-hypervisors?marker=2&limit=1

  reponse::

      {
        "hypervisors": [
          {
            "hypervisor_hostname": "fake-mini",
            "id": 3,
            "state": "up",
            "status": "enabled"
          }
        ]
      }

Security impact
---------------

None.

Notifications impact
--------------------

None

Other end user impact
---------------------

None


Performance Impact
------------------

Reduce load on horizon with help of pagination of retrieving hypervisors from
Nova side.

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
  liyingjun

Work Items
----------

1. Change db api to support pagination params.

2. Add compute node object method and refactor compute api.

3. Add REST API microversion.

Dependencies
============

None


Testing
=======

The changes will be exercised through unit tests.

Documentation Impact
====================

New REST API microversion will be added.

References
==========

None
