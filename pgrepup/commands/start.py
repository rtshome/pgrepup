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
from ..helpers.replication import *
from ..helpers.docopt_dispatch import dispatch
from ..helpers.ui import *
from ..helpers.database import *


@dispatch.on('start')
def start(**kwargs):

    output_cli_message("Start replication and upgrade")
    puts("")
    databases = get_cluster_databases(connect('Destination'))
    with indent(4, quote=' >'):
        for d in databases:
            output_cli_message(d)
            start_subscription(d)
            print(output_cli_result(True, 4))
