#!/usr/bin/env python3
"""Author:      Olivier van der Toorn <oliviervdtoorn@gmail.com>
Description:    Simple wrapper around matrix-python-sdk. Makes sending messages
                to a Matrix room easy.

Matrix-Python-SDK: https://github.com/matrix-org/matrix-python-sdk
"""
import os
import sys
import re
import argparse
import configparser
from matrix_client.api import MatrixHttpApi
from matrix_client.client import MatrixClient

import log

def flags():
    """Parses the arguments given.

    :return: dictionary of the arguments
    """
    parser = argparse.ArgumentParser(description='Python to Matrix bridge.')
    parser.add_argument('room', type=str, nargs='?',
                        help='room to deliver message to')
    parser.add_argument('message', type=str, nargs='+',
                                help='the message to Matrix')
    parser.add_argument('-u', '--user', type=str, dest='username',
                        help='username to use (overrides the config)')
    parser.add_argument('-p', '--password', type=str, dest='password',
                        help='password to use (overrides the config)')
    parser.add_argument('-c', '--config', type=str, dest='config',
                        default='/etc/matrix.conf',
                        help=('specifies the config file '
                              '(defaults to /etc/matrix.conf)')) 
    parser.add_argument('-t', '--type', type=str, dest='message_type',
                        help=('sets the message type'))
    parser.add_argument('-d', '--debug', action='store_const', dest='debug',
                        const=True, default=False,
                        help='enables the debug output')

    args = parser.parse_args()
    if args.config and (args.username or args.password):
        print("-c and -u|-p are mutually exclusive")
        sys.exit(2)

    return vars(parser.parse_args())

def read_config(config_file, conf_section='Matrix'):
    """Reads a matrix config file.

    :param config_file: path to the config file
    :type config_file: str
    :param conf_section: section of the config file to read
    :type conf_section: str
    :return: config dictionary
    """
    if os.path.isfile(config_file) is False:
        print('config file "{0}" not found'.format(config_file))
        sys.exit(19)

    config = configparser.ConfigParser()
    config.optionxform = str
    config.read(config_file)
    return {key: value for key, value in config[conf_section].items()}

def merge_config(args, config):
    """This function merges the args and the config together.
    The command line arguments are prioritized over the configured values.

    :param args: command line arguments
    :type args: dict
    :param config: option from the config file
    :type config: dict
    :return: dict with values merged
    """
    for key, value in args.items():
        if value is not None:
            config[key] = value

    return config

def setup(config):
    """Sets up the Matrix client. Makes sure the (specified) room is joined.
    """
    client = MatrixClient("https://{0}:{1}".format(
        config['homeserver'], int(config['port'])))
    client.login_with_password(
        username=config['username'], password=config['password'])
    room = client.join_room('{0}:{1}'.format(
        config['room'], config['homeserver']))
    return client, room

def send_message(config, room):
    """Sends a message into the room. The config dictionary hold the message.

    :param config: config dictionary
    :type config: dictionary
    :param room: reference to the Matrix room
    :type room: MatrixClient.room
    """
    message = config['message']
    logging.debug('sending message:\n%s', message)
    room.send_html(message, msgtype=config['message_type'])

if __name__ == '__main__':
    args = flags()
    args['message'] = " ".join(args['message'])
    if args['debug'] is True:
        log.set_log_level('DEBUG')

    else:
        log.set_log_level()

    logging = log.logging
    config = merge_config(args, read_config(args['config']))
    logging.debug('config: %s', config)
    client, room = setup(config)
    send_message(config, room)
    #message = break_line(message)
    #message = zabbix(message)
    #send_html(room, message)
