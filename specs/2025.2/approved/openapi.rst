..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

===============
OpenAPI Schemas
===============

https://blueprints.launchpad.net/nova/+spec/openapi-3

We would like to start documenting our APIs in an industry-standard,
machine-readable manner. Doing so opens up many opportunities for both
OpenStack developer and OpenStack users alike, notably the ability to both
auto-generate and auto-validate both client tooling and documentation alike. Of
the many API description languages available, OpenAPI (fka "Swagger") appears
to be the one with both the largest developer mindshare and the one that would
be the best fit for OpenStack due to the existing tooling used in many
OpenStack services, thus we would opt to use this format.

.. note::

    This is a continuation of a spec that was previously approved in Dalmatian
    (2024.2) and Epoxy (2025.1). We merged all of the groundwork for this in
    Dalmatian and worked on the response bodies schemas in Epoxy but did not
    get them completed.

Problem description
===================

The history of API description languages has been mainly a history of
half-baked ideas, unnecessary complication, and in general lots of failure.
This history has been reflected in OpenStack's own history of attempting to
document APIs, starting with our early use of WADL through to our experiments
with Swagger 2.0 and RAML, leading to today's use of our custom ``os_api_ref``
project, built on reStructuredText and Sphinx.

It is only in recent years that things have started to stabilise somewhat, with
the development of widely used API description languages like OpenAPI, RAML and
API Blueprint, as well as supporting SaaS tools such as Postman and Apigee.
OpenAPI in particular has seen broad adoption across multiple sectors, with
sites as varied as `CloudFlare`__ and `GitHub`__ providing OpenAPI schemas for
their APIs. OpenAPI has evolved significantly in recent years and now supports
a wide variety of API patterns including things like webhooks. Even more
beneficial for OpenStack, OpenAPI 3.1 is a full superset of JSON Schema meaning
we have the ability to re-use much of the validation we already have.

.. __: https://blog.cloudflare.com/open-api-transition
.. __: https://github.com/github/rest-api-description

Use Cases
---------

As an end user, I would like to have access to machine-readable, fully
validated documentation for the APIs I will be interacting with.

As an end user, I want statically viewable documentation hosted as part of the
existing docs site without requiring a running instance of Nova.

As an SDK/client developer, I would like to be able to auto-generate bindings
and clients, promoting consistency and minimising the amount of manual work
needed to develop and maintain these.

As a Nova developer, I would like to have a verified API specification that I
can use should I need to replace the web framework/libraries we use in the
event they are no longer maintained.

Proposed change
===============

This effort can be broken into a number of distinct steps:

- Add a new decorator for removed APIs and actions

  We have a number of APIs and actions that no longer have backing code and
  return ``HTTP 410 (Gone)`` or ``HTTP 400 (Bad Request)``, respectively. We
  will not add schemas for these in the initial attempt at this so we need some
  mechanism to indicate this. We will add a new ``removed`` decorator that will
  highlight these removed APIs and indicate the version they were removed in
  and the reason for their removal. We can later use this as a heuristic in our
  tests to skip schema checks for these methods.

  .. note::

     This was completed in Dalmatian (2024.2)

- Add missing request body and query string schemas

  There is already good coverage of both request bodies and query string
  parameters but it is not complete. A list of incomplete schemas is given at
  the end of this section. The additional schemas will merely validate what is
  already allowed, which will mean extensive use of ``"additionalProperties":
  true`` or empty schemas. Put another way, an API that currently ignores
  unexpected request body fields or query string parameters will continue to
  ignore them. We may wish to make these stricter, as we did for most APIs in
  microversion 2.75, but that is a separate issue that should be addressed
  separately.

  Once these specs are added, tests will be added to ensure all non-deprecated
  and non-removed API resources have appropriate schemas.

  .. note::

     This was completed in Dalmatian (2024.2)

- Add response body schemas

  These will be sourced from existing OpenAPI schemas, currently published
  at `github.com/gtema/openstack-openapi`__, from `Tempest's API schemas`__,
  and where necessary from new schemas auto-generated from JSON response bodies
  generated in tests and manually modified handle things like enum values.

  Once these are added, tests will be added to ensure all non-deprecated and
  non-removed API resources have appropriate response body schemas. In
  addition, we will add a new configuration option that will control how we do
  verification at the API layer, ``[api] response_validation``. This will be an
  enum value with three options:

  ``error``
    Raise a HTTP 500 (Server Error) in the event that an API returns an
    "invalid" response.

    This will be the default in CI i.e. for our unit, functional and
    integration tests. This should not be used in production. The help text
    of the option will indicate this and we will set the ``advanced`` option.

  ``warn``
    Log a warning about an "invalid" response, prompting operations to file a
    bug report against Nova.

    This will be initial (and likely forever) default in production.

  ``ignore``
    Disable API response body validation entirely. This is an escape hatch in
    case we mess up.

  .. note:

     It is important to note that this option will only affect response body
     validation. Request body and request query string parameter validation
     will remain mandatory and will not be configurable.

.. __: https://github.com/gtema/openstack-openapi
.. __: https://github.com/openstack/tempest/tree/c0da6e843a/tempest/lib/api_schema/response/compute

.. note::

    The development of tooling required to gather these JSON Schema schemas and
    generate an OpenAPI schema will not be developed inside Nova and is
    therefore not covered by this spec. Nova will merely consume the resulting
    tooling for use in documentation. It is intended that the same tool will be
    usable across any OpenStack project that uses the same web frameworks
    (in Nova's case, WebOb + Routes).

.. note::

    The impact of middleware that modifies either the request or response will
    not be accounted for in this change. This is because these are configurable
    and they cannot be guaranteed to exist in a given deployment. Examples
    include the ``sizelimit`` middleware from ``oslo.middlware`` and the
    ``auth_token`` middleware from ``keystonemiddleware``.

Alternatives
------------

- Use a different tool

  We could use a different tool than OpenAPI to publish our specs. In a manner
  of speaking we already do this - albeit not in a machine-readable manner -
  through our use of os-api-ref.

  This idea has been rejected because OpenAPI is clearly the best tool for the
  It is the most widely used API description language available today and
  aligns well with our existing use of JSON Schema for API validation. While it
  does not support OpenStack's microversion API design pattern out-of-the-box,
  previous experiments have demonstrated that it is extensible enough to add
  this.

- Maintain these specs out-of-tree

  We could use a separate repo to store and maintain specs for Nova and the
  other OpenStack services.

  This idea has been rejected because it prevents us testing the specs on each
  commit to Nova and means work that could be spread across multiple teams is
  instead focused on one small team. It will result in more bugs and a lag
  between changes to the Nova API and changes to the out-of-tree specs. It will
  result in duplication of effort across Nova, Tempest, and the specs projects.

- Publish the spec via an API resource rather than in our docs

  We could publish the spec via a new, unversioned API endpoint such as
  ``/spec``. A ``GET`` request to this would return the full spec, either
  statically generated at deployment time or dynamically generated (and then
  cached) at runtime.

  This is rejected because it brings limited advantages and multiple
  disadvantages. Nova's API is designed to be backwards-compatible and
  non-extensible. As such, a user with the latest version of the spec should be
  able to use it to communicate with any OpenStack deployment running a version
  of Nova that supports microversions. It is also expected that the "master"
  version of the spec will continuously improve as things are tightened up,
  documentation is improved, and bugs or mistakes are corrected. We want
  consumers of the spec to see these changes immediately rather than wait for
  their deployment to be updated. Finally, OpenStack's previous forays into
  discoverable APIs, such as Keystone's use of JSONHome or Glance's attempts to
  publish resource schemas, have seen limited take-up outside of the projects
  themselves. Taken together, this all suggests there is no reason or advantage
  to publishing deployment-specific specs and users would be better served by
  fetching the latest version of the spec from the api-ref documentation
  published on docs.openstack.org (which, one should note, is itself
  intentionally unversioned).

Data model impact
-----------------

None.

REST API impact
---------------

There will be no direct REST API impact. Users will see HTTP 500 error if they
set ``[api] response_validation = error`` and encounter an invalid response,
however, we will not encourage use of this option in production and will
instead focus on validating this ourselves in CI.

We may wish to address issues that are uncovered as we add schemas, but this
work is considered secondary to this effort and can be tackled separately.

Security impact
---------------

None.

Notifications impact
--------------------

None.

Other end user impact
---------------------

This should be very beneficial for users who are interested in developing
client and bindings for OpenStack. In particular, this should (after an initial
effort in code generation) reduce the workload of the SDK team as well as teams
outside of OpenStack that work on client tooling such as the Gophercloud team.

Performance Impact
------------------

There will be a minimal impact on API performance when validation is enabled as
we will now verify both requests and responses for all API resources. Given our
existing extensive use of JSON Schema for API validation, it is expected that
this should not be a significant issue.

Other deployer impact
---------------------

As noted previously, there will be one new config option, ``[api]
response_validation``. Operators may see increased warnings in their logs due
to incomplete schemas, but most if not all of these issues should be ironed out
by our CI coverage.

Developer impact
----------------

Developers working on the API microversions will now be encouraged to provide
JSON Schema schemas for both requests and responses.

Upgrade impact
--------------

None.


Implementation
==============

Assignee(s)
-----------

Primary assignee:
  stephenfinucane

Other contributors:
  gtema

Feature Liaison
---------------

None.

Work Items
----------

- Add missing request body schemas
- Add tests to validate existence of request body schemas
- Add missing query string schemas
- Add tests to validate existence of query string schemas
- Add response body schemas
- Add decorator to validate response body schemas against response
- Add tests to validate existence of response body schemas

Dependencies
============

The actual generation of an OpenAPI documentation will be achieved via a
separate tool. It is not yet determined if this tool will live inside an
existing project, such as ``os_api_ref`` or ``openstacksdk``, or inside a
wholly new project. In any case, it is envisaged that this tool will handle
OpenStack-specific nuances like microversions that don't map 1:1 to OpenAPI
concepts in a consistent and documented fashion.

Testing
=======

Unit tests will ensure that schemas eventually exist for request bodies, query
strings, and response bodies.

Unit, functional and integration tests will all work together to ensure that
response body schemas match real responses by setting ``[api]
response_validation`` to ``error``.

Documentation Impact
====================

Initially there should be no impact as we will continue to use ``os_api_ref``
as-is for our ``api-ref`` docs. Eventually we will replace or extend this
extension to generate documentation from our OpenAPI schema.

References
==========

APIs missing schemas
--------------------

These are the APIs that are currently (as of 2024-04-11, commit ``1bca24aeb``)
missing API request body schemas and query string schemas.

.. rubric:: Missing request body schemas

- ``AdminActionsController._inject_network_info``
- ``AdminActionsController._reset_network``
- ``AgentController.create``
- ``AgentController.update``
- ``BareMetalNodeController._add_interface``
- ``BareMetalNodeController._remove_interface``
- ``BareMetalNodeController.create``
- ``CellsController.create``
- ``CellsController.sync_instances``
- ``CellsController.update``
- ``CertificatesController.create``
- ``CloudpipeController.create``
- ``CloudpipeController.update``
- ``ConsolesController.create``
- ``DeferredDeleteController._force_delete``
- ``DeferredDeleteController._restore``
- ``FixedIPController.reserve``
- ``FixedIPController.unreserve``
- ``FloatingIPBulkController.create``
- ``FloatingIPBulkController.update``
- ``FloatingIPController.create``
- ``FloatingIPBulkController.create``
- ``FloatingIPBulkController.update``
- ``FloatingIPController.create``
- ``FloatingIPDNSDomainController.update``
- ``FloatingIPDNSEntryController.update``
- ``LockServerController._unlock``
- ``NetworkAssociateActionController._associate_host``
- ``NetworkAssociateActionController._disassociate_host_only``
- ``NetworkAssociateActionController._disassociate_project_only``
- ``NetworkController._disassociate_host_and_project``
- ``NetworkController.add``
- ``NetworkController.create``
- ``PauseServerController._pause``
- ``PauseServerController._unpause``
- ``RemoteConsolesController.get_rdp_console``
- ``RescueController._unrescue``
- ``SecurityGroupActionController._addSecurityGroup``
- ``SecurityGroupActionController._removeSecurityGroup``
- ``SecurityGroupController.create``
- ``SecurityGroupController.update``
- ``SecurityGroupDefaultRulesController.create``
- ``SecurityGroupRulesController.create``
- ``ServersController._action_confirm_resize``
- ``ServersController._action_revert_resize``
- ``ServersController._start_server``
- ``ServersController._stop_server``
- ``ShelveController._shelve``
- ``ShelveController._shelve_offload``
- ``SuspendServerController._resume``
- ``SuspendServerController._suspend``
- ``TenantNetworkController.create``

.. rubric:: Missing request query string schemas

- ``AgentController.index``
- ``AggregateController.index``
- ``AggregateController.show``
- ``AvailabilityZoneController.detail``
- ``AvailabilityZoneController.index``
- ``BareMetalNodeController.index``
- ``BareMetalNodeController.show``
- ``CellsController.capacities``
- ``CellsController.detail``
- ``CellsController.index``
- ``CellsController.info``
- ``CellsController.show``
- ``CertificatesController.show``
- ``CloudpipeController.index``
- ``ConsoleAuthTokensController.show``
- ``ConsolesController.index``
- ``ConsolesController.show``
- ``ExtensionInfoController.index``
- ``ExtensionInfoController.show``
- ``FixedIPController.show``
- ``FlavorAccessController.index``
- ``FlavorExtraSpecsController.index``
- ``FlavorExtraSpecsController.show``
- ``FlavorsController.show``
- ``FloatingIPBulkController.index``
- ``FloatingIPBulkController.show``
- ``FloatingIPController.index``
- ``FloatingIPController.show``
- ``FloatingIPDNSDomainController.index``
- ``FloatingIPDNSEntryController.show``
- ``FloatingIPPoolsController.index``
- ``FpingController.index``
- ``FpingController.show``
- ``HostController.reboot``
- ``HostController.show``
- ``HostController.shutdown``
- ``HostController.startup``
- ``HypervisorsController.detail``
- ``HypervisorsController.index``
- ``HypervisorsController.search``
- ``HypervisorsController.servers``
- ``HypervisorsController.show``
- ``HypervisorsController.statistics``
- ``HypervisorsController.uptime``
- ``IPsController.index``
- ``IPsController.show``
- ``ImageMetadataController.index``
- ``ImageMetadataController.show``
- ``ImagesController.detail``
- ``ImagesController.index``
- ``ImagesController.show``
- ``InstanceActionsController.index``
- ``InstanceActionsController.show``
- ``InstanceUsageAuditLogController.index``
- ``InstanceUsageAuditLogController.show``
- ``InterfaceAttachmentController.index``
- ``InterfaceAttachmentController.show``
- ``NetworkController.index``
- ``NetworkController.show``
- ``QuotaClassSetsController.show``
- ``QuotaSetsController.defaults``
- ``QuotaSetsController.detail``
- ``QuotaSetsController.show``
- ``SecurityGroupController.show``
- ``SecurityGroupDefaultRulesController.index``
- ``SecurityGroupDefaultRulesController.show``
- ``ServerDiagnosticsController.index``
- ``ServerGroupController.show``
- ``ServerMetadataController.index``
- ``ServerMetadataController.show``
- ``ServerMigrationsController.index``
- ``ServerMigrationsController.show``
- ``ServerPasswordController.index``
- ``ServerSecurityGroupController.index``
- ``ServerTagsController.index``
- ``ServerTagsController.show``
- ``ServerTopologyController.index``
- ``ServerVirtualInterfaceController.index``
- ``ServersController.show``
- ``SnapshotController.show``
- ``TenantNetworkController.index``
- ``TenantNetworkController.show``
- ``VersionsController.show``
- ``VolumeAttachmentController.show``
- ``VolumeController.show``

.. note::

   We should emphasise that many - but not all - of the aforementioned APIs
   are either deprecated or removed. We may wish *not* to add schemas for
   these, though by doing so we will lose the ability to generate documentation
   or clients for these APIs from the OpenAPI spec.

History
=======

.. list-table:: Revisions
   :header-rows: 1

   * - Release Name
     - Description
   * - 2024.2 Dalmatian
     - Introduced. Missing query schema and request body schemas added.
   * - 2025.1 Epoxy
     - Re-proposed to finish response body schemas.
   * - 2025.2 Flamingo
     - Re-proposed to finish response body schemas.
