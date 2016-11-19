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
import os
import sys
try:  # Python 2
    from ConfigParser import SafeConfigParser
    from StringIO import StringIO
except ImportError:  # Python 3
    from configparser import SafeConfigParser
    from io import StringIO


this = sys.modules[__name__]
this.config = None
this.filename = None


class ConfigFileNotFound(Exception):
    pass


def create():
    this.config = SafeConfigParser()
    return this.config


def load(filename):
    this.config = SafeConfigParser()
    load_result = this.config.read(os.path.expanduser(filename))
    if len(load_result) != 1:
        raise ConfigFileNotFound("The configuration file %s does not exist" % filename)
    this.filename = os.path.expanduser(filename)


def config():
    return this.config


def get_tmp_folder():
    return os.path.expanduser(this.config.get('Security', 'tmp_folder'))



def save(filename=None, print_save_result=True):
    if filename is None and this.filename is None:
        raise ConfigFileNotFound("Missing config file to write to")

    if filename is None:
        filename = this.filename

    cfg_file = open(filename, 'w')
    this.config.write(cfg_file)
    cfg_file.close()
    os.chmod(filename, 0600)

    if print_save_result:
        print "Configuration saved to %s." % filename
        print "You can now use the check command to verify setup of source and destination databases"
