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
from check import checks
from ..helpers.replication import *
from ..config import config
from ..helpers.crypt import decrypt


@dispatch.on('status')
def status(**kwargs):
    targets = ['Source', 'Destination']

    # Shortcut to ask master password before output Configuration message
    decrypt(config().get('Source', 'password'))

    output_cli_message("Configuration")
    puts("")
    check_results = {}
    with indent(4, quote=' >'):
        for t in targets:
            results = checks(t)
            output_cli_message("%s database cluster" % t)
            print(output_cli_result(results['result']))
            check_results[t] = results['result']

    output_cli_message("Pglogical setup")
    puts("")
    setup_results = {}
    with indent(4, quote=' >'):
        for t in targets:
            output_cli_message("%s database cluster" % t)
            setup_results[t] = {}
            print
            with indent(4, quote=' '):
                for db in get_cluster_databases(connect(t)):
                    output_cli_message(db)
                    setup_results[t][db] = get_setup_result(t, db)
                    print(output_cli_result(setup_results[t][db], compensation=4))

    output_cli_message("Replication status")
    puts("")
    with indent(4, quote=' >'):
        for db in get_cluster_databases(connect(t)):
            output_cli_message("Database %s" % db)
            if not (setup_results['Source'][db] and setup_results['Destination'][db] and
                    check_results['Source'] and check_results['Destination']):
                print(output_cli_result("Skipped, configuration/setup problems"))
            else:
                r = get_replication_status(db)
                if not r['result']:
                    print(output_cli_result(False))
                    continue
                with indent(4, quote=' '):
                    print
                    output_cli_message("Replication status")
                    print(output_cli_result(r['status'], compensation=4))
        output_cli_message("Xlog difference (bytes)")
        print(output_cli_result("%d" % get_replication_delay()))
