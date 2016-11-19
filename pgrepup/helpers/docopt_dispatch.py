"""Dispatch from command-line arguments to functions."""
import re
import sys
from collections import OrderedDict
from clint.textui import puts, colored


class DispatchError(Exception):
    pass


class Dispatch(object):

    def __init__(self):
        self._functions = OrderedDict()

    def on(self, *patterns):
        def decorator(function):
            self._functions[patterns] = function
            return function
        return decorator

    def __call__(self, *args, **kwargs):
        from docopt import docopt
        arguments = docopt(*args, **kwargs)

        from ..config import load as config_load
        from ..config import ConfigFileNotFound

        try:
            config_load(arguments['-c'])
        except ConfigFileNotFound as e:
            if not arguments['config']:
                puts(colored.red(str(e)))
                sys.exit(1)

        for patterns, function in self._functions.items():
            if all(arguments[pattern] for pattern in patterns):
                function(**self._kwargify(arguments))
                return
        raise DispatchError('None of dispatch conditions %s is triggered'
                            % self._formated_patterns)

    @property
    def _formated_patterns(self):
        return ', '.join(' '.join(pattern)
                         for pattern in self._functions.keys())

    @staticmethod
    def _kwargify(arguments):
        kwargify = lambda string: re.sub('\W', '_', string).strip('_')
        return dict((kwargify(key), value) for key, value in arguments.items())


dispatch = Dispatch()
