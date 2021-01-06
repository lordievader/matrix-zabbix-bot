#!/usr/bin/env python3
"""Author:      Olivier van der Toorn <oliviervdtoorn@gmail.com>
Description:    Simple script to login with a given username and password and
                return an access token.
"""
import os
import argparse
import logging
import configparser
import matrix
from matrix_client.client import MatrixClient


def flags():
    """Parses the arguments given.

    :return: dictionary of the arguments
    """
    parser = argparse.ArgumentParser(description='Python to Matrix bridge.')
    parser.add_argument('room', type=str, nargs='?',
                        help='room to deliver message to')
    parser.add_argument('-u', '--user', type=str, dest='username',
                        help='username to use (overrides the config)')
    parser.add_argument('-p', '--password', type=str, dest='password',
                        help='password to use (overrides the config)')
    parser.add_argument('-c', '--config', type=str, dest='config',
                        default='/etc/zabbix-bot.yaml',
                        help=('specifies the config file '
                              '(defaults to /etc/zabbix-bot.yaml)'))
    parser.add_argument('-t', '--type', type=str, dest='message_type',
                        help=('sets the message type'))
    parser.add_argument('-d', '--debug', action='store_const', dest='debug',
                        const=True, default=False,
                        help='enables the debug output')
    return vars(parser.parse_args())


def set_log_level(level='INFO'):
    """Sets the log level of the notebook. Per default this is 'INFO' but
    can be changed.

    :param level: level to be passed to logging (defaults to 'INFO')
    :type level: str
    """
    logging.basicConfig(format='%(asctime)s: %(levelname)8s - %(message)s',
                        level=level)


def get_token(config):
    """Returns a login token.
    """
    loginargs = {}
    client = MatrixClient("https://{0}:{1}".format(
        config['homeserver'], int(config['port'])), **loginargs)
    token = client.login(
        username=config['username'],
        password=config['password'],
        device_id='zabbixbot'
    )
    logging.info("Authenticated, add the following to your config:\ntoken: %s", token)
    return token


if __name__ == '__main__':
    args = flags()
    if args['debug'] is True:
        set_log_level('DEBUG')

    else:
        set_log_level()

    try:
        config = matrix.merge_config(args, matrix.read_config(args['config']))

    except FileNotFoundError:
        config = args
        if None in [config['username'], config['password'], config['room']]:
            raise

    logging.debug('config: %s', config)
    get_token(config['matrix'])
