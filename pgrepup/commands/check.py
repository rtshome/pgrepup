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
import sys
from clint.textui import puts, colored, indent
from ..helpers.docopt_dispatch import dispatch
from ..helpers.operation_target import get_target
from ..helpers.database import *


this = sys.modules[__name__]
this.current_position = 0


@dispatch.on('check')
def check(**kwargs):
    target = get_target(kwargs)

    targets = []
    if target == 'source':
        targets.append('Source')
    elif target == 'destination':
        targets.append('Destination')
    else:
        targets.append('Source')
        targets.append('Destination')

    puts("Global checkings...")

    with indent(4, quote=' >'):
        output_check_message("Folder %s exists and is writable" % get_tmp_folder())
        c = checks('Source', 'tmp_folder')
        print(output_check_result(c['results']['tmp_folder']))

    for t in targets:
        puts("Checking %s..." % t)
        with indent(4, quote=' >'):
            output_check_message("Connection PostgreSQL connection to %(host)s:%(port)s with user %(user)s" %
                                 get_connection_params(t))
            c = checks(t, 'connection')
            print(output_check_result(c['results']['connection']))
            conn = None
            if c['results']['connection']:
                conn = c['data']['conn']

            output_check_message("If pglogical extension is installed")
            c = checks(t, 'pglogical_installed', db_conn=conn)
            print(output_check_result(c['results']['pglogical_installed']))

            output_check_message("Needed wal_level setting")
            c = checks(t, 'wal_level', db_conn=conn)
            print(output_check_result(c['results']['wal_level']))
            if not c['results']['wal_level']:
                output_hint("Set wal_level to logical")

            output_check_message("Needed max_worker_processes setting")
            c = checks(t, 'max_worker_processes', db_conn=conn)
            print(output_check_result(c['results']['max_worker_processes']))
            if not c['results']['max_worker_processes']:
                output_hint("Increase max_worker_processes to %d" % c['data']['needed_worker_processes'])

            output_check_message("Needed max_replication_slots setting")
            c = checks(t, 'max_replication_slots', db_conn=conn)
            print(output_check_result(c['results']['max_replication_slots']))
            if not c['results']['max_replication_slots']:
                output_hint("Increase max_replication_slots to %d" % c['data']['needed_max_replication_slots'])

            output_check_message("Needed max_wal_senders setting")
            c = checks(t, 'max_wal_senders', db_conn=conn)
            print(output_check_result(c['results']['max_wal_senders']))
            if not c['results']['max_wal_senders']:
                output_hint("Increase max_wal_senders to %d" % c['data']['needed_max_wal_senders'])

            output_check_message("pg_hba.conf settings")
            c = checks(t, 'pg_hba.conf', db_conn=conn)
            print(output_check_result(c['results']['pg_hba.conf']))
            if not c['results']['pg_hba.conf']:
                output_hint("Add the following lines to %s:" % c['data']['pg_hba.conf'])
                print("        " + colored.yellow(c['data']['pg_hba_replication_rule']))
                print("        " + colored.yellow(c['data']['pg_hba_connection_rule']))
                print("    " + colored.yellow("After adding the lines, remember to reload postgreSQL"))

            output_check_message("Local pg_dumpall version")
            c = checks(t, 'pg_dumpall', db_conn=conn)
            print(output_check_result(c['results']['pg_dumpall']))
            if not c['results']['pg_dumpall']:
                output_hint(c['data']['pg_dumpall'])


def checks(target, single_test=None, db_conn=None):
    checks_to_do = [single_test] if single_test else [
        "tmp_folder",
        "connection",
        "pglogical_installed",
        "max_worker_processes",
        "max_replication_slots",
        "wal_level",
        "max_wal_senders",
        "pg_hba.conf",
        "pg_dumpall"
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

        elif c == 'max_worker_processes':
            if not db_conn:
                continue

            needed_worker_processes = int(get_database_count(db_conn))

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
            current_value = get_setting_value(source_db_conn, 'max_replication_slots')
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

            pg_dumpall_exists = os.system("which pg_dumpall >/dev/null") == 0

            if not pg_dumpall_exists:
                reusable_results['pg_dumpall'] = "Install postgresql client utils locally."
                checks_result[c] = False
                continue

            version_rule = re.compile(".*([0-9]\.[0-9]\.[0-9]).*")
            pg_dumpall_version = version_rule.match(subprocess.check_output(["pg_dumpall", "--version"]))
            if not pg_dumpall_version:
                reusable_results['pg_dumpall'] = "Install PostgreSQL client utils locally."
                checks_result[c] = False
                continue

            if pg_dumpall_version.group(1) < db_version:
                checks_result[c] = False
                reusable_results['pg_dumpall'] = "Upgrade local PostgreSQL client utils to version %s" % db_version
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

    overall_result = True
    for r in iter(checks_result.keys()):
        overall_result = overall_result and isinstance(checks_result[r], bool) and checks_result[r] is True

    return {
        'result': overall_result,
        'results': checks_result,
        'data': reusable_results
    }


def output_check_result(result):

    if isinstance(result, bool):
        text = colored.green('OK') if result else colored.red('KO')
    else:
        text = colored.black(result)

    return '.' * (80 - this.current_position - len(text)) + text


def output_check_message(text):
    this.current_position = len(text)+1
    puts(text + ' ', False)


def output_hint(hint):
    print "    " + colored.yellow("Hint: " + hint)

