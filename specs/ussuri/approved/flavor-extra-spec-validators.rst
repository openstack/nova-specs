..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

===========================
Flavor Extra Spec Validator
===========================

https://blueprints.launchpad.net/nova/+spec/flavor-extra-spec-validators

Introduce a mechanism to describe and validate flavor extra specs.

Problem description
===================

Flavor extra specs are one of the Wild West aspects of nova. There are a number
of issues we'd like to address:

- Lack of documentation for many flavor extra specs [1]_. While Glance has
  metadefs [2]_, those are generally out-of-date, incomplete, and not
  consumable from nova and our user-facing documentation.

- No warnings or errors if there is a typo in your extra spec, resulting in
  different behavior to that expected.

- No defined way to do things like deprecate a flavor extra spec, resulting in
  continued reinvention of the wheel.

Use Cases
---------

* As a deployer, I'd like to know what flavor extra specs and image metadata
  properties are available and why I'd want to use them.

* As a deployer, I'd like nova to tell me when I've used a flavor extra spec
  that doesn't exist or has a typo in it.

* As a developer, I'd like an easy way to deprecate flavor extra specs, which
  is something that will only become more common if we do things like model
  NUMA in placement.

* As a documentation writer, I'd like to be able to cross-reference the various
  flavor extra specs and image metadata properties available.

Proposed change
===============

A flavor extra spec is a key-value pair. For example::

    hw:cpu_policy=dedicated

Different solutions are needed to validate the *value* part of an extra spec
compared to the *key* part. This spec aims to tackle validation of both,
however, the following are considered out-of-scope for this change:

- Enforcement of extra spec dependencies. For example, if extra spec A requires
  extra spec B be configured first. We will document the dependency but it
  won't be enforced.

  .. note:: In most cases this is already handled by virt drivers.

- Enforcement of virt driver dependencies. Unfortunately, while flavor extra
  specs should be generic, this isn't always the case. As above, we will
  document this dependency but it won't be enforced.

This change builds upon `Flavor extra spec image metadata validation
<http://specs.openstack.org/openstack/nova-specs/specs/stein/implemented/flavor-extra-spec-image-property-validation.html>`__,
which covers some of these issues for us.

Value validation
----------------

Value validation is the easier of the two issues to tackle. It will resolve
issues like the following in a generic manner::

    hw:cpu_policy=deddddicated

For a generic extra spec, a definition of a validator will need to contain the
following:

- Name or *key* of the extra spec, e.g. ``hw:cpu_policy`` for the above
  example. This must be patternable to handle e.g. ``hw:numa_cpus.{id}``.

- Description of the extra spec.

- Support status of the extra spec.

- Valid values; whether it's an integer, a boolean, a string matching a given
  regex or pattern, an enum, or something else entirely

- Virt driver dependencies; this is only for documentation purposes and will
  not be enforced

- Extra spec dependencies; this is only for documentation purposes and will not
  be enforced

For any extra specs defined in in-tree code, we propose also maintaining the
definitions in-tree. To do this, we propose adding a new module,
``nova.api.validation.extra_specs``, which will contain definitions for *flavor
validators*. These will be defined using Python objects.

For example:

.. code-block:: python

    numa_node = base.ExtraSpecValidator(
        name='hw:numa_nodes',
        description=(
            'The number of virtual NUMA nodes to allocate to configure the '
            'guest with. Each virtual NUMA node will be mapped to a unique '
            'host NUMA node. Only supported by the libvirt virt driver.'
        ),
        value={
            'type': int,
            'description': 'The number of virtual NUMA nodes to allocate',
            'min': 1,
        },
    )

    numa_cpu = base.ExtraSpecValidator(
        name='hw:numa_cpu.{id}',
        description=(
            'A mapping of **guest** CPUs to the **guest** NUMA node '
            'identified by ``{id}``. This can be used to provide asymmetric '
            'CPU-NUMA allocation and is necessary where the number of guest '
            'NUMA nodes is not a factor of the number of guest CPUs.'
        ),
        parameters=[
            {
                'name': 'id',
                'type': int,
                'description': 'The ID of the **guest** NUMA node.',
            },
        ],
        value={
            'type': str,
            'description': (
                'The guest CPUs, in the form of a CPU map, to allocate to the '
                'guest NUMA node identified by ``{id}``.'
            ),
            'pattern': r'\^?\d+((-\d+)?(,\^?\d+(-\d+)?)?)*',
        },
    )

In addition to the extra specs defined in-tree, it is also possible for
operators to define their own extra specs that would be used by e.g. custom
scheduler filters. For these, we propose providing an entry point through which
operators can define their own custom definitions. This entry point should
point to a list of extra spec validators. These will have lower precedence than
in-tree definitions. This is not expected to be a large burden since operators
already need to provide a package for the custom scheduler filters and
documentation will be provided to help users add these.

For example:

.. code-block:: ini

    nova.extra_spec_validators =
        custom_scheduler = custom.scheduler.extra_spec_validators:VALIDATORS

.. code-block:: python

    VALIDATORS = [
        base.ExtraSpecValidator(
            name='foo:bar',
            description='A custom, out-of-tree validator'
            value={
                'type:' bool,
                'description' 'Whether to allow the instance to do something',
            }
        ),
    ]

Regardless of the source of the extra spec validator, they will be used by the
API behind the :command:`openstack flavor set` command. A microversion will be
introduced for this API to avoid breaking existing tools that are inadvertently
setting the wrong values.

Key validation
--------------

We also want to be able to catch invalid extra specs themselves. It will
resolve issues like the following in a generic manner::

    hw:cpu_pollllicy=dedicated

This involves maintaining a registry of **all** valid extra specs. Given that
we're using a regex to define extra spec names and provide custom extra spec
validators via the entry point, we expect to have enough power to achieve this.
However, there may be a scenarios where an operator wishes to disable or bypass
this validation. To this end, we will add a new ``validation`` query parameter
to the ``flavors/{flavor_id}/os-extra_specs`` API. This will accept three
possible values:

``strict`` (default)
    Requests for extra specs with invalid values or extra specs that we do not
    have a validator for will be rejected with a HTTP 400 response.

``permissive``
    Requests for extra specs with invalid values will be rejected with a HTTP
    400 response. Requests for unregistered extra specs will be logged but
    permitted.

``off``
    Validation is disabled. No logging will occur.

All other values will be rejected.

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

* We could introduce a configuration option to toggle strict API validation
  instead of or in addition to the API microversion. This introduces a new
  example of config-driven API behavior, which is something we're trying to
  remove from nova. It is also unnecessary since users can use older API
  microversions if necessary.

* We could initially log warnings for invalid keys and introduce the API change
  in a later release. This is unnecessary because the use of microversions
  and/or the ``validation`` query parameter allows users to continue using the
  older behavior when absolutely necessary.

* We could introduce a new API microversion each time a new extra spec is
  introduced. This would be extremely tedious, would only be possible for
  in-tree extra specs, and is on the whole rather unnecessary.

* We could not add the ``validate`` query parameter and instead insist that all
  extra specs be registered. However, this validation is intended to help
  operators, not hurt them, and there are reasons people might want to bypass
  this.

* We could use a YAML file to describe out-of-tree extra specs rather than
  custom Python objects. However, this is prone to inadvertent tampering and
  forces people to learn multiple ways of configuring things.

Data model impact
-----------------

None.

REST API impact
---------------

We will add a REST API microversion to the ``POST
flavors/{flavor_id}/os-extra_specs`` API to return HTTP 400 invalid flavor
extra specs. We will also add support for a ``validation`` query parameter to
partially or fully disable this behavior, if necessary.

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

Operators will now need to describe any custom flavor extra specs used in their
deployment using custom validators or will they will see errors when using the
new API microversion without the ``validation`` parameter.

Developer impact
----------------

Developers should now add new flavor extra specs to the
``nova.api.validation.extra_specs`` module to take advantage of the validation
available.

Upgrade impact
--------------

Operators with out-of-tree scheduler filters or virt drivers may need to add
extra spec validators to their package.


Implementation
==============

Assignee(s)
-----------

Primary assignee:
  stephenfinucane

Other contributors:
  None

Feature Liaison
---------------

stephenfinucane

Work Items
----------

1. Produce extra spec definitions for all in-tree flavor extra specs.

2. Add entry point-based loading mechanism for custom extra specs and document
   how operators can and should use this.

3. Add a new API microversion and code to validate user-provided flavor extra
   specs and these definitions.

4. Add a Sphinx extension to render this spec into documentation and another
   tool to convert the spec into Glance metadata definitions.

5. Add a tool to generate glance-metadef compatible JSON files that can be
   consumed by the glance metadata definitions catalog API.


Dependencies
============

None.


Testing
=======

Unit tests.


Documentation Impact
====================

There will be better docs, through the power of Sphinx. We will need to
document how operators can develop validators for their custom extra specs.


References
==========

.. [1] https://docs.openstack.org/image-guide/image-metadata.html#metadata-definition-service
.. [2] https://github.com/openstack/glance/blob/18.0.0/etc/metadefs/compute-libvirt.json


History
=======

.. list-table:: Revisions
   :header-rows: 1

   * - Release Name
     - Description
   * - Train
     - Introduced
   * - Ussuri
     - Re-proposed with a simpler name and signficant modifications
