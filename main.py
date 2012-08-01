import json
import random

from google.appengine.api import channel
from google.appengine.api import users
from google.appengine.ext.webapp.util import login_required
import webapp2
from webapp2_extras import jinja2

from display import GenerateTable
from display import SendColor
from models import PopulateBatch


COLUMNS = 8
ROWS = 8
SQUARES_TO_COLOR = COLUMNS*ROWS


class BeginWork(webapp2.RequestHandler):

  @login_required
  def get(self):
    try:
      user_id = users.get_current_user().user_id()
      tuples_encountered = []
      work = []
      for _ in range(SQUARES_TO_COLOR):
        row = random.randrange(ROWS)
        column = random.randrange(COLUMNS)
        while (row, column) in tuples_encountered:
          row = random.randrange(ROWS)
          column = random.randrange(COLUMNS)
        tuples_encountered.append((row, column))

        args = (row, column, user_id)
        kwargs = {}

        work.append((SendColor, args, kwargs))

      PopulateBatch(user_id, work)
      self.response.out.write(json.dumps({'populate_init_succeeded': True}))
    except:
      self.response.out.write(json.dumps({'populate_init_succeeded': False}))


class MainPage(webapp2.RequestHandler):

  @webapp2.cached_property
  def Jinja2(self):
    return jinja2.get_jinja2(app=self.app)

  def RenderResponse(self, template, **context):
    rendered_value = self.Jinja2.render_template(template, **context)
    self.response.write(rendered_value)

  @login_required
  def get(self):
    user_id = users.get_current_user().user_id()
    token = channel.create_channel(user_id)
    table = GenerateTable('pixels', rows=8, columns=8)
    self.RenderResponse('main.html', token=token, table=table)


app = webapp2.WSGIApplication([('/begin-work', BeginWork),
                               ('/.*', MainPage)],
                              debug=True)
