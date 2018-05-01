..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

===========================
Add Generation to Consumers
===========================

https://blueprints.launchpad.net/nova/+spec/add-consumer-generation

Potential conflicts have been identified when more than one process attempts to
allocate resources for a given consumer, and there is currently no way to
detect these conflicts. We propose to add a generation field to the consumers
table in Placement, and implement the same mechanism for tracking updates to
consumers as is implemented for ResourceProviders.


Problem description
===================

When resources are consumed by a consumer, the allocations posted are the full
set of allocations for that consumer, and will overwrite any existing
allocations for that consumer. There is a potential race condition when more
than one process is making allocations for a consumer. For example, Nova is
creating an instance, and asking Neutron to create the required network
resources. Neutron does so, and creates the allocations. Nova then claims the
resources it's providing for the instance, and writes its understanding of the
current allocations to Placement, overwriting Neutron's allocations.

Use Cases
---------

As a service using Placement, I want to know that the allocations I am creating
are accurate, and that other services do not accidentally overwrite the
allocations I create.

Proposed change
===============

A ``generation`` column will be added to the ``consumers`` table. This will be
an auto-incrementing integer, just like the generation column in the
resource_providers table. And like the resource_providers generation, it is
intended to be opaque to the users of the API. This value will be included in
all Placement responses that provide data for a consumer, and must be included
in any request to placement that changes allocations for that consumer. As is
the case for updates to ResourceProviders, if the supplied consumer generation
doesn't match the the current value, Placement will reject the request and
return a 409 Conflict response. Since in many cases there will not be an
existing consumer record, the request would supply ``None`` as the consumer
generation.

As this is an API change, a new microversion will be created. Any older service
that does not support this new microversion will continue to work, but will be
susceptible to the race condition described above.

.. note::

    The term "Microversion 1.X" is used here to indicate the microversion that
    will be added for this new functionality. "Microversion 1.X-1" is used to
    refer to the microversion directly preceding the one added for this new
    functionality.

.. warning::

    Two clients operating on the *same* allocation, one of which using a
    pre-generation microversion is an unsafe operation.

In order to ensure that a consumer record exists for all allocation records, we
will add an online data migration that will find any consumer UUIDs in the
allocations table that have no corresponding record in the consumers table and
populate a record in the consumers table with that UUID. Because we do not want
the consumers.project_id and consumers.user_id columns to be NULLable, we will
add two CONF options for indicating the project and user external identifier to
use for missing consumer records.

``PUT /allocations/{consumer_uuid}``
------------------------------------

The below sections detail the behavior expected from the ``PUT
/allocations/{consumer_uuid}`` call.

No existing allocation records for the consumer
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

When there **ARE NO** existing allocation records that referenced this
consumer UUID, the call will exhibit the following behavior:

* Microversion <1.8: always succeeds. A consumer record is always created, and
  the value of ``CONF.placement.incomplete_consumer_{project|user}_id`` will be
  used for the missing project and user identifiers. A generation will be
  created for this new consumer record.

* Microversion 1.8 - 1.X-1: always succeeds, and consumer record is always
  created with the ``project_id`` and ``user_id`` present in the request
  payload. A generation will be created for this new consumer record

* Microversion 1.X: A new ``consumer_generation`` field will be required in the
  request payload. It will be required to be ``None`` in order to indicate the
  caller expects that this is a new consumer. A new consumer record will be
  created with a generation.

Existing allocation records, but no consumer record for the consumer
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

In this situation, there **ARE** existing allocation records that referenced
this consumer UUID, however there **ARE NO** consumer records that reference
the consumer UUID. This means the allocation records were created prior to
microversion 1.8 *and* the online data migration that creates incomplete
consumer records has *not yet run*.

In this case, the call will exhibit the following behavior:

* Microversion <1.8: always succeeds. A consumer record is always created, and
  the value of ``CONF.placement.incomplete_consumer_{project|user}_id`` will be
  used for the missing project and user identifiers. A generation will be
  created for this new consumer record.

* Microversion 1.8 - 1.X-1: always succeeds, and consumer record is always
  created with the ``project_id`` and ``user_id`` present in the request
  payload. A generation will be created for this new consumer record

* Microversion 1.X: A new ``consumer_generation`` field will be required in the
  request payload. It will be required to be ``None`` in order to indicate the
  caller understands the allocation was created with an older microversion.

Existing allocation records, existing consumer record for the consumer
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

In this final situation, there **IS** an existing consumer record as well as
allocation records that reference the consumer. The allocations must have been
created at or after microversion 1.8 *or* the online data migration that
creates incomplete consumer records has *already run*.

In this case, the call will exhibit the following behavior:

* Microversion <1.X: always succeeds and always overwrites the consumer's
  allocations entirely. The placement service will read the consumer's current
  generation before attempting to replace the allocations, and increment that
  generation at the end of the allocation replacement transaction.

* Microversion 1.X: A new ``consumer_generation`` field will be required in the
  request payload. It will be required to be match the value of the consumer's
  known generation. Placement will check that its known generation matches the
  given generation and return a ``409 Conflict`` if there is a mismatch.
  Furthermore, if another process modifies the same consumer's allocations
  concurrently to the request, the generation increment will fail for the
  consumer and a ``409 Conflict`` will be returned indicating a concurrent
  write occurred. The caller should then re-read the consumer's generation,
  evaluate if the original allocation request is still valid, and if so,
  re-issue the allocation request.

``POST /allocations``
---------------------

This variant of creating allocations was introduced in microversion 1.13 and
required a project and user to be specified for one or more consumers involved
in the allocation.

No existing allocation records for the consumer
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

When there **ARE NO** existing allocation records that referenced this
consumer UUID, the call will exhibit the following behavior:

* Microversion 1.13 - 1.X-1: always succeeds, and consumer records are always
  created since ``project_id`` and ``user_id`` will always be present. A
  generation will be created for these new consumer records

* Microversion 1.X: A new ``consumer_generation`` field will be required in the
  request payload **for each consumer allocation section**. It will be required
  to be ``None`` in order to indicate the caller expects that this is a new
  consumer.

Existing allocation records, but no consumer record for the consumer
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

When there **IS NOT** an existing consumer record, however there exist
allocation records for consumers referenced in the request, that means that a
user previously created allocations for that consumer using microversion <1.8.

In this case, the call will exhibit the following behavior:

* Microversion 1.13 - 1.X-1: always succeeds, and consumer records are always
  created since ``project_id`` and ``user_id`` will always be present. A
  generation will be created for these new consumer records

* Microversion 1.X: A new ``consumer_generation`` field will be required in the
  request payload **for each consumer allocation section**. It will be required
  to be ``None`` in order to indicate the caller expects that this is a new
  consumer.

Existing allocation records, existing consumer record for the consumer
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

When there **IS** an existing consumer record, the call will exhibit the
following behavior:

* Microversion 1.13 - 1.X-1: always succeeds, the existing consumer records
  will have their generation automatically incremented with no protection
  against concurrent updates

* Microversion 1.X: A new ``consumer_generation`` field will be required in the
  request payload **for each consumer allocation section**. It will be required
  to be equal to the value of the consumer's known generation. Placement will
  check that its known generation matches the given generation and return a
  ``409 Conflict`` if there is a mismatch. Furthermore, if another process
  modifies the same consumer's allocations concurrently to the request, the
  generation increment will fail for the consumer and a ``409 Conflict`` will
  be returned indicating a concurrent write occurred and the caller should
  re-read the consumer's generation and retry its request as appropriate.

``DELETE /allocations/{uuid}``
------------------------------

There are no changes to ``DELETE /allocations/{uuid}``. We were unable to find
a way to supply a consumer generation in the ``DELETE /allocations/{uuid}``
call.

Generation-safe deletions need to be done via PUT/POST with an empty
allocations dict.

Alternatives
------------

We could modify the way that allocations are handled, and allow for a PATCH
method to avoid accidentally overwriting another service's allocations. While
this will also address the race condition, it was not favored by many in the
discussions we had at the Rocky PTG.

We considered adding the generation to a header, queryparam, and payload on
DELETE but couldn't conscion the inconsistency.

Data model impact
-----------------

A new integer ``generation`` column, defaulting to 0,  will be added to
Placement's ``consumers`` table, and a corresponding migration will be created.

REST API impact
---------------


* /resource_providers/{uuid}/allocations - the GET method will be changed to
  return the current generation value for the consumer. The returned JSON will
  look like::

    {'resource_provider_generation': GENERATION,
     'allocations':
       CONSUMER_ID_1: {
           # This next line will be added to the response.
           'consumer_generation': CONSUMER1_GENERATION,
           'resources': {
              'DISK_GB': 4,
              'VCPU': 2
           }
       },
       CONSUMER_ID_2: {
           # This next line will be added to the response.
           'consumer_generation': CONSUMER2_GENERATION,
           'resources': {
              'DISK_GB': 6,
              'VCPU': 3
           }
       }
    }

* /allocations/<consumer_id> - The GET method will include the consumer
  generation in its response::

    {
        'allocations': {
            RP_UUID_1: {
                'generation': GENERATION,
                'resources': {
                    'DISK_GB': 4,
                    'VCPU': 2
                }
            },
            RP_UUID_2: {
                'generation': GENERATION,
                'resources': {
                    'DISK_GB': 6,
                    'VCPU': 3
                }
            }
        },
        'project_id': PROJECT_ID,
        'user_id': USER_ID,
        # This next line will be added to the response.
        'consumer_generation': CONSUMER_GENERATION
    }

  The PUT method will be changed to require consumer generation, and will
  return a 409 Conflict if the supplied generation does not match the current
  value in the consumers table. See above for detailed explanation of the
  expected behavior.

  In addition to the above changes, we will also be modifying the PUT method to
  accept empty allocations. This will allow similar behaviour to POST and
  facilitate a concurrent-update-safe DELETE operation for allocations.

* /allocations - The POST method accepts multiple allocations, and the schema
  will be modified in a new version to add a required value for
  'consumer_generation' at the same level as 'project_id' and 'user_id'::

        ... },
        "project_id": {
            "type": "string",
            "minLength": 1,
            "maxLength": 255
        },
        "user_id": {
            "type": "string",
            "minLength": 1,
            "maxLength": 255
        },
        # This section will be added to the schema.
        "consumer_generation": {
            "type": "integer",
            "minimum": 1,
        }
    },
    "required": [
        "allocations",
        "project_id",
        "user_id",
        # This will be a new required field in the POST request
        "consumer_generation"
    ]

POST will be changed to require consumer generation per consumer section.

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

Services that work with allocations will have to be updated to either retry the
allocation in the event of a conflict, or otherwise handle the allocation
failure. This may have a very small impact on overall performance, but is
expected to be negligible in most cases.

Other deployer impact
---------------------

None

Developer impact
----------------

Developers of services that interact with placement will have to modify their
code for allocating to specify the new microversion, and supply the appropriate
consumer generation in any allocation create or delete requests. They will also
have to add handler code in the event that an allocation attempt returns a
conflict.

Upgrade impact
--------------

A new online data migration hook will be added that will ensure consumer
records are created for any allocation that references a consumer UUID that has
no corresponding record in the consumers table. Two new CONF options --
``CONF.placement.incomplete_consumer_project_id`` and
``CONF.placement.incomplete_consumer_user_id`` will allow the deployer to set a
particular project or user UUID to use when creating missing consumer records
for allocations that were created prior to microversion 1.8.

Running the existing ``nova-manage db online_data_migrations`` CLI command will
automatically run this online data migration to create missing consumer
records.

Implementation
==============

Assignee(s)
-----------

Primary assignee:
  ed-leafe

Other contributors:
  cdent
  jaypipes

Work Items
----------

* Add the ``generation`` column to the consumers table, and create the
  corresponding migration script.

* Modify all the allocation handler code to increment the consumer generation
  on all changes.

* Modify input & output schemas/payloads to include the generation.

* Add generation conflict checking that will return a 409 if generations don't
  match.

* Add a microversion that requires consumer generation for all allocations.

Dependencies
============

None


Testing
=======

Functional tests will be added to verify that consumer generation values are
properly returned, and that any allocation for that consumer changes the
generation. They will also verify that allocation requests with a matching
generation succeed, and those with a non-matching generation fail with a 409
Conflict.


Documentation Impact
====================

The developer documentation for working with Placement will have to be updated
to include information about using consumer generations, and that services
using Placement should be updated to handle a 409 response when creating
allocations.

References
==========

* https://etherpad.openstack.org/p/nova-ptg-rocky-placement
  Rocky PTG etherpad, discussion on or around line 164

* http://lists.openstack.org/pipermail/openstack-dev/2018-March/128041.html
  Jay Pipes's Rocky PTG Placement recap email to the dev list, about halfway
  down
