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

"""
Pgrepup

Usage:
  pgrepup [-c config] config
  pgrepup [-c config] check [source|destination|all]
  pgrepup [-c config] setup
  pgrepup [-c config] start
  pgrepup [-c config] status
  pgrepup [-c config] stop
  pgrepup [-c config] uninstall
  pgrepup -h | --help
  pgrepup --version

Options:
  -c config     Optional config file. [default: ~/.pgrepup]
  -h --help     Show this screen
  --version     Show version
"""
from version import __version__
from clint.textui import puts, colored
import commands
from helpers.docopt_dispatch import dispatch
from clint.textui import puts, colored


def main():
    puts(colored.green("Pgrepup %s" % __version__))
    try:
        dispatch(__doc__)
    except KeyboardInterrupt:
        puts("\n" + colored.red('Execution aborted'))
        exit(0)
