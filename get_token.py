#!/usr/bin/env python3
"""Author:      Olivier van der Toorn <oliviervdtoorn@gmail.com>
Description:    Simple script to login with a given username and password and
                return an access token.
"""
import os
import imp
import argparse
import logging
import configparser
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

    if 'domain' not in config:
        config['domain'] = config['homeserver']

    return config


def set_log_level(level='INFO'):
    """Sets the log level of the notebook. Per default this is 'INFO' but
    can be changed.

    :param level: level to be passed to logging (defaults to 'INFO')
    :type level: str
    """
    imp.reload(logging)
    logging.basicConfig(format='%(asctime)s: %(levelname)8s - %(message)s',
                        level=level)


def get_token(config):
    """Returns a login token.
    """
    loginargs = {}
    client = MatrixClient("https://{0}:{1}".format(
        config['homeserver'], int(config['port'])), **loginargs)
    token = client.login_with_password(
        username=config['username'], password=config['password'])
    logging.info("Authenticated, add the following to your config:\n token = %s", token)
    return token


if __name__ == '__main__':
    args = flags()
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
    get_token(config)
