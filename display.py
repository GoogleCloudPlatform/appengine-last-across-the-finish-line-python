import json
import random

from google.appengine.api import channel


CHOICES = '0123456789ABCDEF'


def GenerateTable(table_id, rows=8, columns=8):
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


def RandHexColor(length=6):
  result = [random.choice(CHOICES) for _ in range(length)]
  return '#' + ''.join(result)


def SendColor(row, column, session_id):
  color = RandHexColor(length=6)

  color_dict = {
      'row': row,
      'column': column,
      'color': color
  }
  channel.send_message(session_id, json.dumps(color_dict))
