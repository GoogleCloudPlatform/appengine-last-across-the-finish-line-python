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


"""Main handlers module for gae-last-across-the-finish-line."""


__author__ = 'dhermes@google.com (Daniel Hermes)'


# General libraries
import json

# App engine specific libraries
from google.appengine.api import channel
from google.appengine.api import users
from google.appengine.ext.webapp.util import login_required
import webapp2
from webapp2_extras import jinja2

# App specific libraries
from display import GenerateTable
from display import RandomRowColumnOrdering
from display import SendColor
from models import PopulateBatch


COLUMNS = 8
ROWS = 8


class BeginWork(webapp2.RequestHandler):
  """Handler to initiate a batch of work."""

  def post(self):  # pylint:disable-msg=C0103
    """A handler which will spawn work for random row, column pairs.

    Generates all unique row, column pairs and then populates a batch of
    workers, each with SendColor. If any type of error is encountered, returns
    a JSON encoded failure message, otherwise returns a success message.

    Uses the user ID of the logged in user as a proxy for session ID.
    """
    try:
      user_id = users.get_current_user().user_id()

      work = []
      for row, column in RandomRowColumnOrdering(ROWS, COLUMNS):
        args = (row, column, user_id)
        work.append((SendColor, args, {}))  # No keyword args

      PopulateBatch(user_id, work)
      self.response.out.write(json.dumps({'populate_init_succeeded': True}))
    except:  # pylint:disable-msg=W0702
      self.response.out.write(json.dumps({'populate_init_succeeded': False}))


class MainPage(webapp2.RequestHandler):
  """Handler to serve main page with static content."""

  def RenderResponse(self, template, **context):
    """Use Jinja2 instance to render template and write to output.

    Args:
      template: filename (relative to $PROJECT/templates) that we are rendering
      context: keyword arguments corresponding to variables in template
    """
    jinja2_renderer = jinja2.get_jinja2(app=self.app)
    rendered_value = jinja2_renderer.render_template(template, **context)
    self.response.write(rendered_value)

  @login_required
  def get(self):  # pylint:disable-msg=C0103
    """A handler which will create a channel and serve main page.

    Uses the user ID to create a channel for message passing and creates
    a ROWS x COLUMNS size table. Passes the token for the channel into the
    template so the channel can be opened by the client.
    """
    user_id = users.get_current_user().user_id()
    token = channel.create_channel(user_id)
    table = GenerateTable('pixels', ROWS, COLUMNS)
    self.RenderResponse('main.html', token=token, table=table)


# pylint:disable-msg=C0103
app = webapp2.WSGIApplication([('/begin-work', BeginWork),
                               ('/', MainPage)],
                              debug=True)
