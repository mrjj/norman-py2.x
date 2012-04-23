# Copyright (c) 2011 David Townshend
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

from nose.tools import assert_raises, with_setup
from norman import tools
from norman._database import Database

from norman._dbconnector import JsonDBConnector
from norman._field import Field
from norman._table import Table


class TestDBConnector(object):

    def setup(self):
        self.db = Database()

        @self.db.add
        class Persons(Table):
            custno = Field(unique=True)
            name = Field(index=True)
            age = Field(default=20)
            address = Field(index=True)


            def validate(self):
                if not isinstance(self.age, int):
                    self.age = tools.int2(self.age, 0)
                assert isinstance(self.address, Addresses)

        self.Persons = Persons

        @self.db.add
        class Addresses(Table):
            street = Field(unique=True)
            town = Field(unique=True)

            @property
            def people(self):
                return Persons.get(address=self)

            def validate(self):
                assert isinstance(self.town, Towns)

        self.Addresses = Addresses

        @self.db.add
        class Towns(Table):
            name = Field(unique=True)

        self.Towns = Towns


    def test_json_export(self):
        self.Persons(age=35, name="Sherlock Holmes", address=self.Addresses(street="Baker st.", town=self.Towns(name="London")))
        json_connector = JsonDBConnector(self.db)
        dump = json_connector.return_dump()
        assert dump


    def test_json_import(self):
        self.Persons.delete()
        self.Addresses.delete()
        self.Towns.delete()

        json_connector = JsonDBConnector(self.db)
        init_dump = '{"addresses": [{"_uuid_": "7b6e18c4-4259-4da3-b44c-cb335e9d0929", "street": "Baker st.", "town": "d2d3f8df-8ce5-40b0-8183-38084b198dc7"}], "persons": [{"_uuid_": "efc1ec5a-0ef3-4881-870a-bdf69651d7ff", "address": "7b6e18c4-4259-4da3-b44c-cb335e9d0929", "age": "35", "custno": 0, "name": "Sherlock Holmes"}], "towns": [{"_uuid_": "d2d3f8df-8ce5-40b0-8183-38084b198dc7", "name": "London"}]}'
        json_connector.import_dump(init_dump)

        p1 = list(self.Persons.get(name="Sherlock Holmes"))[0]
        a1 = list(self.Addresses.get(street="Baker st."))[0]
        t1 = list(self.Towns.get(name="London"))[0]
        assert p1.address is a1
        assert a1.town is t1


