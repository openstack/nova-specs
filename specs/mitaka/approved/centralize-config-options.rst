..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

=========================
Centralize Config Options
=========================

Include the URL of your launchpad blueprint:

https://blueprints.launchpad.net/nova/+spec/centralize-config-options

Nova has around 800 config options*. Those config options are the interface
to the cloud operators. Unfortunately they often lack a good documentation
which
* explains their impact,
* shows their interdependency to other config options and
* explains which of the Nova services they influence.
This cloud operator interface needs to be consolidated and one way of doing
this is, to move the config options from their declaration in multiple modules
to a few centrally managed modules. These centrally managed modules should
also provide the bigger picture of the configuration surface we provide. This
got already discussed on the ML [1].

\* see the "nova.flagmappings" file which get generated in the
"openstack-manuals" project for the "configuration reference" manual.

Problem description
===================

Same as above

Use Cases
----------

* As an end user I'm not affected by this change and won't notice a difference.
* As a developer I will find all config options in one place and will add
  further config options to that central place.
* As a cloud operator I will see more helpful descriptions on the config
  options. The default values, names, sections won't change in any way and
  my ``nova.conf`` files will work as before.

Proposed change
===============

The change consists of two views,

* a technical one, which describes how the refactoring is done in terms
  of code placement
* and a quality view, which describes the standard a good config option
  help text has to fulfill.

Technical View
--------------

There was a proof of concept in Gerrit which shows the intention [2]. The
steps are as followed:

#. There will be a new package called ``nova/conf``.

#. This package contains a module for each section in the ``nova.conf`` file.
   For example:

   * ``nova/conf/default.py``
   * ``nova/conf/ssl.py``
   * ``nova/conf/cells.py``
   * ``nova/conf/libvirt.py``
   * [...]

#. All ``CONF.import_opt(...)`` calls get moved to the new section
   modules from the previous step.

#. All ``CONF.register_opts(...)`` calls get moved to the module
   ``nova/conf/__init__.py``. This allows the usage of::

       import nova.conf

       CONF = nova.conf.CONF

       if CONF.<section>.<config-option>:
           # do something

   Which means that the normal functional code, which uses the config options
   doesn't need to get changed for this.

#. The ``opts.py`` modules which are necessary to build the configuration
   reference guide need to change their pointer to the new modules. For
   example the ``nova/virt/opts.py``::

       import nova.conf.default

       def list_opts():
           return [
               ('DEFAULT',
                itertools.chain(
                    nova.conf.default.imagecache_opts,


Quality View
------------

Operators will work with this interface, so the documentation has to be
precise and non-ambiguous. So let's have a view at some negative examples and
why I consider them not sufficient. After that, the changed positive example
should show which direction we should go. This section will close with a
generic template for config options which should be implemented during this
refactoring.

**Negative Examples:**

The following example is from the *serial console* feature::

    cfg.StrOpt('base_url',
           default='ws://127.0.0.1:6083/',
           help='Location of serial console proxy.'),

It lacks the description which services use this, how one can decide to
use another port and what the impact this has.

Another example from the *image cache* feature::

    cfg.IntOpt('image_cache_manager_interval',
               default=2400,
               help='Number of seconds to wait between runs of the '
                    'image cache manager. Set to -1 to disable. '
                    'Setting this to 0 will run at the default rate.'),

On the plus side, it shows the possible values and their impact, but does
not describe which service consumes this and if it has interdependencies
to other config options.

**Positive Example:**

Here is an example how this could look like for a config option of the
*serial console* feature::

    serial_opt_base_url = cfg.StrOpt('base_url',
                                     default='ws://127.0.0.1:6083/',
                                     help="""The token enriched URL which is
    returned to the end user to connect to the nova-serialproxy service.

    This URL is the handle an end user will get (enriched with a token at
    the end) to establish the connection to the console of a guest.

    Services which consume this:

    * ``nova-compute``

    Possible values:

    * A string which is a URL

    Interdependencies to other options:

    * The IP address must be identical to the address to which the
      ``nova-serialproxy`` service is listening (see option
      ``serialproxy_host`` in section ``[serial_console]``).
    * The port must be the same as in the option ``serialproxy_port``
      of section ``[serial_console]``.
    * If you choose to use a secured websocket connection, start this
      option with ``wss://`` instead of the unsecured ``ws://``.
      The options ``cert`` and ``key`` in the ``[DEFAULT]`` section
      have to be set for that.'"""),

    serial_console_group = cfg.OptGroup(name="serial_console",
                                        title="The serial console feature",
                                        help="""The serial console feature
    allows you to connect to a guest in case a graphical console like VNC or
    SPICE is not available.""")

    CONF.register_opt(serial_opt_base_url, group=serial_console_group)

Another example can be made for the *image cache* feature::

    cfg.IntOpt('image_cache_manager_interval',
               default=2400,
               min=-1,
               help="""Number of seconds to wait between runs of
    the image cache manager.

    The image cache manager is responsible for ensuring that local disk doesn't
    fill with backing images that aren't currently in use. It should be noted
    that if local disk is too full to start a new instance, and cleaning the
    image cache would free enough space to make the hypervisor node usable then
    the hypervisor node wont be usable until the next run of the image cache
    manager. In other words, the cache manager is not run more frequently as
    a hypervisor node becomes resource constrained.

    Services which consume this:

    * ``nova-compute``

    Possible values:

    * ``-1`` Disables the cleaning of the image cache.
    * ``0`` Runs the cleaning at the default rate.
    * Other values greater than ``0`` describes the number of seconds
      between two cleanups

    Interdependencies to other options:

    * None
    """),

**Generic Template**

Based on the positive example above, the generic template a config option
should fulfill to be descriptive to the operators would be::

    help="""#A short description what it does. If it is a unit (e.g. timeout)
    # describe the unit which is used (seconds, megabyte, mebibyte, ...)

    # A long description what the impact and scope is. The operators should
    # know the expected change in the behavior of Nova if they tweak this.

    Services which consume this:

    # A list of services which consume this option. Operators should not
    # read code to know which one of the services will change its behavior.
    # Nor should they set this in every ``nova.conf`` file to be sure.

    Possible values:

    # description of possible values. Especially if this is an option
    # with numeric values (int, float), describe the edge cases (like the
    # min value, max value, 0, -1).

    Interdependencies to other options:

    # Which other config options have to be considered when I change this
    # one? If it stand solely on its own, use "None"
    """),



Alternatives
------------

The ML discussion [2] concluded that the following ideas wouldn't work for us:

#. *Move all of the config options into one single ``flags.py`` module.*
   It was reasoned that this file would be vastly huge and that merge
   conflicts for the contributors would be unavoidable.

#. *Ship the config options in data files with the code rather than being*
   *inside the Python code itself.* It was reasoned that this could cause a
   missing update of the config options description if it was used in a
   different way than before.

#. *Don't use config options directly in the functional code. Make a*
   *dependency injection to the object which needs the configured value*
   *and depend only on that objects attributes.* Yes, this is the one with
   the most benefit in terms of testability, clean code, OOP practices and
   so on. The outcome of this blueprint is also to get a feeling how that
   approach could be done in the end. A first proof of concept [3] was a bit
   cumbersome.

Data model impact
-----------------

None

REST API impact
---------------

None

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

#. It could also be that we like to deprecate options because they don't get
   used anymore.

#. Otherwise the deployer should get more and more happy about helpful texts
   and descriptions.

Developer impact
----------------

#. Contributors which are actively working on config options could have merge
   conflicts and need to rebase.
#. New config options should directly be added to the new central place at
   ``nova/conf/<section>.py``.

Implementation
==============

Assignee(s)
-----------

Primary assignee:
  Markus Zoeller (markus_z)
  https://launchpad.net/~mzoeller

Other contributors:
  None (but highly welcome)

Work Items
----------

#. create folder ``nova/conf`` with modules for each ``nova.conf`` section
#. move options from a functional module to the section module from above
#. enhance the help texts from config options and option groups.


Dependencies
============

#. Depending on the outcome of the discussion of [4] which proposes to enrich
   the config option object by interdependencies, we could use that. But this
   blueprint doesn't have a hard dependency on that.
#. Depending on the outcome of the discussion of [5] which proposes to enrich
   the config option object by allowing to format the help text with a markup
   language, we could use that. But this blueprint doesn't have a hard
   dependency on that.

Testing
=======

The ``nova.conf`` sample gets generated as part of the ``docs`` build.
If this fails we know that something went wrong.


Documentation Impact
====================

None


References
==========

[1] MailingList "openstack-dev"; July 2015; "Streamlining of config options
    in nova":
    http://lists.openstack.org/pipermail/openstack-dev/2015-July/070306.html
[2] Gerrit; PoC; "DO NOT MERGE: Example of config options reshuffle":
    https://review.openstack.org/#/c/214581
[3] Gerrit; PoC; "DO NOT MERGE: replace global CONF access by object":
    https://review.openstack.org/#/c/218319
[4] Launchpad; oslo.config; blueprint "option-interdependencies"
    https://blueprints.launchpad.net/oslo.config/+spec/option-interdependencies
[5] Launchpad; oslo.config; blueprint "help-text-markup"
    https://blueprints.launchpad.net/oslo.config/+spec/help-text-markup

History
=======

.. list-table:: Revisions
   :header-rows: 1

   * - Release Name
     - Description
   * - Mitaka
     - Introduced
