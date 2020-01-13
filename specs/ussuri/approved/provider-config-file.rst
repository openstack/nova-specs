..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

===========================
Provider Configuration File
===========================

https://blueprints.launchpad.net/nova/+spec/provider-config-file

This is a proposal to configure resource provider inventory and traits using a
standardized YAML file format.

.. note:: This work is derived from `Jay's Rocky provider-config-file
          proposal`_ and `Konstantinos's device-placement-model spec`_ (which
          is derived from `Eric's device-passthrough spec`_), but differs in
          several substantive ways.

.. note:: This work is influenced by requirements to Nova to support non
          native compute resources that are managed by Resource Management
          Daemon for finer grain control. PTG discussion notes available at
          `Resource Management Daemon_PTG Summary`_

.. note:: We currently limit the ownership and consumption of the provider
          config YAML as described by the file format to Nova only.

.. note:: The provider config will currently only accept placement overrides
          to create and manage inventories and traits for resources not
          natively managed by the Nova virt driver.

.. note:: This is intended to define a) a file format for currently active use
          cases, and b) Nova's consumption of such files. Subsequent features
          can define the semantics by which the framework can be used by other
          consumers or enhanced to satisfy particular use cases.

Problem description
===================
In order to facilitate the proper management of resource provider information
in the placement API by agents within Nova (such as virt drivers and the
PCI passthrough subsystem), we require a way of expressing various
overrides for resource provider information. While we could continue to use
many existing and new configuration options for expressing this information,
having a standardized, versioned provider descriptor file format allows us to
decouple the management of provider information from the configuration of the
service or daemon that manages those resource providers.

Use Cases
---------
Note that the file format/schema defined here is designed to accommodate the
following use cases. The file format/schema currently addresses a few use cases
that require changes to resource provider information as consumed by virt
drivers in Nova but it should allow options for extensions to be consumed
by Nova or other services as described in the problem statement in the future.

Inventory Customization
~~~~~~~~~~~~~~~~~~~~~~~

**An operator would like to describe inventories for new platform features**

These features could be experimental or not yet completely supported by Nova.
The expectation is that Nova can manage these inventories and help schedule
workloads requesting support for new platform features against their
capacities. For instance, to report ``CUSTOM_LLC`` (last-level cache)
inventories.

The file defined by this spec must allow its author to:

* Identify a provider unambiguously.
* Create and manage inventories for resource classes not natively managed by
  Nova virt driver (``CUSTOM_LLC``, ``CUSTOM_MEMORY_BANDWIDTH`` etc.)

Trait Customization
~~~~~~~~~~~~~~~~~~~

**An operator wishes to associate new custom traits with a provider.**

These features could be experimental or not yet completely supported by Nova.
The expectation is that Nova can manage these traits and help schedule
workloads with support to new platform features against their traits.

The file defined by this spec must allow its author to:

* Identify a provider unambiguously.
* Specify arbitrary custom traits which are to be associated with the provider.

Proposed change
===============

Provider Config File Schema
---------------------------
A versioned YAML file format with a formal schema is proposed. The scope of
this spec is the schema, code to parse a file into a Python dict, code to
validate the dict against the schema, and code to merge the resulting dict with
the provider tree as processed by the resource tracker.

The code shall be introduced into the ``openstack/nova`` project initially and
consumed by the resource tracker. Parts of it (such as the schema definition,
file loading, and validation) may be moved to a separate oslo-ish library in
the future if it can be standardized for consumption outside of Nova.

The following is a simplified pseudo-schema for the file format.

.. code-block:: yaml

  meta:
    # Version ($Major, $minor) of the schema must successfully parse documents
    # conforming to ($Major, *). I.e. additionalProperties must be allowed at
    # all levels; but code at a lower $minor will ignore fields it does not
    # recognize. Schema changes representing optional additions should bump
    # $minor. Any breaking schema change (e.g. removing fields, adding new
    # required fields, imposing a stricter pattern on a value, etc.) must bump
    # $Major. The question of whether/how old versions will be deprecated or
    # become unsupported is left for future consideration.
    schema_version: $Major.$minor

  providers:
    # List of dicts
      # Identify a single provider to configure.
      # Exactly one of uuid or name is mandatory. Specifying both is an error.
      # The consuming nova-compute service will error and fail to start if the
      # same value is used more than once across all provider configs for name
      # or uuid.
      # NOTE: Caution should be exercised when identifying ironic nodes,
      # especially via the `$COMPUTE_NODE` special value. If an ironic node
      # moves to a different compute host with a different provider config, its
      # attributes will change accordingly.
    - identification:
          # Name or UUID of the provider.
          # The uuid can be set to the specialized string `$COMPUTE_NODE` which
          # will cause the consuming compute service to apply the configuration
          # in this section to each node it manages unless that node is also
          # identified by name or uuid.
          uuid: ($uuid_pattern|"$COMPUTE_NODE")
          # Name of the provider.
          name: $string
      # Customize provider inventories
      inventories:
          # This section allows the admin to specify various adjectives to
          # create and manage providers' inventories.  This list of adjectives
          # can be extended in the future as the schema evolves to meet new
          # use cases. For now, only one adjective, `additional`, is supported.
          additional:
              # The following inventories should be created on the identified
              # provider. Only CUSTOM_* resource classes are permitted.
              # Specifying inventory of a resource class natively managed by
              # nova-compute will cause the compute service to fail.
              $resource_class:
                  # `total` is required. Other optional fields not specified
                  # get defaults from the Placement service.
                  total: $int
                  reserved: $int
                  min_unit: $int
                  max_unit: $int
                  step_size: $int
                  allocation_ratio: $float
              # Next inventory dict, keyed by resource class...
              ...
      # Customize provider traits.
      traits:
          # This section allows the admin to specify various adjectives to
          # create and manage providers' traits.  This list of adjectives
          # can be extended in the future as the schema evolves to meet new
          # use cases. For now, only one adjective, `additional`, is supported.
          additional:
              # The following traits are added on the identified provider. Only
              # CUSTOM_* traits are permitted. The consuming code is
              # responsible for ensuring the existence of these traits in
              # Placement.
              - $trait_pattern
              - ...
    # Next provider...
    - identification:
      ...

Example
~~~~~~~
.. note:: This section is intended to describe at a very high level how this
          file format could be consumed to provide ``CUSTOM_LLC`` inventory
          information.

.. note:: This section is intended to describe at a very high level how this
          file format could be consumed to provide P-state compute trait
          information.

.. code-block:: yaml

  meta:
    schema_version: 1.0

  providers:
    # List of dicts
    - identification:
          uuid: $COMPUTE_NODE
      inventories:
          additional:
              CUSTOM_LLC:
                  # Describing LLC on this compute node
                  # max_unit indicates maximum size of single LLC
                  # total indicates sum of sizes of all LLC
                  total: 22
                  reserved: 2
                  min_unit: 1
                  max_unit: 11
                  step_size: 1
                  allocation_ratio: 1
      traits:
          additional:
              # Describing that this compute node enables support for
              # P-state control
              - CUSTOM_P_STATE_ENABLED

Provider config consumption from Nova
-------------------------------------
Provider config processing will be performed by the nova-compute process as
described below. There are no changes to virt drivers. In particular, virt
drivers have no control over the loading, parsing, validation, or integration
of provider configs. Such control may be added in the future if warranted.

Configuration
  A new config option is introduced::

    [compute]
    # Directory of yaml files containing resource provider configuration.
    # Default: /etc/nova/provider_config/
    # Files in this directory will be processed in lexicographic order.
    provider_config_location = $directory

Loading, Parsing, Validation
  On nova-compute startup, files in ``CONF.compute.provider_config_location``
  are loaded and parsed by standard libraries (e.g. ``yaml``), and
  schema-validated (e.g. via ``jsonschema``). Schema validation failure or
  multiple identifications of a node will cause nova-compute startup to fail.
  Upon successful loading and validation, the resulting data structure is
  stored in an instance attribute on the ResourceTracker.

Provider Tree Merging
  A generic (non-hypervisor/virt-specific) method will be written that merges
  the provider config data into an existing ``ProviderTree`` data structure.
  The method must detect conflicts whereby provider config data references
  inventory of a resource class managed by the virt driver. Conflicts should
  log a warning and cause the conflicting config inventory to be ignored.
  The exact location and signature of this method, as well as how it detects
  conflicts, is left to the implementation. In the event that a resource
  provider is identified by both explicit UUID/NAME and $COMPUTE_NODE, only the
  UUID/NAME record will be used.

``_update_to_placement``
  In the ResourceTracker's ``_update_to_placement`` flow, the merging method is
  invoked after ``update_provider_tree`` and automatic trait processing, *only*
  in the ``update_provider_tree`` flow (not in the legacy ``get_inventory`` or
  ``compute_node_to_inventory_dict`` flows). On startup (``startup == True``),
  if the merge detects a conflict, the nova-compute service will fail.

Alternatives
------------
Ad hoc provider configuration is being performed today through an amalgam of
oslo.config options, more of which are being proposed or considered to deal
with VGPUs, NUMA, bandwidth resources, etc. The awkwardness of expressing
hierarchical data structures has led to such travesties as
``[pci]passthrough_whitelist`` and "dynamic config" mechanisms where config
groups and their options are created on the fly. YAML is natively suited for
this purpose as it is designed to express arbitrarily nested data structures
clearly, with minimal noisy punctuation. In addition, the schema is
self-documenting.

Data model impact
-----------------
None

REST API impact
---------------
None

Security impact
---------------
Admins should ensure that provider config files have appropriate permissions
and ownership. Consuming services may wish to check this and generate an error
if a file is writable by anyone other than the process owner.

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
An understanding of this file and its implications is only required when the
operator desires provider customization. The deployer should be aware of the
precedence of records with UUID/NAME identification over $COMPUTE_NODE.

Developer impact
----------------
Subsequent specs will be needed for services consuming this file format.

Upgrade impact
--------------
None. (Consumers of this file format will need to address this - e.g. decide
how to deprecate existing config options which are being replaced).

Implementation
==============

Assignee(s)
-----------

Primary assignee:
  dustinc

Other contributors:
  efried dakshinai

Feature Liaison
---------------

Feature liaison:
  efried

Work Items
----------

* Construct a formal schema
* Implement parsing and schema validation
* Implement merging of config to provider tree
* Incorporate above into ResourceTracker
* Compose a self-documenting sample file

Dependencies
============
None


Testing
=======
* Schema validation will be unit tested.
* Functional and integration testing to move updates from provider config file
  to Placement via Nova virt driver.

Documentation Impact
====================
* The formal schema file and a self-documenting sample file for provider
  config file.
* Admin-facing documentation on guide to update the file and how Nova
  processes the updates.
* User-facing documentation (including release notes).

References
==========
.. _Jay's Rocky provider-config-file proposal: https://review.openstack.org/#/c/550244/2/specs/rocky/approved/provider-config-file.rst
.. _Konstantinos's device-placement-model spec: https://review.openstack.org/#/c/591037/8/specs/stein/approved/device-placement-model.rst
.. _Eric's device-passthrough spec: https://review.openstack.org/#/c/579359/10/doc/source/specs/rocky/device-passthrough.rst
.. _Resource Management Daemon_PTG Summary: http://lists.openstack.org/pipermail/openstack-discuss/2019-May/005809.html
.. _Handling UUID/NAME and $COMPUTE_NODE conflicts: http://eavesdrop.openstack.org/irclogs/%23openstack-nova/%23openstack-nova.2019-11-19.log.html#t2019-11-19T21:25:26

History
=======

.. list-table:: Revisions
   :header-rows: 1

   * - Release Name
     - Description
   * - Stein
     - Introduced
   * - Train
     - Re-proposed, simplified
   * - Ussuri
     - Re-proposed
