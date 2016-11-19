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
from ..helpers.replication import *
from ..helpers.utils import merge_two_dicts
from ..config import get_tmp_folder
from ..helpers.ui import *
from check import checks


@dispatch.on('setup')
def setup(**kwargs):

    result = True
    if check_destination_subscriptions():
        result = False

    output_cli_message("Check if there are active subscriptions in Destination nodes")
    print(output_cli_result(result, -4))
    if not result:
        print "    " + colored.yellow("Hint: use pgrepup stop to terminate the subscriptions")
        sys.exit(1)

    targets = ['Source', 'Destination']
    files_to_clean = []
    try:
        output_cli_message("Global tasks")
        puts("")
        with indent(4, quote=' >'):
            output_cli_message("Remove nodes from Destination cluster")
            print
            with indent(4, quote=' '):
                for db in get_cluster_databases(connect('Destination')):
                    output_cli_message(db)
                    drop_node(db)
                    print(output_cli_result(True, 4))

            output_cli_message("Create temp pgpass file")
            pg_pass = create_pgpass_file()
            print(output_cli_result(bool(pg_pass)))

            output_cli_message("Drop pg_logical extension in all databases")
            print
            with indent(4, quote=' '):
                for db in get_cluster_databases(connect('Source')):
                    output_cli_message(db)
                    if not clean_pglogical_setup(db):
                        print(output_cli_result(False, compensation=4))
                        continue
                    print(output_cli_result(True, compensation=4))

        source_setup_results = {}
        for t in targets:
            results = checks(t)
            output_cli_message("Setup %s" % t)
            if not results['result']:
                print(output_cli_result('Skipped'))
                continue

            puts("")
            with indent(4, quote=' >'):
                if t == 'Source':
                    source_setup_results = _setup_source(results['data']['conn'], pg_pass)
                    if isinstance(source_setup_results, dict) and source_setup_results.has_key('pg_dumpall'):
                        files_to_clean.append(source_setup_results['pg_dumpall'])
                else:
                    _setup_destination(
                        results['data']['conn'],
                        pg_pass=pg_pass,
                        source_setup_results=source_setup_results
                    )
    finally:
        output_cli_message("Cleaning up")
        puts("")
        with indent(4, quote=' >'):
            output_cli_message("Remove temporary pgpass file")
            print(output_cli_result(remove_pgpass_file()))

            output_cli_message("Remove other temporary files")
            for tempf in files_to_clean:
                try:
                    os.unlink(tempf)
                    print(output_cli_result(True))
                except OSError:
                    print(output_cli_result(False))


def _setup_source(conn, pg_pass):
    result = {'result': True}
    output_cli_message("Create user for replication")
    result['result'] = result['result'] and create_user(conn, get_pgrepup_replication_user(),
                                                        get_pgrepup_user_password())
    print(output_cli_result(result['result']))

    pg_dumpall_schema = "%s/pg_dumpall_schema_%s.sql" % (get_tmp_folder(), uuid.uuid4().hex)
    output_cli_message("Dump globals and schema of all databases")
    pg_dumpall_schema_result = \
        os.system("PGPASSFILE=%(pgpass)s pg_dumpall -U %(user)s -h %(host)s -p%(port)s -s -f %(fname)s --if-exists -c" %
                  merge_two_dicts(
                      get_connection_params('Source'),
                      {"fname": pg_dumpall_schema, "pgpass": pg_pass}
                  ))
    result['result'] = result['result'] and pg_dumpall_schema_result == 0
    print(output_cli_result(result['result']))

    if pg_dumpall_schema_result == 0:
        result['pg_dumpall'] = pg_dumpall_schema

    output_cli_message("Setup pglogical replication sets on Source node name")
    print
    with indent(4, quote=' '):
        for db in get_cluster_databases(conn):
            output_cli_message(db)
            if not create_replication_sets(db):
                result[db] = False
                print(output_cli_result(result[db], compensation=4))
                continue
            result[db] = True
            print(output_cli_result(True, compensation=4))

    # output_cli_message("Setup pglogical ddl replication on Source node name")
    # print
    # with indent(4, quote=' '):
    #     for db in get_cluster_databases(conn):
    #         output_cli_message(db)
    #         if not setup_ddl_syncronization(db):
    #             print(output_cli_result(False, compensation=4))
    #             continue
    #         print(output_cli_result(True, compensation=4))

    for db in get_cluster_databases(conn):
        store_setup_result('Source', db, result[db] and result['result'])
    return result


def _setup_destination(conn, pg_pass, source_setup_results):
    result = {'result': True}
    output_cli_message("Create and import source globals and schema")
    if source_setup_results.has_key('pg_dumpall'):
        restore_schema_result = \
            os.system(
                "PGPASSFILE=%(pgpass)s psql -U %(user)s -h %(host)s -p%(port)s -f %(fname)s -d postgres &>/dev/null"
                % merge_two_dicts(
                    get_connection_params('Destination'),
                    {"fname": source_setup_results['pg_dumpall'], "pgpass": pg_pass}
                ))

        result['result'] = result['result'] and restore_schema_result == 0
        print(output_cli_result(restore_schema_result == 0))
    else:
        result['result'] = result['result'] and False
        print(output_cli_result('Skipped'))

    output_cli_message("Setup pglogical Destination node name")
    print
    with indent(4, quote=' '):
        for db in get_cluster_databases(conn):
            output_cli_message(db)
            result[db] = create_pglogical_node(db)
            print(output_cli_result(result[db], compensation=4))

    for db in get_cluster_databases(conn):
        store_setup_result('Destination', db, result[db] and result['result'])
