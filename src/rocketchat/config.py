# coding: utf-8
"""
Errbot config module.

Config options:
https://github.com/errbotio/errbot/blob/master/errbot/config-template.py
"""
from __future__ import absolute_import

# Standard imports
from datetime import datetime
import logging


# Backend name
BACKEND = 'RocketChat'

# Data directory containing data of backends and plugins
BOT_DATA_DIR = './bot_data'

# Directory containing extra backends
BOT_EXTRA_BACKEND_DIR = './backends'

# Directory containing extra plugins
BOT_EXTRA_PLUGIN_DIR = './plugins'

# Admin bot user names
BOT_ADMINS = ('errbot_admin@localhost',)

# Core plugin names
CORE_PLUGINS = ('ACLs', 'Backup', 'Health', 'Help', 'Plugins', 'Utils')

# Log file path
BOT_LOG_FILE = './errbot.log'

# Logging level
BOT_LOG_LEVEL = logging.DEBUG


class ROCKETCHAT_CONFIG(object):
    """
    Config object for AoikRocketChatErrbot.

    Config values can be overridden by env variables. Config key `SERVER_URI`
    maps to env variable name `AOIKROCKETCHATERRBOT_SERVER_URI`. Use string
    '0', 'false' or 'no' to mean boolean false in env variable value.
    """

    # Meteor server URI.
    #
    # Required.
    #
    # E.g.: 'ws://127.0.0.1:3000/websocket'
    #
    SERVER_URI = 'ws://127.0.0.1:3000/websocket'

    # Meteor client login username.
    #
    # Required.
    #
    LOGIN_USERNAME = 'errbot'

    # Meteor client login password.
    #
    # Required.
    #
    LOGIN_PASSWORD = 'errbot'

    # Whether patch meteor client to fix an existing bug.
    #
    # Default is true.
    #
    PATCH_METEOR_CLIENT = True

    # Whether reconnect is enabled.
    #
    # Default is true.
    #
    RECONNECT_ENABLED = True

    # Whether heartbeat is enabled.
    #
    # If enabled, a specified heartbeat function will be called at a specified
    # interval.
    #
    # Default is false.
    #
    HEARTBEAT_ENABLED = False

    # Heartbeat interval in seconds.
    #
    # Default is 10.
    #
    HEARTBEAT_INTERVAL = 10

    # Create heartbeat function
    @classmethod
    def _heartbeat_func(cls, backend):
        """
        Heartbeat function.

        :param backend: Backend object.

        :return: None.
        """
        # Create message
        msg = 'Heartbeat: {}'.format(datetime.now().strftime('%H:%M:%S'))

        # Send message
        backend.send_rocketchat_message(
            params={
                # Room ID
                'rid': 'GENERAL',
                # Message
                'msg': msg,
            }
        )

    # Heartbeat function object.
    #
    # The function takes the backend object as argument.
    #
    # Required if config `HEARTBEAT_ENABLED` is true.
    #
    HEARTBEAT_FUNC = _heartbeat_func

    # Logging level for this backend only
    BOT_LOG_LEVEL = logging.DEBUG
