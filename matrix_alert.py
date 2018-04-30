#!/usr/bin/env python3
"""Author:      Olivier van der Toorn <oliviervdtoorn@gmail.com>
Description:    Zabbix alert script for matrix.
This script expects the `matrix_zabbix_bot' import is available.
"""
import re
import logging
from matrix_zabbix_bot import matrix


def colorize(color_config, message):
    """Colorize a message based upon the severity of the message.

    :param color_config: the color configuration
    :type color_config: dict
    :param message: the message to color
    :type message: str
    :return: colorized message
    """
    for level, color in color_config.items():
        regex = re.compile('^{0}[:\s].*'.format(level), re.IGNORECASE)
        if regex.match(message):
            color, emoji = color.split(',')
            break

    else:
        color, emoji = color_config['not classified'].split(',')

    formatted_message = '<font color=\"{0}\">{1} {2}</font>'.format(
        color, emoji, message)
    return formatted_message


if __name__ == '__main__':
    args = matrix.flags()
    args['message'] = " ".join(args['message'])
    if args['debug'] is True:
        matrix.set_log_level('DEBUG')

    else:
        matrix.set_log_level()

    try:
        config = matrix.merge_config(args, matrix.read_config(args['config']))

    except FileNotFoundError:
        config = args
        if None in [config['username'], config['password'], config['room']]:
            raise

    color_config = matrix.read_config(args['config'], 'Colors')

    logging.debug(color_config)
    config['message'] = colorize(color_config, config['message'])
    client, room = matrix.setup(config)
    matrix.send_message(config, room)
