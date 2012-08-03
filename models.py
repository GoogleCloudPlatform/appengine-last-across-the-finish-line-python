import json

from google.appengine.api import channel
from google.appengine.ext.deferred import defer
from google.appengine.ext import ndb


MAX_KEYS = 100


def AlwaysComplete(key, method, *args, **kwargs):
  task = key.get()
  try:
    method(*args, **kwargs)
  except:
    # TODO: Consider failing differently.
    pass
  finally:
    # No need to be transactional since AlwaysComplete is not a transaction
    defer(task.Complete)


class BatchTask(ndb.Model):
  completed = ndb.BooleanProperty(default=False)

  @ndb.transactional
  def Populate(self, method, *args, **kwargs):
    self.put()

    kwargs['_transactional'] = True
    defer(AlwaysComplete, self.key, method, *args, **kwargs)

  @ndb.transactional
  def Complete(self):
    self.completed = True
    self.put()

    batcher_parent = self.key.parent().get()
    defer(batcher_parent.CheckComplete, _transactional=True)


class TaskBatcher(ndb.Model):
  all_tasks_loaded = ndb.BooleanProperty(default=False)

  def CheckComplete(self):
    # Does not need to be transactional since it doesn't change data
    session_id = self.key.id()
    if self.all_tasks_loaded:
      incomplete = BatchTask.query(BatchTask.completed == False,
                                   ancestor=self.key).fetch(1)
      if len(incomplete) == 0:
        channel.send_message(session_id, json.dumps({'status': 'complete'}))
        # No need to be transactional since CheckComplete is not a transaction
        defer(self.CleanUp)
        return

    channel.send_message(session_id, json.dumps({'status': 'incomplete'}))

  @ndb.transactional
  def CleanUp(self):
    children = BatchTask.query(ancestor=self.key).fetch(
        MAX_KEYS, keys_only=True)

    if children:
      ndb.delete_multi(children)
      defer(self.CleanUp, _transactional=True)
    else:
      self.key.delete()


def _PopulateBatch(session_id, work):
  batcher_key = ndb.Key(TaskBatcher, session_id)
  batcher = TaskBatcher(key=batcher_key)
  batcher.put()

  for method, args, kwargs in work:
    task = BatchTask(parent=batcher_key)
    task.Populate(method, *args, **kwargs)

  batcher.all_tasks_loaded = True
  batcher.put()
  # TODO: Call check complete here


def PopulateBatch(session_id, work):
  defer(_PopulateBatch, session_id, work)
