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
import sys
from clint.textui import puts, prompt, colored, indent, progress


this = sys.modules[__name__]
this.current_position = 0


def output_cli_message(text):
    this.current_position = len(text) + 1
    puts(text + ' ', False)


def output_cli_result(result, compensation=0):
    if isinstance(result, bool):
        text = colored.green('OK') if result else colored.red('KO')
    else:
        text = colored.black(result)

    return '.' * (80 - this.current_position - len(text) - compensation) + text
