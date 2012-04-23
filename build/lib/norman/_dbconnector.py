# -*- coding: utf-8 -*-
#
# Copyright (c) 2011 Ilya Kutukov post.ilya@gmail.com
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License as published by the
# Free Software Foundation; either version 2 of the License, or (at your
# option) any later version.
#
# This program is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY
# or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU General Public License
# for more details.
#
# You should have received a copy of the GNU General Public License along
# with this program; if not, write to the Free Software Foundation, Inc.,
# 675 Mass Ave, Cambridge, MA 02139, USA.

from __future__ import with_statement
from __future__ import unicode_literals
from pprint import pprint

import uuid
import logging
import re
import simplejson
from norman.tools import u
from norman._field import NotSet
from norman._table import Table


class DBConnector(object):
    """
    Basic class for DB export-import connector
    """
    UUID_FIELD_LENGTH = 36
    UUID_REGEXP = re.compile('^[\w]{8}-[\w]{4}-[\w]{4}-[\w]{4}-[\w]{12}$')

    def __init__(self, db, *args, **kwargs):
        self.db = db

    def __export_native(self):
        """ Prepare db representation in pyhon dict-list structure
        {
            'tablename1': [
                {
                    '_uuid_': 'c8682f76-570a-4810-96a0-6fc92b181dbe',
                    'field1': 'field 1 content'
                    'field2foreign': 'cfbb21bb-4080-4a83-b0a1-8762f9bbab96'
                },
                ...
            ],
            ...
        }

        All values in the table are converted to strings.
        Keys is presented as _uuid_ fields of each serialized object.
        Foreign keys also provided as UUIDs.
        """

        oid_uuid_bijection = {}

        # There is only plase this function is used so no separate method needed
        def get_uuid_for_object(object_or_oid):
            """ Recieve object and determine its id or just recieve id in int form """
            if isinstance(object_or_oid, int):
                oid = object_or_oid
            else:
                oid = id(object_or_oid)

            if oid not in oid_uuid_bijection.keys():
                oid_uuid_bijection[oid] = str(uuid.uuid4())
            return oid_uuid_bijection[oid]

        # Iterate over tables and records, converting them to dict-list structure
        result = {}
        for table in self.db:
            table_content = []
            for record in table:
                record_content = dict(_uuid_=get_uuid_for_object(record))
                for fname in table.fields():
                    value = getattr(record, fname)
                    if isinstance(value, Table):
                        value = get_uuid_for_object(value)
                    elif value is NotSet:
                        value = 0
                    elif value is not None:
                        # force unicode conversion
                        value = u(value)
                    record_content[fname] = value

                table_content.append(record_content)
                # Table presented as class, but in most DB naming conventions
                # capitalized table names is unnormal,
                # so it will be capitalized back on import
            result[table.__name__.lower()] = table_content
        return result


    def export_dump(self):
        """ Convert native structure to SQL or other format dump """
        return self.__export_native()

    def __import_record(self, records_list, uid):
        # if record was already inserted
        if isinstance(records_list[uid], Table):
            return records_list[uid]

        record = records_list[uid]
        table = record["_table_"]

        keys = set(table.fields()) & set(record.keys())

        args = {}
        for key in keys:
            if isinstance(record[key], int):
                if record[key] == 0:
                    args[key] = NotSet
            else:
                #check for UUID in value
                if len(record[key]) == self.UUID_FIELD_LENGTH\
                   and self.UUID_REGEXP.match(record[key])\
                and record[key] in records_list.keys():
                    args[key] = self.__import_record(records_list, record[key])
                else:
                    args[key] = record[key]

        inserted_record = table(**args)
        records_list[uid] = inserted_record
        return inserted_record


    def __import_native(self, native):
        """ Create DB enteties from native python dict-list structure """
        existing_tables = dict()
        for table in self.db:
            existing_tables[table.__name__] = table

        records_list = dict()

        for (table_name, records) in native.items():
            table = existing_tables.get(table_name.capitalize(), None)
            if table is not None:
                for record in records:
                    if '_uuid_' in record.keys():
                        uuid = record.pop('_uuid_')
                        record['_table_'] = table
                        records_list[uuid] = record
                    else:
                        logging.warning('no _uuid_ field')

        for (uuid, record) in records_list.items():
            self.__import_record(records_list, uuid)


    def import_dump(self, dump):
        """ Read native structure from SQL or other format dump """
        self.__import_native(dump)


class JsonDBConnector(DBConnector):
    """ database connector for json format """

    def export_dump(self):
        native_dump = super(JsonDBConnector, self).export_dump()
        return simplejson.dumps(native_dump, sort_keys=True)

    def import_dump(self, dump):
        loaded_dump = simplejson.loads(dump)
        return super(JsonDBConnector, self).import_dump(loaded_dump)
