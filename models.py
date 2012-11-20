#!/usr/bin/python

# Copyright (C) 2010-2012 Google Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.


"""Models module for gae-last-across-the-finish-line.

Defines a set of methods and datastore models that allow an arbitrary batch of
work to be performed and tracked asynchronously. The status of the batch is
checked periodically and sent back to the client until the batch has completed.
"""


__author__ = 'dhermes@google.com (Daniel Hermes)'


# General libraries
import json

# App engine specific libraries
from google.appengine.api import channel
from google.appengine.ext.deferred import defer
from google.appengine.ext import ndb


def AlwaysComplete(task, method, *args, **kwargs):
  """Attempt to run a method and complete a task upon completion or failure.

  Runs the method with the provided arguments or catches any errors if the
  method fails. Always cleans up by deferring the Complete method on the task
  object retrieved from the key. Defers it rather than running here in
  case Complete is a transactional method and if it failed it would cause the
  method to be retried in a task.

  Args:
    task: An NDB object representing a task with a Complete method.
    method: A method to be called in this piece of work.
    args: The positional arguments to be passed to method.
    kwargs: The keyword arguments to be passed to method.
  """
  try:
    method(*args, **kwargs)  # pylint:disable-msg=W0142
  except:  # pylint:disable-msg=W0702
    # TODO: Consider failing differently.
    pass
  finally:
    # No need to be transactional since AlwaysComplete is not a transaction
    defer(task.Complete)


class BatchTask(ndb.Model):
  """Model to represent a task and the status of the task."""
  # Very important that the default value True of `indexed` is used here
  # since we need to query on BatchTask.completed
  completed = ndb.BooleanProperty(default=False)   # pylint:disable-msg=E1101

  @ndb.transactional
  def Populate(self, method, *args, **kwargs):
    """Puts a task in the datastore and spawns a task with the work provided.

    Adds _transactional as a keyword argument to be passed in to defer, which
    will be stripped out and cause the task to be added transactionally, meaning
    it will only be enqueued if the put succeeds (and only after the put
    succeeds, which is important).

    Args:
      method: A method to be deferred via AlwaysComplete.
      args: The positional arguments to be passed to method.
      kwargs: The keyword arguments to be passed to method.
    """
    self.put()

    kwargs['_transactional'] = True
    defer(AlwaysComplete, self, method, *args, **kwargs)

  @ndb.transactional
  def Complete(self):
    """Marks task as completed and notifies parent to check all tasks are done.

    Retrieves the parent of the key and transactionally defers the CheckComplete
    method of the parent to check if all tasks have completed.

    Adds _transactional as a keyword argument to be passed in to defer, which
    will be stripped out and cause the task to be added transactionally, meaning
    it will only be enqueued if the put succeeds (and only after the put
    succeeds, which is important).
    """
    self.completed = True
    self.put()

    batcher_parent = self.key.parent().get()
    defer(batcher_parent.CheckComplete, _transactional=True)


class TaskBatcher(ndb.Model):
  """Model to represent a batch of tasks and the loading status of the batch.

  Expects the key to be a session ID for communicating with a client.
  """
  # pylint:disable-msg=E1101
  all_tasks_loaded = ndb.BooleanProperty(default=False, indexed=False)
  # pylint:enable-msg=E1101

  def CheckComplete(self):
    """Checks if all tasks with this object as parent have complete.

    If the tasks have not finished loading, will not do anything. Otherwise,
    attempts to retrieve a single BatchTask that has not completed. Since no
    puts or deletes are executed, and this is an ancestor query, it is
    guaranteed to be consistent with the datastore.

    If no such BatchTask exists, then a message containing status complete
    is sent to the client and the CleanUp method on the object is called.
    """
    # Does not need to be transactional since it doesn't change data
    session_id = self.key.id()
    if self.all_tasks_loaded:
      incomplete = BatchTask.query(BatchTask.completed == False,
                                   ancestor=self.key).fetch(1)
      if len(incomplete) == 0:
        channel.send_message(session_id, json.dumps({'status': 'complete'}))
        self.CleanUp()
        return

    channel.send_message(session_id, json.dumps({'status': 'incomplete'}))

  @ndb.transactional
  def Ready(self):
    """Called to signal batch is fully loaded and check if batch finished.

    Sets all_tasks_loaded to True transactionally, but also checks if all the
    tasks have completed by the time the queue is filled.
    """
    self.all_tasks_loaded = True
    self.put()

    self.CheckComplete()

  @ndb.transactional
  def CleanUp(self):
    """Cleans up task batcher and all children.

    Attempts to iterate over child tasks by key only and delete them all, then
    delete the parent. Since the only callers of this method do so in a deferred
    task, if this times out, the task will retry and have many fewer entries to
    delete.
    """
    children = BatchTask.query(ancestor=self.key).iter(keys_only=True)
    ndb.delete_multi(children)
    self.key.delete()


def _PopulateBatch(session_id, work):
  """Populates a TaskBatcher with a set of work tasks.

  Args:
    session_id: An ID to be used as the key and for sending messages
        to the client via channel.
    work: A list of 3-tuples containing the work to be done in worker
        tasks. The 3-tuple contains a method, the positional arguments and
        the keyword arguments to be passed to that method.
  """
  batcher_key = ndb.Key(TaskBatcher, session_id)
  batcher = TaskBatcher(key=batcher_key)
  ndb.transaction(batcher.put)

  for method, args, kwargs in work:
    task = BatchTask(parent=batcher_key)
    task.Populate(method, *args, **kwargs)  # pylint:disable-msg=W0142

  batcher.Ready()


def PopulateBatch(session_id, work):
  """Defers a task to populate a TaskBatcher with a set of work tasks.

  This serves to allow _PopulateBatch to be deferred by default without forcing
  users to worry about the deferred library.

  Args:
    session_id: An ID to be used as the key and for sending messages
        to the client via channel.
    work: A list of 3-tuples containing the work to be done in worker
        tasks. The 3-tuple contains a method, the positional arguments and
        the keyword arguments to be passed to that method.
  """
  defer(_PopulateBatch, session_id, work)
