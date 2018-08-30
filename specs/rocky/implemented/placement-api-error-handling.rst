..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

============================
Placement API error handling
============================

https://blueprints.launchpad.net/nova/+spec/placement-api-error-handling

This blueprint aims to extend the placement API to include detailed, consistent
error messages in the response body to allow clear distinctions between
different errors that use the same HTTP status code.

Problem description
===================

Error conditions in the placement REST API are signalled by HTTP status codes
and message bodies. For some of the errors it is impossible to distinguish the
reason why a particular response was issued other than reading the message
which was returned in the response body. This approach creates a strong
coupling between client code and the exact message of the error response. This
is very fragile in the face of change.

Use Cases
---------

As a consumer of the placement API, I want to be able to clearly distinguish
the different reasons for failed requests, especially in the case where there
are different causes for the same HTTP status code, so that I can react to each
case accordingly.

Proposed change
===============

We propose to extend existing HTTP error responses with a ``code`` field as
described in the API-WG Errors_ specification. This will help consumers of the
API to easily recognize the type of the error cases. Note that the new format
of the response is for ``application/json`` only (because of the way WebOb is
used it is possible, if the ``accept`` header specifies something other than
``application/json``, to get an error response that is ``text/plain`` or
``text/html``).

The exact implementation for doing this requires some experimentation. Webob's
error formatting makes it quite challenging to get at the desired information
(the formatter does not have clean access to the exception object). The most
straightforward thing to do is to inject the WSGI ``environ`` with the required
information when creating an exception. Doing this elegantly is where the
experimentation comes in. There is a `work in progress`_ spike.

This spec does not propose changing every error response. Instead the goal is
to add the framework that makes it possible for the ``code`` field to be
defined as required. This is for at least two reasons:

* Making all the changes at once will require a lot of churn in the code for
  limited immediate value.
* Delaying implementation while we determine a complete ontology for placement
  error responses may delay us until the heat death of the universe.

For those errors where a specific code is not yet required, a generic code will
be present. A new microversion will be created. Before that microversion, no
code is present. After that microversion a code will always be present but it
will not always be specific to any given error.

Alternatives
------------

We can keep things as they are, examining strings in the returned messages from
the API response to determine what the cause was for a certain error. This is
considered insufficiently robust.

We can more completely implement the Errors_ specification by also adding a
``help`` link that points to documentation that explains the error code. That
is not proposed here as it depends on building a new collection of
documentation, and the immediate need is to be able effectively distinguish
errors. If it turns out that we want it, we can always add it later.

We could consider whether we need or want the addition of codes to individual
error responses to be bounded by a microversion. Historically, changes in error
bodies have not required a microversion, but in this case the presence of the
code enables a different code path in the client (check the code instead of
parse a string). Signalling this by way of a microversion could be nice but at
the same time code could just check for the `code` key in the response.
Another option could be to microversion as needed. For example, the case of
inventory violation conflicts (versus generation conflicts), might be a good
choice. The model of handling microversions described in the proposed change
above is preferred as it is simpler.

Data model impact
-----------------

None

REST API impact
---------------

A framework will be added such that when raising WebOb-based exceptions,
a code can optionally be added which, if present, will extend the JSON-based
error response.

This means that responses that looked like this::

  Content-Type: application/json
  {
    "errors": [
      {
        "status": [status],
        "title": "[title]",
        "detail": "[detail]",
        "request_id": "[request_id]"
        ]
      }
    ]
  }

will gain a ``code`` field as follows::

  Content-Type: application/json
  {
    "errors": [
      {
        "code": "[code]",
        "status": [status],
        "title": "[title]",
        "detail": "[detail]",
        "request_id": "[request_id]"
        ]
      }
    ]
  }

``code`` is a unique and meaningful string for each error condition with a
prefix of ``placement.``. For instance, when creating a new resource provider,
if the name of the resource provider already exists and a ``409`` response is
made, it is distinguished from other ``409`` responses by a code of
``placement.resource_provider.name_exists``.

.. note:: It is not the purpose of this specification to come up with a naming
          scheme for error codes. The above is an example only.

The ``code`` string is unique to the handler methods in the placement API code
that raises the exception. Once a code is chosen for a specific error situation
it must not change.

Exceptions that are raised without a code will receive a generic code. The
expectation is that more specific codes will be added incrementally, as
required.

The initial addition of ``code`` support will be done in a microversion change,
but later additions of new codes will not.

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

As codes are added to error responses, client code will be able to use them to
distinguish between errors that have the same HTTP status code.

Upgrade impact
--------------

None.


Implementation
==============

Assignee(s)
-----------

Primary assignee:
  Chris Dent (cdent)

Work Items
----------

* Determine best method for providing the information to
  ``json_error_formatter``.
* Update at least one handler to provide ``code`` for an exception it
  explicitly raises.
* Update gabbi tests accordingly.
* Document the added codes in the `placement api-ref`_.
* Document the need to add codes in the `placement contributor docs`_.

Dependencies
============

None

Testing
=======

Update/provide new gabbi tests that check for error codes.

Documentation Impact
====================

The `placement api-ref`_ will be updated to reflect the addition of codes on
those error responses that are changed.

References
==========

* Errors_ description from API-WG.
* A spiked `work in progress`_.


.. _Errors:  http://specs.openstack.org/openstack/api-wg/guidelines/errors.html
.. _work in progress: https://review.openstack.org/#/c/546177/
.. _placement api-ref: https://developer.openstack.org/api-ref/placement/
.. _placement contributor docs: https://docs.openstack.org/nova/latest/contributor/placement.html

History
=======

.. list-table:: Revisions
   :header-rows: 1

   * - Release Name
     - Description
   * - Queens
     - Introduced
   * - Rocky
     - Re-proposed
