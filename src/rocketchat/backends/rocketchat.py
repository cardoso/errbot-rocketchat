# coding: utf-8
"""
Errbot backend for Rocket.Chat.
"""
from __future__ import absolute_import

# Standard imports
import logging
import os
from pprint import pformat
from threading import Event
import time
from traceback import format_exc

# External imports
from MeteorClient import CollectionData
from MeteorClient import MeteorClient
from errbot.backends.base import Card
from errbot.backends.base import OFFLINE
from errbot.backends.base import ONLINE
from errbot.backends.base import Identifier
from errbot.backends.base import Message
from errbot.backends.base import Person
from errbot.backends.base import Presence
from errbot.backends.base import Room
from errbot.core import ErrBot


def metaclass(meta):
    """
    Parameterized class decorator applying metaclass to decorated class.

    The parameterized class decorator takes a metaclass and creates a class \
        decorator. The created class decorator takes a class and calls the
        metaclass to create a new class based on given class.

    :param meta: Metaclass.

    :return: Class decorator.
    """
    # Create class decorator
    def class_decorator(cls):
        """
        Class decorator.

        :param cls: Original class.

        :return: New class created by the metaclass.
        """
        # Get original class' attributes dict copy
        attrs_dict = cls.__dict__.copy()

        # Remove attribute `__dict__` from the attributes dict copy
        attrs_dict.pop('__dict__', None)

        # Remove attribute `__weakref__` from the attributes dict copy
        attrs_dict.pop('__weakref__', None)

        # Call metaclass to create new class based on given class
        return meta(cls.__name__, cls.__bases__, attrs_dict)

    # Return class decorator
    return class_decorator


class KeyAsValueMeta(type):
    """
    Metaclass that sets given class' attribute keys as attribute values.
    """

    def __init__(cls, name, bases, attrs):
        """
        Metaclass' instance constructor.

        :param cls: Class object to be handled by the metaclass.

        :param name: Class name.

        :param bases: Class object's base classes list.

        :param attrs: Class object's attributes dict.

        :return: None.
        """
        # Call super constructor
        super(KeyAsValueMeta, cls).__init__(name, bases, attrs)

        # For given class' each attribute
        for key, _ in attrs.items():
            # Set attribute key as attribute value
            setattr(cls, key, key)


# Class decorator that applies metaclass `KeyAsValueMeta` to decorated class
key_as_value = metaclass(KeyAsValueMeta)


@key_as_value
class CONFIG_KEYS(object):
    """
    Class that contains config keys.

    After decorated by `key_as_value`, the attribute values are set to be the
    attribute names, i.e. CONFIG_KEYS.SERVER_URI == 'SERVER_URI'.

    Config values can be overridden by env variables. Config key `SERVER_URI`
    maps to env variable name `ROCKETCHAT_SERVER_URI`. Use string
    '0', 'false' or 'no' to mean boolean false in env variable value.

    The prefix used when mapping config name to env variable name is defined at
    5IQNR.
    """

    # Meteor server URI.
    #
    # Required.
    #
    # E.g.: 'ws://127.0.0.1:3000/websocket'
    #
    SERVER_URI = ''

    # Meteor client login username.
    #
    # Required.
    #
    LOGIN_USERNAME = ''

    # Meteor client login password.
    #
    # Required.
    #
    LOGIN_PASSWORD = ''

    # Whether patch meteor client to fix an existing bug.
    #
    # Default is true.
    #
    PATCH_METEOR_CLIENT = ''

    # Whether reconnect is enabled.
    #
    # Default is true.
    #
    RECONNECT_ENABLED = ''

    # Whether heartbeat is enabled.
    #
    # If enabled, a specified heartbeat function will be called at a specified
    # interval.
    #
    # Default is false.
    #
    HEARTBEAT_ENABLED = ''

    # Heartbeat interval in seconds.
    #
    # Default is 10.
    #
    HEARTBEAT_INTERVAL = ''

    # Heartbeat function object.
    #
    # The function takes the backend object as argument.
    #
    # Required if config `HEARTBEAT_ENABLED` is true.
    #
    HEARTBEAT_FUNC = ''

    # Logging level for this backend only
    BOT_LOG_LEVEL = ''


# The backend's config object's attribute name on the config module
_CONFIG_OBJ_KEY = 'ROCKETCHAT_CONFIG'

# 5IQNR
# Prefix used when mapping config name to env variable name.
#
# E.g. Config key `SERVER_URI` maps to env variable name
# `ROCKETCHAT_SERVER_URI`.
#
_ENV_VAR_NAME_PREFIX = 'ROCKETCHAT_'


class RocketChatUser(Person):
    """
    Class that represents a rocket chat user.
    """

    def __init__(self, person, client=None, nick=None, fullname=None):
        """
        Constructor.

        :param person: User name.

        :param client: User's client object. Unused.

        :param nick: User nickname. Defaults to argument `person`.

        :param fullname: User full name. Defaults to argument `person`.

        :return: None.
        """
        # User name
        self._person = person

        # User's client object
        self._client = client

        # User nickname
        self._nick = nick or self._person

        # User full name
        self._fullname = fullname or self._person

    @property
    def person(self):
        """
        Get user name.

        :return: User name.
        """
        # Return user name
        return self._person

    @property
    def client(self):
        """
        Get user's client object.

        :return: User's client object.
        """
        # Return user's client object
        return self._client

    @property
    def nick(self):
        """
        Get user nickname.

        :return: User nickname.
        """
        # Return user nickname
        return self._nick

    @property
    def fullname(self):
        """
        Get user full name.

        :return: User full name.
        """
        # Return user full name
        return self._fullname

    # ACL attribute used by the `ACLs` plugin
    aclattr = person

    def __str__(self):
        """
        Get string value of the object.

        :return: String value of the object.
        """
        # Return user name
        return self._person


class RocketChat(ErrBot):
    """
    Errbot backend for Rocket.Chat.

    The backend logs in as a Rocket.Chat user, receiving and sending messages.
    """

    def __init__(self, config):
        """
        Constructor.

        :param config: Errbot's config module.

        :return: None.
        """
        # Call super method
        super(RocketChat, self).__init__(config)

        # Get the backend's config object
        self._config_obj = getattr(self.bot_config, _CONFIG_OBJ_KEY, None)

        # Get logging level from env variable or config object
        log_level = orig_log_level = self._get_config(
            CONFIG_KEYS.BOT_LOG_LEVEL, None
        )

        # If not specified
        if log_level is None:
            # Get logging level from config module
            log_level = orig_log_level = getattr(
                self.bot_config, CONFIG_KEYS.BOT_LOG_LEVEL, None
            )

            # If not specified
            if log_level is None:
                # Use default
                log_level = logging.DEBUG

        # If the logging level is string, e.g. 'DEBUG'.
        # This means it may be an attribute name of the `logging` module.
        if isinstance(log_level, str):
            # Get attribute value from the `logging` module
            log_level = getattr(logging, log_level, None)

        # Error message
        error_msg = None

        # If the logging level is not int
        if not isinstance(log_level, int):
            # Get message
            error_msg = 'Config `BOT_LOG_LEVEL` value is invalid: {}'.format(
                repr(orig_log_level)
            )

            # Log message
            self._log_error(error_msg)

            # Raise error
            raise ValueError(error_msg)

        # Get logger
        self._logger = logging.getLogger('rocketchat')

        # Set logging level
        self._logger.setLevel(log_level)

        # Get message
        msg = '# ----- Created logger -----\nBOT_LOG_LEVEL: {}'.format(
            log_level
        )

        # Log message
        self._logger.debug(msg)

        # Get rocket chat server URI
        self._server_uri = self._get_config(
            CONFIG_KEYS.SERVER_URI
        )

        # If server URI is not specified
        if self._server_uri is None:
            # Get message
            error_msg = 'Missing config `SERVER_URI`.'

            # Log message
            self._log_error(error_msg)

            # Raise error
            raise ValueError(error_msg)

        # Get login username
        self._login_username = self._get_config(
            CONFIG_KEYS.LOGIN_USERNAME
        )

        # If login username is not specified
        if self._login_username is None:
            # Get message
            error_msg = 'Missing config `LOGIN_USERNAME`.'

            # Log message
            self._log_error(error_msg)

            # Raise error
            raise ValueError(error_msg)

        # Get login password
        self._login_password = self._get_config(
            CONFIG_KEYS.LOGIN_PASSWORD
        )

        # If login password is not specified
        if self._login_password is None:
            # Get message
            error_msg = 'Missing config `LOGIN_PASSWORD`.'

            # Log message
            self._log_error(error_msg)

            # Raise error
            raise ValueError(error_msg)

        # If login password is not bytes
        if not isinstance(self._login_password, bytes):
            # Convert login password to bytes
            self._login_password = bytes(self._login_password, 'utf-8')

        # Create login user's identifier object.
        #
        # This attribute is required by superclass.
        #
        self.bot_identifier = self.build_identifier(self._login_username)

        # Event set when the the meteor client has done topic subscribing.
        #
        # When the event is set, the meteor client is in one of the two states:
        # - The topic subscribing has succeeded and the meteor client has
        #   started handling messages.
        # - The topic subscribing has failed and the meteor client has been
        #   closed.
        #
        # The rationale is that the loop at 65ZNO uses the meteor client's
        # `connected` attribute to decide whether continue, and the attribute
        # value is ready for use only after this event is set.
        self._subscribing_done_event = Event()

        # Event set when the meteor client calls the `closed` callback at
        # 3DMYH.
        #
        # The rationale is that the main thread code at 5W6XQ has to wait until
        # the meteor client is closed and the `closed` callback hooked at 7MOJX
        # is called. This ensures the cleanup is fully done.
        #
        self._meteor_closed_event = Event()

    @property
    def mode(self):
        """
        Get mode name.

        :return: Mode name.
        """
        # Return mode name
        return 'rocketchat'

    def _log_debug(self, msg):
        """
        Log debug message.

        :param msg: Message to log.

        :return: None.
        """
        # Log the message
        self._logger.debug(msg)

    def __hash__(self):
        """Bots are now stored as a key in the bot so they need to be hashable."""
        return id(self)

    def _log_error(self, msg):
        """
        Log error message.

        :param msg: Message to log.

        :return: None.
        """
        # Log the message
        self._logger.error(msg)

    def _get_config(self, key, default=None):
        """
        Get config value from env variable or config object.

        Env variable takes precedence.

        :param key: Config key.

        :param default: Default value.

        :return: Config value.
        """
        # Get env variable name
        env_var_name = _ENV_VAR_NAME_PREFIX + key

        # Get config value from env variable
        config_value = os.environ.get(env_var_name, None)

        # If not specified
        if config_value is None:
            # If not have config object
            if self._config_obj is None:
                # Use default
                config_value = default

            # If have config object
            else:
                # Get config value from config object
                config_value = getattr(self._config_obj, key, default)

        # Return config value
        return config_value

    def _get_bool_config(self, key, default=None):
        """
        Get boolean config value from env variable or config object.

        Env variable takes precedence.

        :param key: Config key.

        :param default: Default value.

        :return: Config value.
        """
        # Get config value
        config_value = self._get_config(key=key, default=default)

        # If config value is false.
        # This aims to handle False, 0, and None.
        if not config_value:
            # Return False
            return False

        # If config value is not false
        else:
            # Get config value's string in lower case
            config_value_str_lower = str(config_value).lower()

            # Consider '0', case-insensitive 'false' and 'no' as false,
            # otherwise as true.
            return config_value_str_lower not in ['0', 'false', 'no']

    def _patch_meteor_client(self):
        """
        Patch meteor client to fix an existing bug.

        :return: None.
        """
        # Get whether need patch meteor client. Default is True.
        need_patch = self._get_bool_config(
            CONFIG_KEYS.PATCH_METEOR_CLIENT, True
        )

        # If need patch meteor client
        if need_patch:
            # Create `change_data` function
            def change_data(self, collection, id, fields, cleared):
                """
                Callback called when data change occurred.

                :param self: CollectionData object.

                :param collection: Data collection key.

                :param id: Data item key.

                :param fields: Data fields changed.

                :param cleared: Data fields to be cleared.

                :return None.
                """
                # If the data collection key not exists
                #
                # The original `change_data` function assumes it is existing,
                # but it is not in some cases.
                #
                if collection not in self.data:
                    # Add data collection
                    self.data[collection] = {}

                # If the data item key not exists.
                #
                # The original `change_data` function assumes it is existing,
                # but it is not in some cases.
                #
                if id not in self.data[collection]:
                    # Add data item
                    self.data[collection][id] = {}

                # For each data field changed
                for key, value in fields.items():
                    # Add to the data item
                    self.data[collection][id][key] = value

                # For each data field to be cleared
                for key in cleared:
                    # Delete from the data item
                    del self.data[collection][id][key]

            # Store original `change_data`.
            #
            # pylint: disable=protected-access
            CollectionData._orig_change_data = CollectionData.change_data
            # pylint: enable=protected-access

            # Replace original `change_data`
            CollectionData.change_data = change_data

    def build_identifier(self, username):
        """
        Create identifier object for given username.

        :param username: Rocket chat user name.

        :return: RocketChatUser instance.
        """
        # Create identifier object
        return RocketChatUser(username)

    def serve_forever(self):
        """
        Run the bot.

        Called by the Errbot framework.

        :return: None.
        """
        # Log message
        self._log_debug('# ----- serve_forever -----')

        # Patch meteor client
        self._patch_meteor_client()

        # Get whether reconnect is enabled
        reconnect_enabled = self._get_bool_config(
            CONFIG_KEYS.RECONNECT_ENABLED,
            default=True,
        )

        try:
            # Loop
            while True:
                try:
                    # Run for once
                    self.serve_once()

                # If have error
                except Exception:
                    # Log message
                    self._log_error(
                        (
                            '# ----- `serve_once` failed with error'
                            ' -----\n{}'
                        ).format(format_exc())
                    )

                # If reconnect is enabled
                if reconnect_enabled:
                    # Get message
                    msg = (
                        '# ----- Sleep before reconnect -----\n'
                        'Interval: {:.2f}'
                    ).format(self._reconnection_delay)

                    # Log message
                    self._log_debug(msg)

                    # Sleep before reconnect
                    self._delay_reconnect()

                    # Log message
                    self._log_debug('# ----- Wake up to reconnect -----')

                    # Continue the loop
                    continue

                # If reconnect is not enabled
                else:
                    # Break the loop
                    break

        # If have `KeyboardInterrupt`
        except KeyboardInterrupt:
            # Do not treat as error
            pass

        # Always do
        finally:
            # Call `shutdown`
            self.shutdown()

        # Log message
        self._log_debug('# ===== serve_forever =====')

    def serve_once(self):
        """
        Run the bot until the connection is disconnected.

        :return: None.
        """
        # Log message
        self._log_debug('# ----- serve_once -----')

        # Log message
        self._log_debug(
            (
                '# ----- Create meteor client -----\n'
                'SERVER_URI: {}'
            ).format(self._server_uri)
        )

        # Create meteor client
        self._meteor_client = MeteorClient(
            self._server_uri,
            # Disable the meteor client's auto reconnect.
            # Let `serve_forever` handle reconnect.
            auto_reconnect=False,
            debug=False
        )

        # Log message
        self._log_debug('# ----- Hook meteor client callbacks -----')

        # 5DI82
        # Hook meteor client `connected` callback
        self._meteor_client.on('connected', self._meteor_connected_callback)

        # 2RAYF
        # Hook meteor client `changed` callback
        self._meteor_client.on('changed', self._meteor_changed_callback)

        # 4XIZB
        # Hook meteor client `added` callback
        self._meteor_client.on('added', self._meteor_added_callback)

        # 2JEIK
        # Hook meteor client `removed` callback
        self._meteor_client.on('removed', self._meteor_removed_callback)

        # 32TF2
        # Hook meteor client `failed` callback
        self._meteor_client.on('failed', self._meteor_failed_callback)

        # 5W6RX
        # Hook meteor client `reconnected` callback
        self._meteor_client.on(
            'reconnected', self._meteor_reconnected_callback
        )

        # 7MOJX
        # Hook meteor client `closed` callback
        self._meteor_client.on('closed', self._meteor_closed_callback)

        # Clear the event
        self._subscribing_done_event.clear()

        # Clear the event
        self._meteor_closed_event.clear()

        # Log message
        self._log_debug('# ----- Connect to meteor server -----')

        try:
            # Connect to meteor server.
            #
            # If the connecting succeeds, the meteor client's thread will call
            # `self._meteor_connected_callback` hooked at 5DI82. The login,
            # topic subscribing, and message handling are run in that thread.
            #
            # The main thread merely waits until the meteor client is closed,
            # meanwhile it calls heartbeat function at interval if specified.
            #
            self._meteor_client.connect()

        # If have error
        except Exception as e:
            # Log message
            self._log_debug('# ----- Connecting failed -----')

            # Log message
            self._log_debug('# ----- Unhook meteor client callbacks -----')

            # Remove meteor client callbacks
            self._meteor_client.remove_all_listeners()

            # Remove meteor client reference
            self._meteor_client = None

            # The two events below should not have been set if the connecting
            # failed. Just in case.
            #
            # Clear the event
            self._subscribing_done_event.clear()

            # Clear the event
            self._meteor_closed_event.clear()

            # Raise the error
            raise

        # Get whether heartbeat is enabled
        heartbeat_enabled = self._get_bool_config(
            CONFIG_KEYS.HEARTBEAT_ENABLED
        )

        try:
            # Wait until the topic subscribing is done in another thread at
            # 5MS7A
            self._subscribing_done_event.wait()

            # If heartbeat is enabled
            if heartbeat_enabled:
                # Get heartbeat function
                heartbeat_func = self._get_config(
                    CONFIG_KEYS.HEARTBEAT_FUNC
                )

                # Assert the function is callable
                assert callable(heartbeat_func), repr(heartbeat_func)

                # Get heartbeat interval
                heartbeat_interval = self._get_config(
                    CONFIG_KEYS.HEARTBEAT_INTERVAL,
                    default=10,
                )

                # Convert heartbeat interval to float
                heartbeat_interval = float(heartbeat_interval)

                # 65ZNO
                # Loop until the meteor client is disconnected
                while self._meteor_client.connected:
                    # Send heartbeat
                    heartbeat_func(self)

                    # Sleep before sending next heartbeat
                    time.sleep(heartbeat_interval)

            # 5W6XQ
            # Wait until the meteor client is closed and the `closed` callback
            # is called at 3DMYH
            self._meteor_closed_event.wait()

        # If have error
        except Exception as e:
            # Close meteor client.
            #
            # This will cause `self._meteor_closed_callback` to be called,
            # which will set the `self._meteor_closed_event` below.
            #
            self._meteor_client.close()

            # See 5W6XQ
            self._meteor_closed_event.wait()

            # Raise the error
            raise

        # Always do
        finally:
            # Log message
            self._log_debug('# ----- Unhook meteor client callbacks -----')

            # Remove meteor client callbacks
            self._meteor_client.remove_all_listeners()

            # Remove meteor client reference.
            #
            # Do this before calling `callback_presence` below so that the
            # plugins will not be able to access the already closed client.
            #
            self._meteor_client = None

            # Log message
            self._log_debug('# ----- Call `callback_presence` -----')

            # Call `callback_presence`
            self.callback_presence(
                Presence(identifier=self.bot_identifier, status=OFFLINE)
            )

            # Log message
            self._log_debug('# ----- Call `disconnect_callback` -----')

            # Call `disconnect_callback` to unload plugins
            self.disconnect_callback()

            # Clear the event
            self._subscribing_done_event.clear()

            # Clear the event
            self._meteor_closed_event.clear()

        # Log message
        self._log_debug('# ===== serve_once =====')

    def _meteor_connected_callback(self):
        """
        Callback called when the meteor client is connected.

        Hooked at 5DI82.

        :return: None.
        """
        # Log message
        self._log_debug('# ----- _meteor_connected_callback -----')

        # Log message
        self._log_debug(
            '# ----- Log in to meteor server -----\nUser: {}'.format(
                self._login_username
            )
        )

        # Log in to meteor server
        self._meteor_client.login(
            user=self._login_username,
            password=self._login_password,
            # 2I0GP
            callback=self._meteor_login_callback,
        )

    def _meteor_login_callback(self, error_info, success_info):
        """
        Callback called when the meteor client has succeeded or failed login.

        Hooked at 2I0GP.

        :param error_info: Error info.

        :param success_info: Success info.

        :return: None.
        """
        # Log message
        self._log_debug('# ----- _meteor_login_callback -----')

        # If have error info
        if error_info is not None:
            # Get message
            msg = 'Login failed:\n{}'.format(pformat(error_info, width=1))

            # Log message
            self._log_debug(msg)

            # Close meteor client.
            # This will cause `_meteor_closed_callback` be called.
            self._meteor_client.close()

        # If not have error info
        else:
            # Get message
            msg = 'Login succeeded:\n{}'.format(pformat(success_info, width=1))

            # Log message
            self._log_debug(msg)

            # Subscribe to message events
            self._meteor_client.subscribe(
                # Topic name
                name='stream-room-messages',
                params=[
                    # All messages from rooms the rocket chat user has joined
                    '__my_messages__', False,
                ],
                # 6BKIR
                callback=self._meteor_subscribe_callback,
            )

    def _meteor_subscribe_callback(self, error_info):
        """
        Callback called when the meteor client has succeeded or failed \
            subscribing.

        Hooked at 6BKIR.

        :param error_info: Error info.

        :return: None.
        """
        # Log message
        self._log_debug('# ----- _meteor_subscribe_callback -----')

        # If have error info
        if error_info is not None:
            # Get message
            msg = 'Subscribing failed:\n{}'.format(
                pformat(error_info, width=1)
            )

            # Log message
            self._log_debug(msg)

            # Close meteor client.
            # This will cause `self._meteor_closed_callback` to be called.
            self._meteor_client.close()

        # If not have error info
        else:
            # Log message
            self._log_debug('Subscribing succeeded.')

            # Log message
            self._log_debug('# ----- Call `connect_callback` -----')

            # Call `connect_callback` to load plugins.
            #
            # This is called in meteor client's thread.
            # Plugins should not assume they are loaded from the main thread.
            #
            self.connect_callback()

            # Log message
            self._log_debug('# ----- Call `callback_presence` -----')

            # Call `callback_presence`
            self.callback_presence(
                Presence(identifier=self.bot_identifier, status=ONLINE)
            )

            # Log message
            self._log_debug(
                '# ----- Hook callback `_meteor_changed_callback` -----'
            )

            # Reset reconnection count
            self.reset_reconnection_count()

            # 5MS7A
            # Set the topic subscribing is done
            self._subscribing_done_event.set()

    def _meteor_changed_callback(self, collection, id, fields, cleared):
        """
        Callback called when the meteor client received message.

        Hooked at 2RAYF.

        :param collection: Data collection key.

        :param id: Data item key.

        :param fields: Data fields changed.

        :param cleared: Data fields to be cleared.

        :return: None.
        """
        # If is message event
        if collection == 'stream-room-messages':
            # Get `args` value
            args = fields.get('args', None)

            # If `args` value is list
            if isinstance(args, list):
                # For each message info
                for msg_info in args:
                    # Get message
                    msg = msg_info.get('msg', None)

                    # If have message
                    if msg is not None:
                        # Get sender info
                        sender_info = msg_info['u']

                        # Get sender username
                        sender_username = sender_info['username']

                        # If the sender is not the bot itself
                        if sender_username != self._login_username:
                            # Create sender's identifier object
                            sender_identifier = self.build_identifier(
                                sender_username
                            )

                            # Create extras info
                            extras = {
                                # 2QTGO
                                'msg_info': msg_info,
                            }

                            # Create received message object
                            msg_obj = Message(
                                body=msg,
                                frm=sender_identifier,
                                to=self.bot_identifier,
                                extras=extras,
                            )

                            # Log message
                            self._log_debug(
                                '# ----- Call `callback_message` -----'
                            )

                            # Call `callback_message` to dispatch the message
                            # to plugins
                            self.callback_message(msg_obj)

    def _meteor_added_callback(self, collection, id, fields):
        """
        Callback called when the meteor client emits `added` event.

        Hooked at 4XIZB.

        :param collection: Data collection key.

        :param id: Data item key.

        :param fields: Data fields.

        :return: None.
        """
        # Log message
        self._log_debug('# ----- _meteor_added_callback -----')

    def _meteor_removed_callback(self, collection, id):
        """
        Callback called when the meteor client emits `removed` event.

        Hooked at 2JEIK.

        :param collection: Data collection key.

        :param id: Data item key.

        :return: None.
        """
        # Log message
        self._log_debug('# ----- _meteor_removed_callback -----')

    def _meteor_failed_callback(self):
        """
        Callback called when the meteor client emits `failed` event.

        Hooked at 32TF2.

        :return: None.
        """
        # Log message
        self._log_debug('# ----- _meteor_failed_callback -----')

    def _meteor_reconnected_callback(self):
        """
        Callback called when the meteor client emits `reconnected` event.

        Hooked at 5W6RX.

        :return: None.
        """
        # Log message
        self._log_debug('# ----- _meteor_reconnected_callback -----')

    def _meteor_closed_callback(self, code, reason):
        """
        Callback called when the meteor client emits `closed` event.

        Hooked at 7MOJX.

        :param code: Close code.

        :param reason: Close reason.

        :return: None.
        """
        # Log message
        self._log_debug(
            '# ----- _meteor_closed_callback -----\nCode: {}\nReason: {}'
            .format(code, reason)
        )

        # Set the topic subscribing is done
        self._subscribing_done_event.set()

        # 3DMYH
        # Set the meteor client's `closed` event is emitted
        self._meteor_closed_event.set()

    def build_reply(self, mess, text=None, private=False, threaded=False):
        """
        Create reply message object.

        Used by `self.send_simple_reply`.

        :param mess: The original message object.

        :param text: Reply message text.

        :param private: Whether the reply message is private.

        :return: Message object.
        """
        # Create reply message object
        reply = Message(
            body=text,
            frm=mess.to,
            to=mess.frm,
            extras={
                # 5QXGV
                # Store the original message object
                'orig_msg': mess
            }
        )

        # Return reply message object
        return reply

    def prefix_groupchat_reply(self, message, identifier):
        """
        Add group chat prefix to the message.

        Used by `self.send` and `self.send_simple_reply`.

        :param message: Message object to send.

        :param identifier: The message receiver's identifier object.

        :return: None.
        """
        # Do nothing

    def send_rocketchat_message(self, params):
        """
        Send message to meteor server.

        :param params: RPC method `sendMessage`'s parameters.

        :return: None.
        """
        # If argument `params` is not list
        if not isinstance(params, list):
            # Put it in a list
            params = [params]

        # Send message to meteor server
        self._meteor_client.call(
            method='sendMessage',
            params=params,
        )

    def send_card(self, card: Card) -> None:
        """
        Send message to meteor server with an attachment.

        :param card: The information used to build the Rocket Chat attachment.
        :return: None
        """

        # Get original message info.
        #
        # The key is set at 2QTGO
        #
        msg_info = card.parent.extras['msg_info']

        # Get room ID
        room_id = msg_info['rid']

        attachment = {}
        if card.color:
            attachment['color'] = card.color

        if card.title:
            attachment['title'] = card.title

        if card.link:
            attachment['title_link'] = card.link

        if card.summary:
            attachment['text'] = card.summary

        if card.image:
            attachment['image_url'] = card.image

        if card.thumbnail:
            attachment['thumb_url'] = card.thumbnail

        if len(card.fields) > 0:
            fields = []
            for field in card.fields:
                fields.append({
                    'title': field[0],
                    'value': field[1]
                })
            attachment['fields'] = fields

        # Send message to meteor server
        self.send_rocketchat_message(params={
            'rid': room_id,
            'msg': card.body,
            'attachments': [
                attachment
            ]
        })

    def send_message(self, mess):
        """
        Send message to meteor server.

        Used by `self.split_and_send_message`. `self.split_and_send_message` is
        used by `self.send` and `self.send_simple_reply`.

        :param mess: Message object to send.

        :return: None.
        """
        # Call super method to dispatch to plugins
        super(RocketChat, self).send_message(mess)

        # Get original message object.
        #
        # The key is set at 5QXGV and 3YRCT.
        #
        orig_msg = mess.extras['orig_msg']

        # Get original message info.
        #
        # The key is set at 2QTGO
        #
        msg_info = orig_msg.extras['msg_info']

        # Get room ID
        room_id = msg_info['rid']

        # Send message to meteor server
        self.send_rocketchat_message(params={
            'rid': room_id,
            'msg': mess.body,
        })

    def send(
        self,
        identifier,
        text,
        in_reply_to=None,
        groupchat_nick_reply=False,
    ):
        """
        Send message to meteor server.

        :param identifier: Receiver's identifier object.

        :param text: Message text to send.

        :param in_reply_to: Original message object.

        :param groupchat_nick_reply: Whether the message to send is group chat.

        `self.prefix_groupchat_reply` will be called to process the message if
        it is group chat.

        :return: None.
        """
        # If the identifier object is not Identifier instance
        if not isinstance(identifier, Identifier):
            # Get message
            error_msg = (
                'Argument `identifier` is not Identifier instance: {}'
            ).format(repr(identifier))

            # Raise error
            raise ValueError(error_msg)

        # If the original message is not given, emulate receiving a message to confirm with.
        if in_reply_to is None:
            self.create_reply_msg(identifier, text)
            return True

        # Create message object
        msg_obj = Message(
            body=text,
            frm=in_reply_to.to,
            to=identifier,
            extras={
                # 3YRCT
                # Store the original message object
                'orig_msg': in_reply_to,
            },
        )

        # Get group chat prefix from config
        group_chat_prefix = self.bot_config.GROUPCHAT_NICK_PREFIXED

        # If the receiver is a room
        if isinstance(identifier, Room):
            # If have group chat prefix,
            # or the message is group chat.
            if group_chat_prefix or groupchat_nick_reply:
                # Call `prefix_groupchat_reply` to process the message
                self.prefix_groupchat_reply(msg_obj, in_reply_to.frm)

        # Send the message
        self.split_and_send_message(msg_obj)

    def create_reply_msg(self, identifier, text):
        def query_user_callback(*args, **kwargs):
            in_reply_to = Message(
                body=text,
                frm=identifier,
                to=self.bot_identifier,
                extras={"msg_info": args[1]}
            )
            # Re-enter send() method.
            self.send(identifier, text, in_reply_to)

        self._meteor_client.call(
            method="createDirectMessage",
            params=[identifier.person],
            callback=query_user_callback
        )

    def query_room(self, room):
        """
        Query room info. Not implemented.

        :param room: Room ID.

        :return: None.
        """
        # Return None
        return None

    def rooms(self):
        """
        Get room list. Not implemented.

        :return: Empty list.
        """
        # Return empty list
        return []

    def change_presence(self, status=ONLINE, message=''):
        """
        Change presence status. Not implemented.

        :param status: Presence status.

        :param message: Message text to send.

        :return: None.
        """
        # Do nothing
