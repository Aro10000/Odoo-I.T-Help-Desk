.. _stage_status:

Stage and Status
================

.. versionchanged:: 8.0 saas-2 state/stage cleaning

Stage
+++++

This revision removed the concept of state on tec.task objects. The ``state``
field has been totally removed and replaced by stages, using ``stage_id``. The
following models are impacted:

 - ``tec.task`` now use only stages. However a convention still exists about
   'New' stage. A task is consdered as ``new`` when it has the following
   properties:

   - ``stage_id and stage_id.sequence = 1``

 - ``tec.task.type`` do not have any ``state`` field anymore.
 - ``tec.task.report`` do not have any ``state`` field anymore.

By default a newly created task is in a new stage. It means that it will
fetch the stage having ``sequence = 1``. Stage mangement is done using the
kanban view or the clikable statusbar. It is not done using buttons anymore.

Stage analysis
++++++++++++++

Stage analysis can be performed using the newly introduced ``date_last_stage_update``
datetime field. This field is updated everytime ``stage_id`` is updated.

``tec.task.report`` model also uses the ``date_last_stage_update`` field.
This allows to group and analyse the time spend in the various stages.

Open / Assignment date
+++++++++++++++++++++++

The ``date_open`` field meaning has been updated. It is now set when the ``user_id``
(responsible) is set. It is therefore the assignment date.

Subtypes
++++++++

The following subtypes are triggered on ``tec.task``:

 - ``mt_task_new``: new tasks. Condition: ``obj.stage_id and obj.stage_id.sequence == 1``
 - ``mt_task_stage``: stage changed. Condition: ``obj.stage_id and obj.stage_id.sequence != 1``
 - ``mt_task_assigned``: user assigned. condition: ``obj.user_id and obj.user_id.id``
 - ``mt_task_blocked``: kanban state blocked. Condition: ``obj.kanban_state == 'blocked'``


Those subtypes are also available on the ``tec.tec`` model and are used
for the auto subscription.
