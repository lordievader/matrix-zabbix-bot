#!/usr/bin/env python3
"""Author:      Olivier van der Toorn <oliviervdtoorn@gmail.com>
Description:    Zabbix bot responsible for !zabbix calls.
"""
import logging
import datetime
import argparse
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
    room_id = room.room_id.split(':')[0]
    logging.debug('got a message from room: %s', room_id)
    if room_id in config:
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
    zabbix_realm = config[room_id]
    zabbix_config = matrix.read_config(config['config'],
                                       zabbix_realm)
    logging.debug('using zabbix realm: %s\nconfig:\n%s',
                  zabbix_realm, zabbix_config)
    return zabbix_config


def flags():
    """Parses the arguments given.

    :return: dictionary of the arguments
    """
    parser = argparse.ArgumentParser(description='Zabbix bot for Matrix.')
    parser.add_argument('-c', '--config', type=str, dest='config',
                        default='/etc/matrix-zabbix-bot.conf',
                        help=('specifies the config file '
                              '(defaults to '
                              '/etc/matrix-zabbix-bot.conf)'))
    parser.add_argument('-d', '--debug', action='store_const', dest='debug',
                        const=True, default=False,
                        help='enables the debug output')
    return vars(parser.parse_args())


def colorize(trigger):
    """Colorizes the message based on their priority.

    :param messages: the messages to format
    :type messages: list
    :return: formatted messages
    """
    args = flags()
    config = matrix.read_config(args['config'], 'Zabbix-Bot')
    header = '<font color="{color}">'
    footer = '</font>'
    color = '#000000'

    level = trigger['priority'].lower()
    if level in config:
        color = config[level]
        logging.debug('found color: %s', color)

    else:
        color = '#000000'

    header = header.format(color=color)
    return (header, footer)


def zabbix_callback(room, event):
    """Callback function for the !zabbix matches.

    :param room: reference to the room
    :type room: room thingie
    :param event: the message, essentially
    :type event: event
    """
    try:
        room_id = room.room_id.split(':')[0]
        logging.debug('got a message from room: %s', room_id)
        if room_id in config:
            zabbix_realm = config[room_id]
            args = flags()
            zabbix_config = matrix.read_config(args['config'],
                                               zabbix_realm)
            logging.debug('using zabbix realm: %s\nconfig:\n%s',
                          zabbix_realm, zabbix_config)

        else:
            logging.warning('room_id is unknown')
            return

        args = event['content']['body'].split()
        args.pop(0)
        messages = []
        triggers = []
        hosts = []
        if len(args) == 0:
            triggers = zabbix.get_unacked_triggers(zabbix_config)

        elif len(args) == 1:
            arg = args[0]
            if arg == 'all':
                triggers = zabbix.get_triggers(zabbix_config)

            elif arg == 'acked':
                triggers = zabbix.get_acked_triggers(zabbix_config)

            elif arg == 'unacked':
                triggers = zabbix.get_unacked_triggers(zabbix_config)

            elif arg == 'ack':
                messages.append(('please call this trigger in the '
                                 'format of: !zabbix ack {trigger id}'))

            elif arg == 'hosts':
                hosts = zabbix.hosts(zabbix_config)

            elif arg == 'help':
                messages.append('hi')

        elif len(args) == 2:
            if args[0] == 'ack':
                triggerid = args[1]
                messages.append(zabbix.ack(zabbix_config, triggerid))

        if len(triggers) > 0:
            color_config = matrix.read_config(config['config'], 'Colors')
            for trigger in triggers:
                message = ("{prio} {name} {desc}: {value} "
                           "({triggerid})").format(
                    prio=trigger['priority'],
                    name=trigger['hostname'],
                    desc=trigger['description'],
                    value=trigger['prevvalue'],
                    triggerid=trigger['trigger_id'])
                formatted_message = matrix_alert.colorize(color_config, message)
                messages.append(formatted_message)

        if len(hosts) > 0:
            for host in hosts:
                messages.append(("{hostname} {description} status: "
                                 "{status} ({hostid})").format(
                    hostname=host['hostname'],
                    description=host['description'],
                    status=host['status'],
                    hostid=host['hostid']))

        if len(messages) == 0:
            messages.append('No triggers received')

        messages = "<br />".join(sorted(messages))
        matrix_config['message'] = messages
        matrix.send_message(matrix_config, room)

    except Exception as error:  # Keep running!
        logging.error(error, exc_info=True)


def _dnsjedi_help():
    """Returns the help text for the !dnsjedi command.
    """
    help_text = (
        "Usage: !dnsjedi {arguments}"
        "<br /><br />"
        "This command returns current statistics for dnsjedi measurements."
        "<br />"
        "Currently supported arguments:"
        "<br /><br />"
        "left: queries the clustermangers how many chunks are left"
        "<br />"
        "forecast: queries the prediction on when it is done"
        "<br /><br />"
        "Without any arguments this command gives a summary of "
        "the clustermanagers."
    )
    return help_text


def _dnsjedi_forecast_format(value):
    """Converts a forecast value string into a formatted string.

    :param value: seconds string
    :type value: str
    :return: formatted string
    """
    seconds = int(float(value))
    logging.debug(seconds)
    if seconds == 999999999999:
        time_left = "done in a long time"

    else:
        time_delta = datetime.timedelta(seconds=seconds)
        done = datetime.datetime.utcnow() + time_delta
        time_left = "done in about {0} ({1} UTC)".format(
            str(time_delta), done)

    return time_left


def _dnsjedi_chunks_summary(zabbix_config):
    """Returns a summary about the clustermanager chunks.

    :param zabbix_config: the zabbix configuration
    :type zabbix_config: dict
    :return: message to send back
    """
    lines = []
    clustermanagers = zabbix.get_itemvalues_for_group(
        zabbix_config, 'Clustermanagers',
        ['cms.chunks_left',
         'cms.co_queue_len_forecast',
         ])

    if clustermanagers is not None:
        for name, value in sorted(clustermanagers.items()):
            chunks_left = value[0]
            time_left = _dnsjedi_forecast_format(value[1])
            if chunks_left != '0':
                lines.append(
                    "{0}: {1} chunks left, {2}".format(
                        name, chunks_left, time_left))

            else:
                lines.append(
                    "{0}: done".format(name))
    return "<br />".join(lines)


def _dnsjedi_chunks_left(zabbix_config):
    """Returns the chunks left for each clustermanager.

    :param zabbix_config: the zabbix configuration
    :type zabbix_config: dict
    :return: message to send back
    """
    lines = []
    clustermanagers = zabbix.get_itemvalues_for_group(
        zabbix_config, 'Clustermanagers',
        ['cms.chunks_left',
         ])

    if clustermanagers is not None:
        for name, value in sorted(clustermanagers.items()):
            left = value[0]
            lines.append(
                "{0:10s}: {1:>5s} chunks left".format(
                    name, left))
    return "<br />".join(lines)


def _dnsjedi_chunks_forecast(zabbix_config):
    """Returns the chunks forecast for each clustermanager.

    :param zabbix_config: the zabbix configuration
    :type zabbix_config: dict
    :return: message to send back
    """
    lines = []
    clustermanagers = zabbix.get_itemvalues_for_group(
        zabbix_config, 'Clustermanagers',
        ['cms.co_queue_len_forecast',
         ])

    if clustermanagers is not None:
        for name, value in sorted(clustermanagers.items()):
            logging.debug('%s: %s', name, value[0])
            time_left = _dnsjedi_forecast_format(value[0])
            lines.append(
                "{0}: {1}".format(
                    name, time_left))
    return "<br />".join(lines)


def dnsjedi_callback(room, event):
    """Callback function for the !dnsjedi matches.

    :param room: reference to the room
    :type room: room thingie
    :param event: the message, essentially
    :type event: event
    """
    try:
        room_id, zabbix_config = _room_init(room)
        if room_id is None:
            return

        if room_id not in ['!OUZabccnPEwNGbzecZ', '!OTdomlClomfOdIOdOa']:
            return

        args = event['content']['body'].split()
        args.pop(0)

        if len(args) == 0:
            messages = _dnsjedi_chunks_summary(zabbix_config)

        elif len(args) == 1:
            arg = args[0]
            if arg == 'left':
                messages = _dnsjedi_chunks_left(zabbix_config)

            elif arg == 'forecast':
                messages = _dnsjedi_chunks_forecast(zabbix_config)

            else:
                messages = _dnsjedi_help()

        matrix_config['message'] = messages
        matrix.send_message(matrix_config, room)

    except Exception as error:  # Keep running!
        logging.error(error, exc_info=True)
        message = "{0}<br /><br />Please see my log.".format(
            str(error))
        matrix_config['message'] = message
        matrix.send_message(matrix_config, room)
        return


def main():
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

    # Add a !dnsjedi handler
    dnsjedi_handler = MRegexHandler("^!dnsjedi", dnsjedi_callback)
    bot.add_handler(dnsjedi_handler)

    # Start polling
    bot.start_polling()

    # Infinitely read stdin to stall main thread while the bot runs in other
    # threads
    while True:
        input()


if __name__ == "__main__":
    args = flags()
    if args['debug'] is True:
        set_log_level('DEBUG')

    else:
        set_log_level()

    zabbix.logging = logging
    matrix.logging = logging
    config = matrix.read_config(args['config'], 'Zabbix-Bot')
    config['config'] = args['config']
    matrix_config = matrix.read_config(args['config'], 'Matrix')
    logging.debug('config:\n%s', config)
    main()
