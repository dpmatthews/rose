# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# (C) British Crown Copyright 2012-8 Met Office.
#
# This file is part of Rose, a framework for meteorological suites.
#
# Rose is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Rose is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Rose. If not, see <http://www.gnu.org/licenses/>.
# -----------------------------------------------------------------------------
"""Process named settings in rose.config.ConfigTree."""

import os
from rose.env import UnboundEnvironmentVariableError
from rose.fs_util import FileSystemUtil
from rose.popen import RosePopener
from rose.scheme_handler import SchemeHandlersManager
import sys


class UnknownContentError(Exception):

    """Attempt to process an unknown or unsupported content."""

    def __str__(self):
        return "%s: unknown content" % self.args[0]


class ConfigProcessError(Exception):

    """An exception raised when the processing of a setting fails.

    keys: the keys from the root config to the setting.
    value: the value of the setting.
    exc: the exception that triggers this exception.

    """

    def __init__(self, keys, value, exc=None):
        self.keys = keys
        self.value = value
        self.exc = exc
        Exception.__init__(self, keys, value, exc)

    def __str__(self):
        if isinstance(self.exc, UnboundEnvironmentVariableError):
            setting_str = "=".join(list(self.keys))
            return "%s: %s: unbound variable" % (setting_str, self.exc.args[0])
        else:
            setting_str = ""
            if self.keys is not None:
                setting_str += "=".join(list(self.keys))
            if self.value is not None:
                setting_str += "=%s" % str(self.value)
            e_str = str(self.exc)
            if self.exc is None:
                e_str = "bad or missing value"
            return "%s: %s" % (setting_str, e_str)


class ConfigProcessorBase(object):

    """Base class for a config processor."""

    SCHEME = None
    PREFIX = None

    def __init__(self, *args, **kwargs):
        self.manager = kwargs.pop("manager")
        if self.SCHEME is not None:
            self.PREFIX = self.SCHEME + ":"

    def process(self, conf_tree, item, orig_keys=None, orig_value=None):
        """Sub-class should override this method.

        conf_tree:
            The relevant rose.config_tree.ConfigTree object with the full
            configuration.
        item: The current configuration item to process.
        orig_keys:
            The keys for locating the originating setting in conf_tree in a
            recursive processing. None implies a top level call.
        orig_value: The value of orig_keys in conf_tree.
        """
        pass


class ConfigProcessorsManager(SchemeHandlersManager):
    """Load and select config processors."""

    def __init__(self, event_handler=None, popen=None, fs_util=None):
        self.event_handler = event_handler
        if popen is None:
            popen = RosePopener(event_handler)
        self.popen = popen
        if fs_util is None:
            fs_util = FileSystemUtil(event_handler)
        self.fs_util = fs_util
        path = os.path.dirname(os.path.dirname(sys.modules["rose"].__file__))
        SchemeHandlersManager.__init__(
            self, [path], "rose.config_processors", ["process"])

    def handle_event(self, *args, **kwargs):
        """Report an event."""
        if callable(self.event_handler):
            return self.event_handler(*args, **kwargs)

    def process(self, conf_tree, item, orig_keys=None, orig_value=None,
                **kwargs):
        """Process a named item in the conf_tree.

        orig_keys: The keys for locating the originating setting in conf_tree
                   in a recursive processing. None implies a top level call.
        orig_value: The value of orig_keys in conf_tree.
        kwargs: Some processor may accept extra keyword arguments.

        """
        scheme = item
        if ":" in item:
            scheme = item.split(":", 1)[0]
        processor = self.get_handler(scheme)
        if processor is None:
            raise ConfigProcessError(
                orig_keys, orig_value, UnknownContentError(scheme))
        return processor.process(
            conf_tree, item, orig_keys, orig_value, **kwargs)
    __call__ = process
