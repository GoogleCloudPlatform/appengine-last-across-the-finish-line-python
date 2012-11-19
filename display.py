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


"""Display and display workers module for gae-last-across-the-finish-line."""


__author__ = 'dhermes@google.com (Daniel Hermes)'


# General libraries
import json
import random

# App engine specific libraries
from google.appengine.api import channel
from jinja2 import Template


HEX_DIGITS = '0123456789ABCDEF'
TABLE_TEMPLATE = Template("""\
<table id="{{ table_id }}">
  <tbody>
    {% for row in rows %}
    <tr>
      {% for column in columns %}
      <td id="square{{ columns|length * row + column }}" />
      {% endfor %}
    </tr>
    {% endfor %}
  </tbody>
</table>""")


def GenerateTable(table_id, num_rows, num_columns):
  """Generates an HTML table with a fixed number of rows and columns.

  Args:
    table_id: An HTML ID for the table created
    num_rows: The number of rows in the table
    num_columns: The number of columns in the table
  """
  return TABLE_TEMPLATE.render(table_id=table_id,
                               rows=range(num_rows),
                               columns=range(num_columns))


def RandomRowColumnOrdering(rows, columns):
  """Generates a random ordering of all row, column pairs.

  Uses random.shuffle to shuffle the integers between 0 and
  rows*columns - 1 (inclusive) and then maps each of these
  integers to a corresponding row, column pair.

  Args:
    rows: The number of rows in the table
    columns: The number of columns in the table
  """
  square_indices = range(rows*columns)
  random.shuffle(square_indices)
  return [divmod(index, columns) for index in square_indices]


def RandHexColor(length=6):
  """Generates a random color using hexadecimal digits.

  Args:
    length: The number of hex digits in the color. Defaults to 6.
  """
  result = [random.choice(HEX_DIGITS) for _ in range(length)]
  return '#' + ''.join(result)


def SendColor(row, column, session_id):
  """Generates and sends a color to client over the channel for the session ID.

  Args:
    row: The row in the table on the client receiving the color
    column: The column in the table on the client receiving the color
    session_id: The session ID of the client.
  """
  color = RandHexColor(length=6)

  color_dict = {
      'row': row,
      'column': column,
      'color': color
  }
  channel.send_message(session_id, json.dumps(color_dict))
