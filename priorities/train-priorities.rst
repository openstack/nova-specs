.. _train-priorities:
.. _train-themes:

==================
Train Cycle Themes
==================

These are cycle themes. That means we intend to put particular effort into
these initiatives. It does not mean we are committing to finishing any/all
individual items in particular. It also does not mean these are the only things
we will be concentrating on. Consider yourself disclaimed.

#. **Improve/expand Nova's scheduling efficiency and scalability for all
   deployments, with particular focus on large-scale deployments.** This means
   being able to ask Placement better questions so that more filtering is done
   in Placement to reduce the list of allocation candidates and minimize
   Nova-side filtering. Specifically we intend to target efforts such as:

   * NUMA structure modeling and affinity
   * Improved tracking of shared and dedicated logical processors
   * Reporting, tracking, and requesting additional resources on hosts
   * Supporting server group affinity and anti-affinity
   * Trait filters for driver capabilities, image types, and more
   * Forbidden trait and aggregate filters to isolate "special" hosts, avoid
     disabled nodes, etc.

   .. note:: Much of the above work has dependencies on efforts in Placement.
             The Placement team's cycle priorities are aligned accordingly.

#. **Enable requesting an instance with one or more accelerators either
   preprogrammed or dynamically programmed.** This encompasses FPGAs managed by
   Cyborg as well as VGPUs (of multiple types) managed by Nova.

   .. note:: This includes cross-project work with Cyborg. The Cyborg team's
             cycle priorities are aligned accordingly.

#. **We want our documentation to be valid, easily referenced and generally
   suitable for purpose.** We're building on a strong foundation. Three
   objectives:

   #. **Docs should be cleanly aligned to the directory structure.** This is so
      end users can go to '/user' and find the info they want without admin'y
      stuff thrown in. Ditto for admins, devs, etc.
   #. **The install guide should work.**
   #. **Docs in the user and admin guides should be topic-focused and
      self-contained.** Like we did with the `console docs`_, a user/admin
      should be able to search Google for e.g. "attaching a PCI device" and
      find the guide that details what it is, how to enable it and how to use
      it. See https://docs.djangoproject.com/en/2.2/topics/migrations/ for a
      non-OpenStack variant.

.. _`console docs`: https://docs.openstack.org/nova/latest/admin/remote-console-access.html#novnc-based-vnc-console
