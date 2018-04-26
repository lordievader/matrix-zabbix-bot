#!/usr/bin/env python3
"""Author:      Olivier van der Toorn <oliviervdtoorn@gmail.com>
Description:    Simple wrapper around matrix-python-sdk. Makes sending messages
                to a Matrix room easy.

Matrix-Python-SDK: https://github.com/matrix-org/matrix-python-sdk
"""
import argparse
import configparser
import imp
import logging
import os
from matrix_client.client import MatrixClient


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
                        default='/etc/zabbix-bot.conf',
                        help=('specifies the config file '
                              '(defaults to /etc/matrix.conf)'))
    parser.add_argument('-t', '--type', type=str, dest='message_type',
                        help=('sets the message type'))
    parser.add_argument('-d', '--debug', action='store_const', dest='debug',
                        const=True, default=False,
                        help='enables the debug output')
    return vars(parser.parse_args())


def read_config(config_file, conf_section='Matrix'):
    """Reads a matrix config file.

    :param config_file: path to the config file
    :type config_file: str
    :param conf_section: section of the config file to read
    :type conf_section: str
    :return: config dictionary
    """
    config_file = os.path.expanduser(config_file)
    if os.path.isfile(config_file) is False:
        raise FileNotFoundError('config file "{0}" not found'.format(
            config_file))

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


def set_log_level(level='INFO'):
    """Sets the log level of the notebook. Per default this is 'INFO' but
    can be changed.

    :param level: level to be passed to logging (defaults to 'INFO')
    :type level: str
    """
    imp.reload(logging)
    logging.basicConfig(format='%(asctime)s: %(levelname)8s - %(message)s',
                        level=level)


if __name__ == '__main__':
    args = flags()
    args['message'] = " ".join(args['message'])
    if args['debug'] is True:
        set_log_level('DEBUG')

    else:
        set_log_level()

    try:
        config = merge_config(args, read_config(args['config']))

    except FileNotFoundError:
        config = args
        if None in [config['username'], config['password'], config['room']]:
            raise

    logging.debug('config: %s', config)

    client, room = setup(config)
    send_message(config, room)
