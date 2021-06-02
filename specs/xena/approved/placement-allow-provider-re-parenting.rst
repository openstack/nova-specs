..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

========================================
Allow provider re-parenting in placement
========================================

.. note::
    This is specification does not target the Nova services it only impacts the
    Placement service.

https://storyboard.openstack.org/#!/story/2008764

This spec proposes to allow re-parenting and un-parenting (or orphaning) RPs
via ``PUT /resource_providers/{uuid}`` API in Placement.

Problem description
===================

Today placement API only allows change the parent of an RP from None to a valid
RP UUID. However there are use case when moving an RP between parents make
sense.

Use Cases
---------

* An existing PGPU RP needs to be moved under the NUMA RP when NUMA is modeled.

* We have a `neutron bug`_ that introduced an unwanted change causing that
  SRIOV PF RPs was created under the root RP instead of under the neutron agent
  RP. We can fix the broken logic in neutron but we cannot fix the already
  wrongly parented RP in the DB via the placement API.

.. _`neutron bug`: https://bugs.launchpad.net/neutron/+bug/1921150

Proposed change
===============

Re-parenting is rejected today and the code has the following `comment`_ :

    TODO(jaypipes): For now, "re-parenting" and "un-parenting" are
    not possible. If the provider already had a parent, we don't
    allow changing that parent due to various issues, including:

     * if the new parent is a descendant of this resource provider, we
       introduce the possibility of a loop in the graph, which would
       be very bad
     * potentially orphaning heretofore-descendants

    So, for now, let's just prevent re-parenting...

.. _`comment`: https://github.com/openstack/placement/blob/6f00ba5f685183539d0ebf62a4741f2f6930e051/placement/objects/resource_provider.py#L777


The first reason is moot as the loop check is already needed and implemented
for the case when the parent is updated from None to an RP.

The second reason does not make sense to me. By moving an RP under another RP
all the descendants should be moved as well. Similarly how the None -> UUID
case works today. So I don't see how can we orphan any RP by re-parenting.

I see the following possible cases of move:

* RP moved upwards, downwards, side-wards in the same RP tree
* RP moved to a different tree
* RP moved to top level, becoming a new root RP

From placement perspective every case results in one or more valid RP trees.

Based on the data model if there was allocations against the moved RP those
allocations will still refer to the RP after the move. This means that if a
consumer has allocation against a single RP tree before the move might have
allocation against multiple trees after the RP move. Such consumer is already
supported today.

An RP move might invalidate the original intention of the consumer. If the
consumer used an allocation candidate query to select and allocate resources
then by such query the consumer defined a set of rules (e.g. in_tree,
same_subtree) the allocation needs to fulfill. The rules might not be valid
after an RP is moved. However placement never promised to keep such invariant
as that would require the storage of the rules and correlating allocation
candidate queries and allocations. Moreover such issue can already
be created with the POST /reshape API as well. Therefore keeping any such
invariant is the responsibility of the client. So I propose to start supporting
all form of RP re-parenting in a new placement API microversion.

Alternatives
------------
See the API alternatives below.

Data model impact
-----------------

None

REST API impact
---------------

In a new microversion allow changing the parent_uuid of a resource provider to
None or to any valid RP uuid that does not cause a loop in any of the trees via
the ``PUT /resource_providers/{uuid}`` API.

Protecting against unwanted changes
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

As noted above re-parenting can significantly change the RP model in the
Placement database. So such action needs to be done carefully. While the
Placement API is already admin only by default, the request is raised on the
Xena PTG for extra safety measures against unintentional parent changes.
During the spec discussion every the reviewer expressed the view that such
safety measure is not really needed. So this spec only propose to use the new
microversion and extensive documentation to signal the new behavior.

Still there is the list of alternatives discussed during the review:

* `Do nothing`: While it is considered not safe enough during the PTG, during
  the spec review we ended up choosing this as the main solution.
* `A new query parameter`: A new query parameter is proposed for the
  ``PUT /resource_providers/{uuid}`` API called ``allow_reparenting`` the
  default value of the query parameter is ``False`` and the re-parenting cases
  defined in this spec is only accepted by Placement if the request contains
  the new query parameter with the ``True``. It is considered hacky to add a
  query parameter for a PUT request.
* `A new field in the request body`: This new field would have the same meaning
  as the proposed query parameter but it would be put into the request body. It
  is considered non-RESTful as such field is not persisted or returned as the
  result of the PUT request as it does not belong to the representation of the
  ResourceProvider entity the PUT request updates.
* `A new Header`: Instead of a new query paramtere use a new HTTP header
  ``x-openstack-placement-allow-provider-reparenting:True``. As the name shows
  this needs a lot more context encoded in it to be specific for the API it
  modifies while the query parameter already totally API specific.
* `Use a PATCH request for updating the parent`: While this would make the
  parent change more explicit it would also cause great confusion for the
  client for multiple reasons:

  1) Other fields of the same resource provider entity can be updated via the
     PUT request, but not the ``parent_uuid`` field.
  2) Changing the ``parent_uuid`` field from None to a valid RP uuid is
     supported by the PUT request but to change it from one RP uuid to another
     would require a totally different ``PATCH`` request.
* `Use a sub resource`: Signal the explicit re-parenting either in a form of
  ``PUT /resource-providers/{uuid}/force`` or
  ``PUT /resource-providers/{uuid}/parent_uuid/{parent}``. While the second
  option seems to be acceptable to multiple reviewers, I think it will be
  confusing similarly to ``PATCH``. It would create another way to update a
  field of an entity while other fields still updated directly on the parent
  resource.


Security impact
---------------

None

Notifications impact
--------------------

N/A

Other end user impact
---------------------

None

Performance Impact
------------------

The loop detection and the possible update of all the RPs in the changed
subtree with a new ``root_provider_id`` needs extra processing. However the
re-parenting operation is considered very infrequent. So the overall Placement
performance is not affected.

Other deployer impact
---------------------

None

Developer impact
----------------

None

Upgrade impact
--------------

None

Implementation
==============

Assignee(s)
-----------


Primary assignee:
    balazs-gibizer

Feature Liaison
---------------

Feature liaison:
  None

Work Items
----------

* Add a new microversion to the Placement API. Implement an extended loop
  detection and update ``root_provider_id`` of the subtree if needed.
* Mark the new microversion osc-placement as supported.

Dependencies
============

None

Testing
=======

* Unit testing
* Gabbit API testing

Documentation Impact
====================

* API doc needs to be updated. Warn the user that this is a potentially
  dangerous operation.

References
==========

None

History
=======

.. list-table:: Revisions
   :header-rows: 1

   * - Release Name
     - Description
   * - Xena
     - Introduced
