..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

================================
List instances using Searchlight
================================

`<https://blueprints.launchpad.net/nova/+spec/list-instances-using-searchlight>`_

To support efficiently listing instances across multiple cells Nova plans to
integrate support for using `Searchlight`_. This will be an optional feature
as we prove out the effectiveness of this approach.

.. _Searchlight: https://docs.openstack.org/developer/searchlight/


Problem description
===================

Listing instances across multiple cells will be inefficient in a large
deployment since the compute API will have to query each cell and apply filters
and then merge sort the results in Python. It will be more efficient to use a
single global data store like an ElasticSearch (ES) cluster fronted by
Searchlight.

Use Cases
---------

As a user in an OpenStack multiple cell environment it's important that I can
quickly get a view of all my instances. I want to be able to filter and sort
them on the server, and have a predictable sort order when new instances are
created in multiple cells.


Proposed change
===============

Add a configuration option to Nova which will toggle whether or not the compute
API will iterate the cells to list instances and then merge sort the results,
or query Searchlight and translate those results for a proper compute API
response.

This will be configurable and disabled by default because an existing
deployment may not be setup to emit versioned notifications or using
Searchlight, so initially there would be no data to give back in the response.

.. note:: When using Searchlight to service a ``GET /servers`` or
   ``GET /servers/detail`` request we will get all of the necessary information
   from Searchlight. There will not be any additional calls to the nova
   database, otherwise that would defeat the purpose of this change. We will
   not use Searchlight for ``GET /servers/{server_id}`` because when we have a
   specific server ID we can look up which cell it's in using the
   InstanceMapping record in the Nova API database.

Error conditions
----------------

* If configured to use Searchlight but it is not available in the service
  catalog or Nova does not have access to it, we will fallback to the default
  path which means iterating the cells to list instances and merge sort the
  results. A warning would be logged in this case but the API request should
  not fail with a 500. We will also set a flag so that we do not
  continue to check until the service is restarted, similar to how we handled
  the placement API in ``nova.scheduler.client.report.SchedulerReportClient``
  with the ``@safe_connect`` decorator in Newton.

Known issues
------------

* It is currently possible for an administrator to list deleted instances in
  the compute REST API. This is due to the fact that when an instance is
  "deleted" in Nova, it is not actually deleted from the database. It is
  considered "soft deleted", meaning ``instances.deleted != 0`` in the
  database. That is not to be confused with the ``SOFT_DELETED`` status in the
  REST API which is based on the ``reclaim_instance_interval`` configuration
  option. There are two ways to remove a (soft) deleted instance from the REST
  API:

  1. Run the ``nova-manage db archive_deleted_rows`` command which will move
     the (soft) deleted instances to the ``shadow_instances`` table.
  2. Purge the deleted instances from the database directly. While not a
     supported operation in Nova directly, there are publicly available
     scripts for operators to use for purging the database.

  The issue this presents with using Searchlight is that currently Searchlight
  will delete an index entry for the instance once it processes the
  ``compute.instance.delete.end`` notification. This effectively means that
  with the existing behavior, if using Searchlight you will not be able to list
  deleted instances since they will not be stored in Searchlight. This includes
  the `changes-since` query parameter no longer returning deleted instances,
  which it does today.

  Having noted this, we should mention that there is no guarantee today that
  you can list deleted instances from the compute REST API based on the
  data retention/archive/purge policy in the given cloud provider. For example,
  if the cloud provider has a policy to archive or purge all deleted instances
  after 30 days, then they already cannot list instances that were deleted more
  than 30 days ago.

  We will have to sort this limitation out with the Searchlight team. It might
  be possible, for example, to add a configuration option to Searchlight to
  control how long an index can be stored for a deleted instance before it is
  finally removed. It is worth noting that ElasticSearch used to have a concept
  of a ``_ttl`` field but that was `removed in 5.0`_.

  Another alternative is that if `deleted` or `changes-since` query parameters
  are specified, we do not use Searchlight and instead iterate across cells.
  This would not be ideal as it would mean we still have to maintain two code
  paths for listing instances, but we will probably have to do that for a
  couple of releases anyway until we can make Searchlight required, which gives
  us some time to find better solutions with Searchlight.

* When making changes to the compute REST API server response, developers will
  have to also mirror those changes in the versioned notification
  `InstancePayload`_. This also poses an issue between microversions in the
  REST API and the versions on the InstancePayload object. Microversions in the
  REST API are opt-in by the client and Nova will continue to honor older
  microversions. However, the versioned notifications are pushed out at the
  latest available version.

  As an example, say we remove a field 'foo' from the server response in
  microversion 2.53. The compute API will still return the 'foo' field in
  requests with microversion before 2.53. The InstancePayload object cannot
  remove the 'foo' field without a major version bump, and even then it would
  indirectly break the compute API contract if we were using Searchlight since
  Searchlight would not give back a server response with the 'foo' field if it
  were removed from the InstancePayload object. This essentially means we
  cannot drop fields from the InstancePayload for versioned notifications
  unless we have also raised the minimum required microversion in the compute
  REST API to the point that we are also dropping fields from the server
  response.

.. _removed in 5.0: https://www.elastic.co/guide/en/elasticsearch/reference/5.0/breaking_50_mapping_changes.html#_literal__timestamp_literal_and_literal__ttl_literal
.. _InstancePayload: https://github.com/openstack/nova/blob/15.0.0/nova/notifications/objects/instance.py#L19

Data migrations
---------------

A deployment that is not using Searchlight will have none of the necessary
information at first to start using this change for serving compute REST API
requests.

Once Searchlight is deployed and consuming versioned notifications from Nova,
new instance operations will be indexed. However, any existing instance data
will need to be transferred to Searchlight.

Therefore before configuring nova-api to use Searchlight, the deployer must
perform a bulk index of the existing instances from Nova into Searchlight. This
can be performed by issuing::

   searchlight-manage index sync --type OS::Nova::Server

That will tell Searchlight to call the compute REST API to list existing
instances and populate the server indexes using the results. See the
Searchlight documentation for more details on `bulk indexing`_.

.. _bulk indexing: https://docs.openstack.org/developer/searchlight/indexingservice.html#bulk-indexing

Alternatives
------------

None.

Data model impact
-----------------

None.

REST API impact
---------------

While this will change how ``GET /servers`` and ``GET /servers/detail``
responses are generated on the backend, there should be no user-visible changes
to the contract on those APIs. This will be enforced via Tempest testing.

It should also be noted that ElasticSearch supports `pagination`_ and
Searchlight is largely compatible with ElasticSearch, so it supports paging by
page/size. You could also do it with the OpenStack 'marker' method by ordering
on id.

.. _pagination: https://www.elastic.co/guide/en/elasticsearch/guide/current/pagination.html

Security impact
---------------

This would require deploying an ElasticSearch cluster and front that with
project Searchlight, which means another endpoint in the service catalog and
potentially service user. The ES cluster will need to have proper access
controls in place. This also means enabling notifications in the deployment
such that Nova versioned notifications can be fed into the Searchlight ES
cluster.

Notifications impact
--------------------

None. While this solution depends on using versioned notifications in Nova,
there are no changes proposed for notifications themselves.

Other end user impact
---------------------

None. This change should be transparent to the end user.

Performance Impact
------------------

The intent of this change is to improve performance when listing instances
across a multi-cell deployment. However, the actual performance will depend on
how well the ElasticSearch cluster performs.

Other deployer impact
---------------------

* Configure Nova to emit versioned notifications.
* Setup Searchlight including any service user and endpoint required for the
  service catalog along with the backing data store, e.g. ElasticSearch.
* Existing deployments would need a certain amount of time to feed existing
  instance data into Searchlight before switching the compute API over to using
  it. See the `Data migrations`_ section above for more details.

Developer impact
----------------

Developers will have to ensure that any changes to the compute REST API which
require returning new fields in a response will have those new fields also in
versioned notifications sent to Searchlight.

Depending on how Searchlight implements support for versioned notifications,
developers may also need to update index mappings to expose the new fields. We
might be able to automate that in Searchlight, however, using the work done in
the `json-schema-for-versioned-notifications blueprint`_. If we can not or do
not end up using versioned notification schema in Searchlight then that would
create an install/upgrade order dependency such that Searchlight must be
installed/upgraded before nova-api.

Let's run through a scenario of what this might entail when one is adding a new
field in the compute REST API response. We also need to put that in the
versioned notification payload so Searchlight gets it. The point about the
schema is if the notification also sends the schema, then Searchlight can use
that schema dynamically, otherwise you have to update Searchlight statically to
know about the new field.

Taking the static case, if one is adding a new field to the server
response in the compute API, and let's assume it's not in the instances table
(it's a new column in the DB), then the steps are:

1. Add column to instances table in nova DB.
2. Add field to Instance object.
3. Add field to InstancePayload object.
4. Add schema change to Searchlight for the new field.
5. Add the new field to the compute REST API response via microversion.

This of course means that you have to upgrade Searchlight before you upgrade
nova-api to get the new field out of the REST API.

.. _json-schema-for-versioned-notifications blueprint: https://blueprints.launchpad.net/nova/+spec/json-schema-for-versioned-notifications


Implementation
==============

Assignee(s)
-----------

Primary assignee:
  Zhenyu (Kevin) Zheng (Kevin_Zheng)

Other contributors:
  Matt Riedemann (mriedem)

Work Items
----------

* Get a working development environment where Searchlight is regularly running
  with Nova and consuming notifications.
* Add the conditional path to the compute API ``get_all`` flow where we query
  Searchlight for data if Nova is configured to do so.
* There will likely need to be some kind of translation utility code in place
  to convert the Searchlight response to an ``nova.objects.InstanceList``
  object which will be returned to the REST API handler.
* Integrate Searchlight and configure Nova to emit versioned notifications in
  the ``gate-tempest-dsvm-neutron-nova-next-full-ubuntu-xenial-nv`` job for
  testing.
* Install guide changes to explain the setup of Searchlight with Nova.


Dependencies
============

* For parity with the existing compute REST API, this change depends on
  blueprint `additional-notification-fields-for-searchlight`_ for getting the
  needed information into Searchlight.
* This change also depends on Searchlight adding support for nova versioned
  notifications which is tracked in `blueprint nova-versioned-notifications`_.

.. _additional-notification-fields-for-searchlight: https://blueprints.launchpad.net/nova/+spec/additional-notification-fields-for-searchlight
.. _blueprint nova-versioned-notifications: https://blueprints.launchpad.net/searchlight/+spec/nova-versioned-notifications


Testing
=======

* Unit tests for the changes in the compute API.

* The majority of the test effort for this change will be integrating
  Searchlight into the
  ``gate-tempest-dsvm-neutron-nova-next-full-ubuntu-xenial-nv`` job, enabling
  versioned notifications and then using Searchlight as described in this spec
  for listing instances. A full Tempest run on that job will show if we have
  parity with the API responses.

* When we have a multi-cell CI job setup then we will probably also make the
  same changes to that job for efficient instance listing operations.


Documentation Impact
====================

The `compute admin guide`_ will need to be updated to discuss how to enable
this feature. It is also possible that the install, operations and architecture
guides may also need to be updated.

.. _compute admin guide: https://docs.openstack.org/admin-guide/compute.html


References
==========

None.


History
=======

.. list-table:: Revisions
   :header-rows: 1

   * - Release Name
     - Description
   * - Pike
     - Introduced
