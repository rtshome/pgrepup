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


@dispatch.on('stop')
def stop(**kwargs):

    # Shortcut to ask master password before output Configuration message
    decrypt(config().get('Source', 'password'))

    output_cli_message("Check active subscriptions in Destination nodes")
    puts("")
    subscriptions = get_destination_subscriptions()
    with indent(4, quote=' >'):
        for s in iter(subscriptions.keys()):
            output_cli_message(s)
            message = "Active" if subscriptions[s] else "Stopped"
            print(output_cli_result(message, 4))
            if subscriptions[s]:
                with indent(4, quote=' '):
                    output_cli_message("Launch stop command")
                    syncronize_sequences(s) # must be done BEFORE stopping subscriptions
                    stop_subscription(s)
                    print(output_cli_result("Stopped", 8))

