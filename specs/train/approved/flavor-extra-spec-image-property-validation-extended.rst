..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

=======================================
Flavor Extra Spec Validation (Extended)
=======================================

https://blueprints.launchpad.net/nova/+spec/flavor-extra-spec-image-property-validation-extended

Introduce a YAML-based schema describing flavor extra specs, image metadata
properties, and the relationship between each.

Problem description
===================

Flavor extra specs are one of the Wild West aspects of nova. There are a number
of issues we'd like to address:

- Lack of documentation for many flavor extra specs and image metadata
  properties [1]_. Yes, we have Glance image metadata definitions but they're
  generally rather out-of-date, we don't/can't consume them in Nova, and
  they're not aimed towards user-facing documentation.

- Outdated, incomplete or incorrect Glance metadata definitions.

- No warnings if there is a typo in your extra spec, resulting in different
  behavior to that expected.

- No defined way to do things like deprecate a flavor extra spec, resulting in
  continued reinvention of the wheel.

Use Cases
---------

* As a deployer, I'd like to know what flavor extra specs and image metadata
  properties are available and why I'd want to use them.

* As a deployer, I'd like nova to tell me when I've used a flavor extra spec
  that doesn't exist or has a typo in it.

* As a developer, I'd like an easy way to deprecate flavor extra specs, which
  is something that will only become more common if we do things like move
  tracking of dedicated CPUs into placement.

* As a documentation writer, I'd like to be able to cross-reference the various
  flavor extra specs and image metadata properties available.

Proposed change
===============

A flavor extra spec is a key-value pair. For example::

    hw:cpu_policy=dedicated

Different solutions are needed to validate the *value* part of an extra spec
compared to the *key* part. This spec aims to tackle validation of both *key*
and *value*, starting with the latter and then moving onto the former.

The following are considered out-of-scope for this change:

- Enforcement of extra spec dependencies. For example, if extra spec A requires
  extra spec B be configured first. We will document the dependency but it
  won't be enforced.

- Enforcement of virt driver dependencies. Unfortunately, while flavor extra
  specs should be generic, this isn't always the case. As above, we will
  document this dependency but it won't be enforced.

- Hard enforcement of key validation. Eventually we will want to track all
  possible extra spec names and raise a warning or error for errant values, but
  this is likely to take some time to perfect. In the interim, we will merely
  log these potentially errant values.

This change builds upon `Flavor extra spec image metadata validation
<http://specs.openstack.org/openstack/nova-specs/specs/stein/approved/flavor-extra-spec-image-property-validation.html>`,
which covers some of these issues for us.

Value validation
----------------

Value validation is the easier of the two issues to tackle. It will resolve
issues like the following in a generic manner::

    hw:cpu_policy=deddddicated

For a generic extra spec, a definition of a validator will need to contain the
following:

- Name or *key* of the extra spec, e.g. ``cpu_policy`` for the above example

- Namespace of the extra spec, e.g. ``hw`` for the above example

- Description of the extra spec

- Support status of the extra spec

- Valid values; whether it's an integer, a free-form string, a string matching
  a given regex, an enum, or something else entirely

- Virt driver dependencies; this is only for documentation purposes and will
  not be enforced

- Extra spec dependencies; this is only for documentation purposes and will not
  be enforced

For many extra specs namespaces, we propose maintaining the definitions
in-tree. To do this, we propose adding a new module,
``nova.api.validation.extra_specs``, which will contain definitions for *flavor
validators*. These will be defined using two new base objects,
``BaseValidator`` and ``BaseExtraSpec``. ``BaseValidator`` will be subclassed
to represent a namespace while ``BaseExtraSpec`` will be subclassed to
represent an individual extra spec. ``BaseExtraSpec`` subclasses will be
registered again a namespace.

For example:

.. code-block:: python

    class HWValidator(BaseValidator):
        """A validator for the ``hw`` namespace."""
        name = 'hw'
        description = (
            'Extra specs that modify behavior of the virtual hardware '
            'associated with instances.'
        )

    class CPUPolicy(BaseExtraSpec):
        """A validator for the ``hw:cpu_policy`` extra spec."""
        name = 'cpu_policy'
        description = (
            'The policy to apply when determining what host CPUs the guest '
            'CPUs can run on. If ``shared`` (default), guest CPUs can be '
            'overallocated but cannot float across host cores. If '
            '``dedicated``, guest CPUs cannot be overallocated but are '
            'individually pinned to their own host core.'
        )
        deprecated = True
        value = {
            'type': str,
            'description': 'The CPU policy.',
            'enum': [
                'dedicated',
                'shared'
            ],
        }

    class NUMACPUs(BaseExtraSpec):
        """A validator for the ``hw:numa_cpu.{id}`` extra spec."""
        name = 'numa_cpu.{id}'
        description = (
            'A mapping of **guest** CPUs to the **guest** NUMA node '
            'identified by ``{id}``. This can be used to provide asymmetric '
            'CPU-NUMA allocation and is necessary where the number of guest '
            'NUMA nodes is is not a factor of the number of guest CPUs.'
        )
        params = [
            {
                'name': 'id',
                'type': int,
                'description': 'The ID of the **guest** NUMA node.',
            },
        ]
        value = {
            'type': str,
            'description': (
                'The guest CPUs, in the form of a CPU map, to allocate to the '
                'guest NUMA node identified by ``{id}``.'
            ),
            'pattern': r'\d+((-\d+)?(,\^?\d+(-\d+)?)?)*',
        }

    register(HWValidator, CPUPolicy)
    register(HWValdiator, NUMACPUs)

While many of the definitions will be maintained in-tree, some namespaces will
require special handling as they're owned by external services, e.g. the
``traits`` namespace (owned by os-traits) or the ``accel`` namespace (proposed
for use by cyborg). For these, we propose using `stevedore`_ to allow external
projects to register custom validators. For example, nova would provide the
following:

.. code-block:: ini

    nova.extra_spec_validators =
        hw = nova.api.validation.extra_specs:HWValidator
        os = nova.api.validation.extra_specs:OSValidator
        traits = nova.api.validation.extra_specs:TraitsValidator
        resources = nova.api.validation.extra_specs:ResourcesValidator
        custom = nova.validators.extra_specs:NoopValidator
        * = nova.validators.extra_specs:YAMLValidator

Cyborg could extend this by providing something like the following:

.. code-block:: ini

    nova.extra_spec_validators =
        accel = cyborg.extra_specs_validator:AccelValidator

Finally, there are extra specs that are operator defined and therefore will not
be known by a consuming service. For these, we propose introducing a schema
definition file. This a YAML-formatted file, which describes the flavor extra
specs available. The YAML format is chosen as it allows us to define a
specification in a declarative manner while avoiding the need to write Python
code. The format of this file will nonetheless mirror the format of the Python
objects. For example:

.. code-block:: yaml

    ---
    version: 1.0
    metadata:
    - name: numa_nodes
      namspace: hw
      description: >
        The number of NUMA nodes the instance should have.
      value:
        type: integer
        description: >
          The number of NUMA nodes the instance should have.

    - name: numa_cpus.{id}
      namspace: hw
      description: >
        A mapping of **guest** CPUs to the **guest** NUMA node identified by
        ``{id}``. This can be used to provide asymmetric CPU-NUMA allocation
        and is necessary where the number of guest NUMA nodes is is not a
        factor of the number of guest CPUs.
      parameters:
      - name: id
        type: integer
        description: >
          The ID of the **guest** NUMA node.
      value:
        type: string
        format: '\d+((-\d+)?(,\^?\d+(-\d+)?)?)*'
        description: >
          The guest CPUs, in the form of a CPU map, to allocate to the guest
          NUMA node identified by ``{id}``.

Regardless of the source of the extra spec validator, they will be used by the
API behind the :command:`openstack flavor set` command. A microversion will be
introduced for this command to avoid breaking existing tools that are
inadvertently setting the wrong values.

.. _stevedore: https://docs.openstack.org/stevedore/latest

Key validation
--------------

We also want to be able to catch invalid extra specs themselves. It will
resolve issues like the following in a generic manner::

    hw:cpu_pollllicy=dedicated

This involves maintaining a registry of valid extra specs. Not all extra specs
can be known ahead of time and for dynamic extra specs, such as those proposed
in `Support filtering by forbidden aggregate membership
<http://specs.openstack.org/openstack/nova-specs/specs/stein/approved/negative-aggregate-membership.html>`.
For these, we can rely on a custom namespace validator or YAML specification
provided by the operator. However, completing this registry both in-tree and
out-of-tree is expected to be a complex endeavour and for this reason we won't
enforce validation of keys as part of this spec.

Other changes
-------------

We also propose adding tooling to (a) render reStructuredText documentation
from the definitions and (b) convert the definitions into Glance metadata
definition files. Both of these tools will live within the nova tree, allowing
us to remain the single source of truth for these things.

Alternatives
------------

* We could ignore some of the above issues and try to solve others in a
  piecemeal fashion. This will likely be far more tedious and time consuming as
  modifications will be needed in far more places.

Data model impact
-----------------

None.

REST API impact
---------------

We will add a REST API microversion to the ``POST
flavors/{flavor_d}/os-extra_specs`` API to catch invalid flavor extra specs.

Security impact
---------------

None.

Notifications impact
--------------------

None.

Other end user impact
---------------------

End users will have better documentation for the available flavor extra specs
and image metadata properties.

Performance Impact
------------------

None.

Other deployer impact
---------------------

Operators will now need to add new flavor extra specs to the YAML schema file
or they will see errors when using the new API microversion.

Developer impact
----------------

Developers should now add new flavor extra specs to the
``nova.compute.extra_specs`` module to take advantage of the validation
available.

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
  None

Work Items
----------

1. Produce extra spec definitions for all in-tree flavor extra specs.

2. Add code to validate this against the image metadata properties and flavor
   extra specs on instance create, resize and rebuild operations.

3. Add a Sphinx extension to render this spec into documentation and another
   tool to convert the spec into Glance metadata definitions.

4. Add parser for YAML-formatted definitions and document how operators can and
   should use this.


Dependencies
============

None.


Testing
=======

Unit tests.


Documentation Impact
====================

There will be better docs, through the power of Sphinx.


References
==========

.. [1] https://docs.openstack.org/image-guide/image-metadata.html#metadata-definition-service


History
=======

.. list-table:: Revisions
   :header-rows: 1

   * - Release Name
     - Description
   * - Train
     - Introduced
