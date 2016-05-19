..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

=============================
Add support for Glance v2 API
=============================

https://blueprints.launchpad.net/nova/+spec/use-glance-v2-api

This spec proposes to add the ability for Nova to use the Glance v2 API, and
starts the deprecation period for the support of the Glance v1 API.

While parts of Nova already use the Glance v2 API, this is about making the
dependency on Glance v1 API optional, so it can be removed completely in a
future release.

Problem description
===================

Glance relegated v1 from CURRENT to SUPPORTED status in Kilo. Currently Nova
requires access to the Glance v1 API. Glance would like to deprecate that API
in Newton cycle, so to help that effort Nova should stop using Glance v1 API.

v1 is considered unsuitable for exposing to public for a number of reasons,
but to name a few:

 * image schema isn't exposed,

 * list all images call shows details including all properties on image that
   may result into slow queries or even worse,

 * operators don't have a way to specify certain important properties
   (via schema again) as a part of their deployment,

 * tags API isn't exposed as recommended by the API_WG and therefore ,

 * no possibility to sort by multiple fields,

 * and a lot more!

To allow for a smooth upgrade, we need to ensure Newton supports using both
Glance v1 and Glance v2, to give deployers time to ensure they have Glance v2
deployed in a way that can be used by Nova.

While some areas of Nova already make use of Glance v2, there are many areas
of Nova that still have a hard dependency on Glance v1. The key areas that
still use Glance v1 include:

 * Nova's Image API, that is effectively just a proxy of Glance's v1 API,

 * Virt driver specific download of images and upload of images,

 * CRUD operations on image metadata,

 * Creating and deleting snapshots in common code.

Before we can stop Nova requiring Glance v1 and fully deprecate the requirement
for Glance v1, we need to remove all the above uses of Glance v1.

.. note::

  Nova's external API must keep compatibility regardless of whether it is using
  Glance v1 or Glance v2, to allow for a smooth upgrade between releases.

Use Cases
---------

Currently, Nova deployers are forced to install both Glance v1 and Glance
v2. This is because Nova currently requires Glance v1, but for the reason of
its obvious disadvantages only Glance v2 is considered safe to be exposed
publicly to End Users.

It is assumed that Nova's lack of support for Glance v2 is causing confusion
that is holding people back from deploying Glance v2. This in turn is causing
some problems for the DefCore effort.

Proposed change
===============

Support for Glance v2 will be done within the Nova code.

.. note::

   Because Glance v1 is moving to DEPRECATED and will be removed, the
   code in Nova should be written to optimize the ease of deleting
   Glance v1 code in the future. That means making v1 / v2 API
   decision very early in the code flow, and *not* combining v1 / v2
   handling into common methods.

Constraints
-----------

The Nova Images API still needs to work (within reason). It should be
moved to be backed by Glance v2. The case sensitivity issue regarding
metadata is a known issue once the proxy starts using Glance V2 APIs
in the backend.

A Nova installation should always work on only one version of the
Glance API in production. Flipping back and forth deep in the code
adds a lot of complexity.

Xen virt driver requires a helper in dom0 that runs python 2.4.

Detailed Changes
----------------
Introduce a CONF item use_glance_v1=True under the [glance] section.
This will remove the need for auto discovery of Glance API version
The ``api_servers`` config specifies versionless API servers today,
so is consistent with that. The conf parameter will be deprecated
once we have a CI job that disables glance v1 API and enables
glance V2 APIs by setting the flag to False and eventually passes
all the tests.

If there are differences in the code between glance v1 / v2 methods
and classes should be built independently for the glance v1 vs. v2
interaction. This allows us to delete the v1 code in the future
easily.

Alternatives
------------

None.

Data model impact
-----------------

None.

REST API impact
---------------

The Nova Images API will have incompatibility when it comes to case
sensitivity of metadata. This is unavoidable.

Security impact
---------------

None.

Notifications impact
--------------------

None.

Other end user impact
---------------------

End user must remember about several incompatibilities between v1 and v2 apis:

  * Image properties in v1 are passed with http headers which makes them case
    insensitive. In v2 image info is passed as json document and 'MyProperty'
    and 'myproperty' are two different properties.

  * in v1 user can create custom properties like 'owner' or 'created_at' and
    they are stored in special dictionary 'properties'. v2 images have flat
    structure, which means that all custom properties are located on the same
    level as base properties. It leads to the fact if v1 image has a custom
    property that has a name coincided with the name of base property, then
    this property will be ignored in v2. Example output differences:

    * v1 image output:

      .. code-block:: javascript

          {
            "name": "image_name",
            "owner": "image_owner"
            "properties":
               {
                  "name": "just a custom property",
                  "owner": "another custom property",
                  "licence": "gpl v2",
               }
          }

    * v2 image output:

      .. code-block:: javascript

          {
            "name": "image_name",
            "owner": "image_owner"
            "licence": "gpl v2",
          }

  The Nova proxy should have code to ensure that the V1 output format is
  preserved even while working with Glance V2 APIs in the backend.

  * v2 forbids for user to specify some image properties like ``id`` or
    ``size``.


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

  mfedosin

Other contributors:

  flaper87
  sudipto
  nikhil-komawar

Work Items
----------

* Introduce a top level boolean flag to segregate the Glance V1 and V2 paths.
  The boolean use_glance_v1 is set to True by default to ensure that Glance
  V1 APIs are used by default. Once the boolean is flipped to False, the Nova
  proxy shall start using the Glance V2 APIs.

* Introduce GlanceImageServiceV2 as a similar class to GlanceImageService
  There is expected code duplication across these two above classes however,
  once the V1 APIs are deprecated, all the code related to GlanceImageService
  should be deleted.

* Do the following code re-factor to ensure that the output of CRUD operations
  on the Glance V2 APIs remains consistent with the existing Nova proxy output
  that uses Glance V1 by default:

  * Add another 'schema-based' handler, that transforms glance v2 image
    output to format adopted in nova.image.

  * Add additional handlers that transforms v1 image filters in v2.
    Related feature request: https://bugs.launchpad.net/nova/+bug/1201266

  * Add transformation to 2-stepped image creation
    (creation of the record in db + file uploading).

  * Add special handler for creating active images with size '0' without image
    data.

  * Add the ability to set custom location for an image. It's required for
    libvirt driver, for Ceph backends.

    .. note::
      ``show_multiple_locations`` option must be enabled in glance config
      in order for this to work. In v1 setting custom locations is enabled by
      default for for v2 this option must be activated explicitly. Related
      policies must be modified to allow this.

  * Add special handler to remove custom properties from the image:
    ``purge_props`` flag in v1 vs. ``props_to_remove`` list in v2.

* Adapt Xen virt driver to support v2 api.

* Ensure the rest of the code base can use the existing image code to talk to
  either Glance v1 or Glance v2, defaulting to Glance V1 and subsequently
  switching to Glance V2 as mentioned above.

* Ensure all the virt drivers either support Glance v2 or fallback to v1.

* Add a deprecation warning in the logs if users run with Glance v1.

Dependencies
============

Bug https://bugs.launchpad.net/nova/+bug/1539698 must be fixed before code is
merged.

Testing
=======

The gate jobs today enable glance v1 and v2. The CONF.glance.use_glance_v1
option defaults to True so patches will test against v1. Then we'll add a job
that disables glance v1 and enables only glance v2, and configures nova
to set CONF.glance.use_glance_v1=False and we'll run that job against the
top-level change in the glance v2 integration series.

At that point we deprecate the use_glance_v1 option once we know it's passing
tests with the v2 stack only.

Documentation Impact
====================

* Glance API version configuration option needs to be documented
* Release Notes should note the partial deprecation of Glance v1 support
* Release Note should warn about any virt drivers that are unable to run with
  Glance v2.
* Docs should be updated to highlight the case sensitivity problems as noted
  earlier in the spec.

References
==========

None.

History
=======

.. list-table:: Revisions
   :header-rows: 1

   * - Release Name
     - Description
   * - Liberty
     - Introduced
   * - Mitaka
     - Partial implemented
   * - Newton
     - Re-proposed
