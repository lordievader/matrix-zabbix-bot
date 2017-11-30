#!/usr/bin/env python3
"""Author:      Olivier van der Toorn <oliviervdtoorn@gmail.com>
Description:    Zabbix bot responsible for !zabbix calls.
"""
import argparse
import imp
import logging
import sys
from matrix_bot_api.matrix_bot_api import MatrixBotAPI
from matrix_bot_api.mregex_handler import MRegexHandler
from matrix_bot_api.mcommand_handler import MCommandHandler

import zabbix
import matrix
from matrix import set_log_level

def flags():
    """Parses the arguments given.

    :return: dictionary of the arguments
    """
    parser = argparse.ArgumentParser(description='Zabbix bot for Matrix.')
    parser.add_argument('-c', '--config', type=str, dest='config',
                        default='/etc/matrix-zabbix-bot.conf',
                        help=('specifies the config file '
                              '(defaults to /etc/matrix-zabbix-bot.conf)')) 
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
            for trigger in triggers:
                header, footer = colorize(trigger)
                messages.append(("{header}{prio} {name} {desc}: {value} "
                                 "({triggerid}){footer}").format(
                    header=header,
                    prio=trigger['priority'],
                    name=trigger['hostname'],
                    desc=trigger['description'],
                    value=trigger['prevvalue'],
                    triggerid=trigger['trigger_id'],
                    footer=footer))

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

    except Exception as error: # Keep running!
        logging.error(error, exc_info=True)

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

    # Start polling
    bot.start_polling()

    # Infinitely read stdin to stall main thread while the bot runs in other threads
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
    matrix_config = matrix.read_config(args['config'])
    logging.debug('config:\n%s', config)
    main()
