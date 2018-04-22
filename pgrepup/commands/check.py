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
import re
import subprocess
import semver
from ..helpers.docopt_dispatch import dispatch
from ..helpers.operation_target import get_target
from ..helpers.database import *
from ..helpers.ui import *


@dispatch.on('check')
def check(**kwargs):
    target = get_target(kwargs)

    # Shortcut to ask master password before output Configuration message
    decrypt(config().get('Source', 'password'))

    targets = []
    if target == 'source':
        targets.append('Source')
    elif target == 'destination':
        targets.append('Destination')
    else:
        targets.append('Source')
        targets.append('Destination')

    output_cli_message("Global checkings...", color='cyan')
    print

    with indent(4, quote=' >'):
        output_cli_message("Folder %s exists and is writable" % get_tmp_folder())
        c = checks('Source', 'tmp_folder')
        print(output_cli_result(c['results']['tmp_folder']))

    for t in targets:
        output_cli_message("Checking %s..." % t, color='cyan')
        print
        with indent(4, quote=' >'):
            output_cli_message("Connection PostgreSQL connection to %(host)s:%(port)s with user %(user)s" %
                               get_connection_params(t))
            c = checks(t, 'connection')
            print(output_cli_result(c['results']['connection']))
            conn = None
            if c['results']['connection']:
                conn = c['data']['conn']

            output_cli_message("pglogical installation")
            c = checks(t, 'pglogical_installed', db_conn=conn)
            if c['results']['pglogical_installed'] == 'NotInstalled':
                print(output_cli_result(False))
                print
                output_hint("Install docs at " +
                            "https://2ndquadrant.com/it/resources/pglogical/pglogical-installation-instructions/\n")
            elif c['results']['pglogical_installed'] == 'InstalledNoSharedLibraries':
                print(output_cli_result(False))
                output_hint("Add pglogical.so to shared_preload_libraries in postgresql.conf")
            else:
                print(output_cli_result(c['results']['pglogical_installed']))

            output_cli_message("pg_ddl_deploy installation")
            c = checks(t, 'pg_ddl_deploy_installed', db_conn=conn)
            if c['results']['pg_ddl_deploy_installed'] == 'NotInstalled':
                print(output_cli_result(False))
                print
                output_hint("Install docs at https://github.com/enova/pgl_ddl_deploy\n")
            elif c['results']['pg_ddl_deploy_installed'] == 'InstalledNoSharedLibraries':
                print(output_cli_result(False))
                output_hint("Add pgl_ddl_deploy.so to shared_preload_libraries in postgresql.conf")
            else:
                print(output_cli_result(c['results']['pg_ddl_deploy_installed']))

            output_cli_message("Needed wal_level setting")
            c = checks(t, 'wal_level', db_conn=conn)
            print(output_cli_result(c['results']['wal_level']))
            if not c['results']['wal_level']:
                output_hint("Set wal_level to logical")

            output_cli_message("Needed max_worker_processes setting")
            c = checks(t, 'max_worker_processes', db_conn=conn)
            print(output_cli_result(c['results']['max_worker_processes']))
            if not c['results']['max_worker_processes']:
                output_hint("Increase max_worker_processes to %d" % c['data']['needed_worker_processes'])

            output_cli_message("Needed max_replication_slots setting")
            c = checks(t, 'max_replication_slots', db_conn=conn)
            print(output_cli_result(c['results']['max_replication_slots']))
            if not c['results']['max_replication_slots']:
                output_hint("Increase max_replication_slots to %d" % c['data']['needed_max_replication_slots'])

            output_cli_message("Needed max_wal_senders setting")
            c = checks(t, 'max_wal_senders', db_conn=conn)
            print(output_cli_result(c['results']['max_wal_senders']))
            if not c['results']['max_wal_senders']:
                output_hint("Increase max_wal_senders to %d" % c['data']['needed_max_wal_senders'])

            output_cli_message("pg_hba.conf settings")
            c = checks(t, 'pg_hba.conf', db_conn=conn)
            print(output_cli_result(c['results']['pg_hba.conf']))
            if not c['results']['pg_hba.conf']:
                output_hint("Add the following lines to %s:" % c['data']['pg_hba.conf'])
                print("        " + colored.yellow(c['data']['pg_hba_replication_rule']))
                print("        " + colored.yellow(c['data']['pg_hba_connection_rule']))
                print("    " + colored.yellow("After adding the lines, remember to reload postgreSQL"))

            output_cli_message("Local pg_dumpall version")
            c = checks(t, 'pg_dumpall', db_conn=conn)
            print(output_cli_result(c['results']['pg_dumpall']))
            if not c['results']['pg_dumpall']:
                output_hint(c['data']['pg_dumpall'])

            if t == 'Source':
                output_cli_message("Source cluster tables without primary keys")
                c = checks(t, 'src_databases', db_conn=conn)
                print
                with indent(4, quote=' '):
                    for db in c['data']['src_databases'].keys():
                        output_cli_message(db)
                        if len(c['data']['src_databases'][db].keys()) == 0:
                            print(output_cli_result(True, compensation=4))
                        else:
                            print
                            with indent(4, quote=' '):
                                for table in c['data']['src_databases'][db].keys():
                                    output_cli_message(table)
                                    print(output_cli_result(c['data']['src_databases'][db][table], compensation=8))
                                    if not c['data']['src_databases'][db][table]:
                                        output_hint("Add a primary key or unique index or use the pgrepup fix command")


def checks(target, single_test=None, db_conn=None):
    checks_to_do = [single_test] if single_test else [
        "tmp_folder",
        "connection",
        "pglogical_installed",
        "pg_ddl_deploy_installed",
        "max_worker_processes",
        "max_replication_slots",
        "wal_level",
        "max_wal_senders",
        "pg_hba.conf",
        "pg_dumpall",
        "src_databases"
    ]
    checks_result = {}
    reusable_results = {}
    for c in checks_to_do:
        checks_result[c] = 'Skipped'

        if c == 'connection':
            conn = connect(target)
            checks_result[c] = True if conn else False
            if conn:
                reusable_results['conn'] = conn
                db_conn = conn

        elif c == 'pglogical_installed':
            if not db_conn:
                continue

            # Look at installation instrutions at:
            # https://2ndquadrant.com/it/resources/pglogical/pglogical-installation-instructions/
            if check_extension(db_conn, 'pglogical'):
                checks_result[c] = True

            # The extension is not already present in db
            # Check if we can install it using create extension command
            checks_result[c] = create_extension(db_conn, 'pglogical', test=True)

        elif c == 'pg_ddl_deploy_installed':
            if not db_conn:
                continue

            # Look at installation instrutions at:
            # https://github.com/enova/pgl_ddl_deploy
            if check_extension(db_conn, 'pgl_ddl_deploy'):
                checks_result[c] = True

            # The extension is not already present in db
            # Check if we can install it using create extension command
            checks_result[c] = create_extension(db_conn, 'pglogical', test=False)
            checks_result[c] = create_extension(db_conn, 'pgl_ddl_deploy', test=True)

        elif c == 'max_worker_processes':
            if not db_conn:
                continue

            if target == 'Source':
                needed_worker_processes = int(get_database_count(db_conn)) + 1
            else:
                needed_worker_processes = int(get_database_count(db_conn))*2 + 1

            current_worker_processes = get_setting_value(db_conn, 'max_worker_processes')
            checks_result[c] = int(current_worker_processes) >= needed_worker_processes
            if not checks_result[c]:
                reusable_results['needed_worker_processes'] = needed_worker_processes

        elif c == 'max_replication_slots':
            if not db_conn:
                continue
            # See https://groups.google.com/a/2ndquadrant.com/forum/#!topic/bdr-list/hP0iDPQwAIU
            if target == 'Destination':
                source_db_conn = connect('Source')
            else:
                source_db_conn = db_conn
            needed_value = get_database_count(source_db_conn)
            current_value = get_setting_value(db_conn, 'max_replication_slots')
            checks_result[c] = int(current_value) >= needed_value
            if not checks_result[c]:
                reusable_results['needed_max_replication_slots'] = needed_value

        elif c == 'wal_level':
            if not db_conn:
                continue
            needed_value = "logical"
            current_value = get_setting_value(db_conn, 'wal_level')
            checks_result[c] = current_value == needed_value

        elif c == 'max_wal_senders':
            if not db_conn:
                continue

            needed_value = int(get_database_count(db_conn)) if target == 'Source' else 0
            current_value = get_setting_value(db_conn, 'max_wal_senders')
            checks_result[c] = int(current_value) >= needed_value
            if not checks_result[c]:
                reusable_results['needed_max_wal_senders'] = needed_value

        elif c == 'pg_hba.conf':
            if not db_conn:
                continue

            rows = get_pg_hba_contents(db_conn)
            if not rows:
                continue

            replication_rule = re.compile("^[ ]*host[ ]+replication[ ]+%s[ ]+%s/32[ ]+md5" % (
                                            get_pgrepup_replication_user(),
                                            get_connection_params('Destination')["host"]
                                         ))
            connection_rule = re.compile("^[ ]*host[ ]+all[ ]+%s[ ]+%s/32[ ]+md5" % (
                                            get_pgrepup_replication_user(),
                                            get_connection_params('Destination')["host"]
                                         ))
            replication_rule_present = False
            connection_rule_present = False
            for r in rows:
                if replication_rule.match(r[0]):
                    replication_rule_present = True

                if connection_rule.match(r[0]):
                    connection_rule_present = True

            if replication_rule_present and connection_rule_present:
                checks_result[c] = True
            else:
                checks_result[c] = False
                reusable_results['pg_hba.conf'] = get_setting_value(db_conn, "hba_file")
                reusable_results['pg_hba_replication_rule'] = "host replication %s %s/32 md5" % (
                    get_pgrepup_replication_user(),
                    get_connection_params('Destination')["host"]
                )
                reusable_results['pg_hba_connection_rule'] = "host all %s %s/32 md5" % (
                    get_pgrepup_replication_user(),
                    get_connection_params('Destination')["host"]
                )
        elif c == 'pg_dumpall':
            if not db_conn:
                continue

            db_version = get_postgresql_version(db_conn)

            if target == 'Source':
                other_target_conn = connect('Destination')
            else:
                other_target_conn = connect('Source')
            other_db_version = get_postgresql_version(other_target_conn)

            if other_db_version > db_version:
                db_version = other_db_version

            db_version_rule = re.compile(r'^([0-9.]+)')
            if not db_version_rule.match(db_version):
                reusable_results['pg_dumpall'] = "Invalid PostgreSQL version %s" % db_version
                checks_result[c] = False
                continue
            db_version = db_version_rule.match(db_version).group(1)

            if db_version.count('.')<2:
                db_version += '.0'

            pg_dumpall_exists = os.system("which pg_dumpall >/dev/null") == 0

            if not pg_dumpall_exists:
                reusable_results['pg_dumpall'] = "Install postgresql client utils locally."
                checks_result[c] = False
                continue
            # see semver._REGEX
            pgdumpall_version_rule = re.compile(r""".*pg_dumpall \(PostgreSQL\) ([0-9.]+).*""")
            pg_dumpall_version = subprocess.check_output(["pg_dumpall", "--version"])
            pg_dumpall_version = pgdumpall_version_rule.match(pg_dumpall_version)
            if not pg_dumpall_version:
                reusable_results['pg_dumpall'] = "Install PostgreSQL client utils locally."
                checks_result[c] = False
                continue
            pg_dumpall_version = pg_dumpall_version.group(1)
            if pg_dumpall_version.count('.')<2:
                pg_dumpall_version += '.0'
            if semver.match(pg_dumpall_version, "<" + db_version):
                checks_result[c] = False
                reusable_results['pg_dumpall'] = "Upgrade local PostgreSQL client utils %s to version %s" % (
                    pg_dumpall_version, db_version
                )
                continue

            checks_result[c] = True

        elif c == 'tmp_folder':
            tmp_folder = os.path.expanduser(config().get('Security', 'tmp_folder'))
            if not os.path.isdir(tmp_folder):
                try:
                    os.makedirs(tmp_folder, 0700)
                except os.error:
                    checks_result[c] = False
                    continue

            try:
                fname = "%s/%s" % (tmp_folder, uuid.uuid4().hex)
                f = open(fname, "w")
                f.write("test")
                f.close()
                os.unlink(fname)
                checks_result[c] = True
            except:
                checks_result[c] = False

        elif c == 'src_databases':
            if not db_conn:
                continue
            if target == 'Destination':
                checks_result[c] = True
                continue

            checks_result[c] = True
            reusable_results['src_databases'] = {}
            for db in get_cluster_databases(db_conn):
                s_db_conn = connect('Source', db_name=db)
                reusable_results['src_databases'][db] = {}
                for table in get_database_tables(s_db_conn):
                    t_r = table_has_primary_key(s_db_conn, table['schema'], table['table'])
                    reusable_results['src_databases'][db]["%s.%s" % (table['schema'], table['table'])] = t_r
                    checks_result[c] = checks_result[c] and t_r

    overall_result = True
    for r in iter(checks_result.keys()):
        overall_result = overall_result and isinstance(checks_result[r], bool) and checks_result[r] is True

    return {
        'result': overall_result,
        'results': checks_result,
        'data': reusable_results
    }
