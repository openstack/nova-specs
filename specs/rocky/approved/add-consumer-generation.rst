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

There will be no changes to the ``allocations`` table, but there will be
changes to the Allocation and AllocationList objects. Allocation will have a
``consumer_generation`` nullable IntegerField added, and AllocationList will
have a ``enforce_consumer_generation`` BooleanField added, with a default of
False to preserve old behavior. These fields are needed to to pass the consumer
generation information from the API layer to the object layer. They will not be
persisted to the database.

Below is a summary of the behaviors after this change is made:

When there is no existing consumer record:

* Old microversion: always succeeds, and new consumer record created. Since
  calls using older microversions may not pass the project_id and user_id in
  the request, those columns in the consumers table will be changed to allow
  null values. In that case, the consumer record will contain the consumer ID
  and the generation, but the project_id and user_id columns will be NULL.

* New microversion, CG = None: Success. Since there is no existing record,
  passing None indicates that the caller's view of the state of the consumer
  matches reality.

* New microversion, CG = <anything other than None>: Fail. A 409 Conflict will
  be the response, as the view of the state of the consumer for the caller is
  not in sync with the database.

When there is an existing consumer record:

* Old microversion: always succeeds. The value of the generation field will be
  incremented, but the other fields will remain untouched.

* New microversion, CG = None: Fail. The caller beieves there is no existing
  consumer, and so is not in sync.

* New microversion, CG = <anything other than current gen in DB>: Fail. Again,
  something else has modified the allocations for the consumer, and the caller
  is not in sync.

* New microversion, CG = <matches DB>: Success.


Alternatives
------------

We could modify the way that allocations are handled, and allow for a PATCH
method to avoid accidentally overwriting another service's allocations. While
this will also address the race condition, it was not favored by many in the
discussions we had at the Rocky PTG.

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

  The PUT and DELETE methods will be changed to require consumer generation,
  and will return a 409 Conflict if the supplied generation does not match the
  current value in the consumers table. Currently the consumer_uuid is obtained
  from the request environ; with this change, consumer_generation will also be
  required. If it is missing, a 400 Bad Request will be returned.

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

None


Implementation
==============

Assignee(s)
-----------

Primary assignee:
  ed-leafe

Other contributors:
  cdent

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
