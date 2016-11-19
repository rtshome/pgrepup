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
import getpass
import os
import sys

from ..config import create as create_config, save as save_config
from ..helpers.docopt_dispatch import dispatch
from ..helpers.crypt import encrypt
from clint.textui import puts, prompt, colored


@dispatch.on('config')
def config(**kwargs):
    puts(colored.cyan("Create a new pgrepup config"))
    try:
        while True:
            conf_filename = prompt.query("Configuration filename", default=kwargs['c'])
            if os.path.isfile(os.path.expanduser(conf_filename)):
                if not prompt.yn("File %s exists " % conf_filename +
                                 "and it'll be overwritten by the new configuration. Are you sure?", default="n"):
                    # warning. prompt.yn return true if the user's answer is the same of default value
                    break
            else:
                break
    except KeyboardInterrupt:
        puts("\n")
        sys.exit(0)

    conf = create_config()

    puts(colored.cyan("Security"))
    conf.add_section("Security")
    if prompt.yn("Do you want to encrypt database credentials using a password?", default="y"):
        conf.set("Security", "encrypted_credentials", "y")
        encrypt('')
        puts("You'll be prompted for password every time pgrepup needs to connect to database")
    else:
        conf.set("Security", "encrypted_credentials", "n")

    conf.set(
        "Security",
        "tmp_folder",
        prompt.query("Folder where pgrepup store temporary dumps and pgpass file", "/tmp")
    )

    puts(colored.cyan("Source Database configuration"))
    conf.add_section("Source")
    conf.set("Source", "host", prompt.query("Ip address or Dns name: "))
    conf.set("Source", "port", prompt.query("Port: "))
    conf.set("Source", "connect_database", prompt.query("Connect Database: ", default="template1"))
    conf.set("Source", "user", prompt.query("Username: "))
    pwd = getpass.getpass()
    conf.set("Source", "password", encrypt(pwd))

    puts(colored.cyan("Destination Database configuration"))
    conf.add_section("Destination")
    conf.set("Destination", "host", prompt.query("Ip address or Dns name: "))
    conf.set("Destination", "port", prompt.query("Port: "))
    conf.set("Destination", "connect_database", prompt.query("Connect Database: ", default="template1"))
    conf.set("Destination", "user", prompt.query("Username: "))
    pwd = getpass.getpass()
    conf.set("Destination", "password", encrypt(pwd))

    save_config(os.path.expanduser(conf_filename))


