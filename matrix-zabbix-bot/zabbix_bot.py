#!/usr/bin/env python3
"""Author:      Olivier van der Toorn <oliviervdtoorn@gmail.com>
Description:    Zabbix bot responsible for !zabbix calls.
"""
import argparse
import datetime
import logging
import time
import yaml
from matrix_bot_api.matrix_bot_api import MatrixBotAPI
from matrix_bot_api.mregex_handler import MRegexHandler

import zabbix
import matrix
import matrix_alert
from matrix import set_log_level


def _room_init(room):
    """Boilerplate code for identifying the room.

    :param room: reference to the room
    :type room: matrix room object
    :return: room_id, zabbix_config
    """
    room_id = room.room_id
    logging.debug('got a message from room: %s', room_id)
    if room_id in config['zabbix-bot']:
        zabbix_config = _zabbix_config(room_id)

    else:
        raise RuntimeError('room_id "{0}" is unkown'.format(room_id))

    return (room_id, zabbix_config)


def _zabbix_config(room_id):
    """Returns the zabbix configuration for a given room_id.

    :param room_id: the Matrix room id
    :type room_id: str
    :return: zabbix config directionary
    """
    zabbix_realm = config['zabbix-bot'][room_id]
    zabbix_config = config['zabbix'][zabbix_realm]
    logging.debug('using zabbix realm: %s\nconfig:\n%s',
                  zabbix_realm, zabbix_config)
    return zabbix_config


def _error(matrix_config, room, error):
    """Error handling function. Prints a traceback to the log and the
    title of the error is returned to matrix.

    :param matrix_config: the matrix configuration
    :type matrix_config: dict
    :param room: matrix room reference
    :type room: matrix room object
    :param error: reference to the exception
    :type error: exception
    """
    logging.error(error, exc_info=True)
    message = "{0}<br /><br />Please see my log.".format(
        str(error))
    matrix_config['message'] = message
    matrix.send_message(matrix_config, room)


def _zabbix_help():
    """Returns the help text for the !zabbix command.
    """
    help_text = (
        "Usage: !zabbix {arguments}"
        "<br /><br />"
        "This command returns info about Zabbix (triggers mostly)."
        "<br />"
        "Currently supported arguments:"
        "<br /><br />"
        "help: shows this message"
        "<br />"
        "all: retrieves all triggers"
        "<br />"
        "acked: retrieves acked triggers"
        "<br />"
        "unacked: retrieves unacked triggers"
        "<br />"
        "ack $trigger_id: acknowledges the trigger with the given id "
        "(the number between brackets)"
        "<br /><br />"
        "Without any arguments this command gives unacknowledged "
        "triggers from the configured Zabbix server."
    )
    return help_text


def _zabbix_unacked_triggers(zabbix_config):
    """Retrieves the unacked triggers from zabbix.

    :param zabbix_config: zabbix configuration
    :type zabbix_config: dict
    :return: messages to return to matrix
    """
    messages = []
    triggers = zabbix.get_unacked_triggers(zabbix_config)
    color_config = {}
    for key, value in matrix.read_config(config['config'])['colors'].items():
        if key.startswith('zabbix'):
            key = key.replace('zabbix_', '')
            color_config[key] = value

    for trigger in triggers:
        message = ("{prio} {name} {desc}: {value} "
                   "({triggerid})").format(
            prio=trigger['priority'],
            name=trigger['hostname'],
            desc=trigger['description'],
            value=trigger['prevvalue'],
            triggerid=trigger['trigger_id'])
        formatted_message = matrix_alert.colorize(
            color_config, message)
        messages.append(formatted_message)

    return "<br />".join(messages)


def _zabbix_acked_triggers(zabbix_config):
    """Retrieves the acked triggers from zabbix.

    :param zabbix_config: zabbix configuration
    :type zabbix_config: dict
    :return: messages to return to matrix
    """
    messages = []
    triggers = zabbix.get_acked_triggers(zabbix_config)
    color_config = {}
    for key, value in matrix.read_config(config['config'], 'Colors').items():
        if key.startswith('zabbix'):
            key = key.replace('zabbix_', '')
            color_config[key] = value

    for trigger in triggers:
        message = ("{prio} {name} {desc}: {value} "
                   "({triggerid})").format(
            prio=trigger['priority'],
            name=trigger['hostname'],
            desc=trigger['description'],
            value=trigger['prevvalue'],
            triggerid=trigger['trigger_id'])
        formatted_message = matrix_alert.colorize(
            color_config, message)
        messages.append(formatted_message)

    return "<br />".join(messages)


def _zabbix_all_triggers(zabbix_config):
    """Retrieves the all triggers from zabbix regardless of their
    status.

    :param zabbix_config: zabbix configuration
    :type zabbix_config: dict
    :return: messages to return to matrix
    """
    messages = []
    triggers = zabbix.get_triggers(zabbix_config)
    color_config = {}
    for key, value in matrix.read_config(config['config'], 'Colors').items():
        if key.startswith('zabbix'):
            key = key.replace('zabbix_', '')
            color_config[key] = value

    for trigger in triggers:
        message = ("{prio} {name} {desc}: {value} "
                   "({triggerid})").format(
            prio=trigger['priority'],
            name=trigger['hostname'],
            desc=trigger['description'],
            value=trigger['prevvalue'],
            triggerid=trigger['trigger_id'])
        formatted_message = matrix_alert.colorize(
            color_config, message)
        messages.append(formatted_message)

    return "<br />".join(messages)


def _zabbix_acknowledge_trigger(zabbix_config, trigger_id):
    """Acknowledges a trigger with the given id.

    :param zabbix_config: zabbix configuration
    :type zabbix_config: dict
    :param trigger_id: id to acknowledge
    :type trigger_id: int
    :return: messages to return to matrix
    """
    messages = []
    messages.append(zabbix.ack(zabbix_config, trigger_id))
    return "<br />".join(messages)


def zabbix_callback(room, event):
    """Callback function for the !zabbix matches.

    :param room: reference to the room
    :type room: room thingie
    :param event: the message, essentially
    :type event: event
    """
    try:
        room_id, zabbix_config = _room_init(room)
        if room_id is None:
            return

        args = event['content']['body'].split()
        args.pop(0)
        messages = []
        if len(args) == 0:
            messages = _zabbix_unacked_triggers(zabbix_config)

        elif len(args) == 1:
            arg = args[0]
            if arg == 'all':
                messages = _zabbix_all_triggers(zabbix_config)

            elif arg == 'acked':
                messages = _zabbix_acked_triggers(zabbix_config)

            elif arg == 'unacked':
                messages = _zabbix_unacked_triggers(zabbix_config)

        #     elif arg == 'hosts':
        #         hosts = zabbix.hosts(zabbix_config)

            else:
                messages = _zabbix_help()

        elif len(args) == 2:
            if args[0] == 'ack':
                trigger_id = args[1]
                messages = _zabbix_acknowledge_trigger(
                    zabbix_config, trigger_id)

            else:
                messages = _zabbix_help()

        else:
            messages = _zabbix_help()

        if len(messages) == 0:
            messages = 'Nothing to notify'

        matrix_config['message'] = messages
        matrix.send_message(matrix_config, room)

    except Exception as error:  # Keep running!
        return _error(matrix_config, room, error)


def flags():
    """Parses the arguments given.

    :return: dictionary of the arguments
    """
    parser = argparse.ArgumentParser(description='Zabbix bot for Matrix.')
    parser.add_argument('-c', '--config', type=str, dest='config',
                        default='/etc/zabbix-bot.yaml',
                        help=('specifies the config file '
                              '(defaults to '
                              '/etc/zabbix-bot.yaml)'))
    parser.add_argument('-d', '--debug', action='store_const', dest='debug',
                        const=True, default=False,
                        help='enables the debug output')
    return vars(parser.parse_args())


def main():
    """Main function.
    """
    zabbix.logging = logging
    matrix.logging = logging
    config['config'] = args['config']
    logging.debug('config:\n%s', config)

    # Create an instance of the MatrixBotAPI
    logging.debug('matrix config:\n%s', matrix_config)
    homeserver = "https://{server}:{port}".format(
        server=matrix_config['homeserver'], port=int(matrix_config['port']))
    bot = MatrixBotAPI(
        matrix_config['username'],
        matrix_config['password'],
        homeserver)

    # Add a !zabbix handler
    zabbix_handler = MRegexHandler("^!zabbix", zabbix_callback)
    bot.add_handler(zabbix_handler)

    # Start polling
    while True:
        thread = bot.start_polling()
        thread.join()
        logging.warning(
            'thread died, waiting five seconds before connecting again...')
        time.sleep(5)


if __name__ == "__main__":
    # TODO: Move out of global scope
    # while accesible to callback functions.
    args = flags()
    if args['debug'] is True:
        set_log_level('DEBUG')

    else:
        set_log_level()

    config = matrix.read_config(args['config'])
    matrix_config = config['matrix']

    main()
