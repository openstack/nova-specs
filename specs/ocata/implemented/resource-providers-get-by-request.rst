..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

===========================================================
Resource Providers - Filtered Resource Providers by Request
===========================================================

https://blueprints.launchpad.net/nova/+spec/resource-providers-get-by-request

This blueprint aims to modify the POST method of the resource_providers REST
resource so that it returns a list of resource providers that can support
the list of requested resource classes.

Problem description
===================

There is currently no way to get a list of resource providers that can fulfill
a set of requested resources by verifying that the respective inventories can
support the existing allocation plus the requested overhead.
That work is a necessary prerequisite for the scheduler being able to call the
placement API in order to narrow the list of acceptable hosts before calling
the filters.

Use Cases
----------

None.

Proposed change
===============

We propose to change the existing /resource_providers REST resource to
support a method providing a request body that would describe a list of
requested amounts of resource classes and would return a list of resource
providers supporting those amounts.

To be clear, the math for knowing whether a resource provider is acceptable
would be, for each resource class, take the related inventory, lookup the
allocations against that inventory and make sure that the amount of free
resource for the inventory is more or equal than the requested amount, with
respect to the defined allocation ratio and the reserved size.

Alternatives
------------

There can be many ways to provide a solution for getting a list of resource
providers but given we prefer to review the implementation rather than
nitpicking which HTTP method or which REST resource could be the best, I
prefer to add a disclaimer below.

Data model impact
-----------------

None.

REST API impact
---------------

.. warning ::

  The following REST API proposal is a possible solution that will be reviewed
  during the implementation. That means that the REST resource or the HTTP
  method could be eventually different in the Nova tree, implying that this
  spec would be amended in a later change.

The following new REST API call will be modified:

`POST /resource_providers`
*************************

The POST method for that /resource_providers REST resource will now accept
a new query string in the URI called 'request' that will return a list of
all the resource providers accepted a list of resource requirements.

Example::

    POST /resource_providers?request

The body of the request must match the following JSONSchema document::

            {
                "type": "object",
                "properties": {
                   "resources": {
                     "type": "object",
                     "patternProperties": {
                       "^[0-9a-fA-F-]+$": {
                         "type": "object",
                         "patternProperties": {
                           "^[A-Z_]+$": {"type": "integer"}
                         }
                       },
                       "additionalProperties": false
                     }
                },
                "required": [
                    "resources"
                ]
                "additionalProperties": False
            }


For example, a request body asking for VCPUs and RAM would look like::

          POST /resource_providers?request
          {
             "resources": {
               "VCPU": 2,
               "MEMORY_MB": 1024
             }
          }


The response would be::

    200 OK
    Content-Type: application/json

    {
      "resource_providers": [
        {
          "uuid": "b6b065cc-fcd9-4342-a7b0-2aed2d146518",
          "name": "RBD volume group",
          "generation": 12,
          "links": [
             {
               "rel": "self",
               "href": "/resource_providers/b6b065cc-fcd9-4342-a7b0-2aed2d146518"
             },
             {
               "rel": "inventories",
               "href": "/resource_providers/b6b065cc-fcd9-4342-a7b0-2aed2d146518/inventories"
             },
             {
               "rel": "aggregates",
               "href": "resource_providers/b6b065cc-fcd9-4342-a7b0-2aed2d146518/aggregates"
             },
             {
               "rel": "usages",
               "href": "resource_providers/b6b065cc-fcd9-4342-a7b0-2aed2d146518/usages"
             }
          ]
        },
        {
          "uuid": "eaaf1c04-ced2-40e4-89a2-87edded06d64",
          "name": "Global NFS share",
          "generation": 4,
          "links": [
             {
               "rel": "self",
               "href": "/resource_providers/eaaf1c04-ced2-40e4-89a2-87edded06d64"
             },
             {
               "rel": "inventories",
               "href": "/resource_providers/eaaf1c04-ced2-40e4-89a2-87edded06d64/inventories"
             },
             {
               "rel": "aggregates",
               "href": "resource_providers/eaaf1c04-ced2-40e4-89a2-87edded06d64/aggregates"
             },
             {
               "rel": "usages",
               "href": "resource_providers/eaaf1c04-ced2-40e4-89a2-87edded06d64/usages"
             }
          ]
        }
      ]
    }


In case a requested resource class doesn't exist, a HTTP400 will be returned.

Security impact
---------------

None.

Notifications impact
--------------------

None.

Other end user impact
---------------------

None.

Performance Impact
------------------

None.

Other deployer impact
---------------------

None.

Developer impact
----------------

None.

Implementation
==============

Assignee(s)
-----------

Primary assignee:
  bauzas

Other contributors:
  cdent
  jaypipes

Work Items
----------

* Write the math
* Expose the API change

Dependencies
============

None.

Testing
=======

Gabbi functional tests will cover that.

Documentation Impact
====================

Of course, we should amend the docs that we need to write anyway.


References
==========

None.
