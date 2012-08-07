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


CHOICES = '0123456789ABCDEF'


def GenerateTable(table_id, rows, columns):
  """Generates an HTML table with a fixed number of rows and columns.

  Args:
    table_id: An HTML ID for the table created
    rows: The number of rows in the table
    columns: The number of columns in the table
  """
  table_elts = ['<table id="{}">'.format(table_id), '<tbody>']
  for row in range(rows):
    row_add = ['<tr>']
    for column in range(columns):
      index = columns*row + column
      row_add.append('<td id="square{}" />'.format(index))
    row_add.append('</tr>')
    table_elts.extend(row_add)
  table_elts.extend(['</tbody>', '</table>'])
  return '\n'.join(table_elts)


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

  result = []
  for index in square_indices:
    row = index / columns  # Integer division intended
    column = index % columns
    result.append((row, column))
  return result


def RandHexColor(length=6):
  """Generates a random color using hexadecimal digits.

  Args:
    length: The number of hex digits in the color. Defaults to 6.
  """
  result = [random.choice(CHOICES) for _ in range(length)]
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
