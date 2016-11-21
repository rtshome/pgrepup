# Copyright (C) 2016 Denis Gasparin <denis@gasparin.net>
#
# This file is part of Pgrepup.
#
# Pgrepup is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Pgrepup is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Pgrepup. If not, see <http://www.gnu.org/licenses/>.
from ..helpers.docopt_dispatch import dispatch
from ..helpers.ui import *
from ..helpers.crypt import *
from ..helpers.database import *
from clint.textui import colored


@dispatch.on('fix')
def fix(**kwargs):

    # Shortcut to ask master password before output Configuration message
    decrypt(config().get('Source', 'password'))

    output_cli_message("Find Source cluster's databases with tables without primary key/unique index...", color='cyan')
    print

    db_conn = connect('Source')
    with indent(4, quote=' >'):
        for db in get_cluster_databases(db_conn):
            output_cli_message(db)
            s_db_conn = connect('Source', db_name=db)
            tables_without_unique = False
            with indent(4, quote=' '):
                for table in get_database_tables(s_db_conn):
                    t_r = table_has_primary_key(s_db_conn, table['schema'], table['table'])
                    if not t_r:
                        tables_without_unique = True
                        print
                        output_cli_message("Found %s.%s without primary key" % (table['schema'], table['table']))
                        result = add_table_unique_index(s_db_conn, table['schema'], table['table'])
                        print(output_cli_result(
                            colored.green('Added %s field' % get_unique_field_name()) if result else False,
                            compensation=4
                        ))

            if not tables_without_unique:
                print(output_cli_result(True))
