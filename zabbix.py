#!/usr/bin/env python3
import os
import re
import configparser
import pprint
import argparse
from pyzabbix import ZabbixAPI

import log

PRIORITY = {
        0: 'Not classified',
        1: 'Information',
        2: 'Warning',
        3: 'Average',
        4: 'High',
        5: 'Disaster',
}

def flags():
    parser = argparse.ArgumentParser(description=('Python wrapper around '
                                                  'the Zabbix API.'))
    parser.add_argument('-c', '--config', type=str, dest='config',
                        nargs='+', default='/etc/zabbix/api.conf',
                        help=('specifies the config file '
                              'the second argument specifies the section in '
                              'the configuration file '
                              '(defaults to /etc/zabbix/api.conf'
                              ' section defaults to "Zabbix")')) 
    parser.add_argument('-d', '--debug', action='store_const', dest='debug',
                        const=True, default=False,
                        help='enables the debug output')
    parser.add_argument('--show_all', action='store_const',
                        dest='show_all', const=True, default=False,
                        help='show all triggers, acked and unacked')
    parser.add_argument('--show_acked', action='store_const',
                        dest='show_acked', const=True, default=False,
                        help='show only acked triggers')
    parser.add_argument('--ack', '-a', nargs=1)
    return vars(parser.parse_args())

def read_config(config_file, section):
    """Read a zabbix-matrix config file.

    :param config_file: config file to read
    :type config_file: str
    :param section: section to read from the config file
    :type section: str
    :return: config dictionary
    """
    if os.path.isfile(config_file) is False:
        logging.error('config file "%s" not found', config_file)

    config = configparser.ConfigParser()
    config.read(config_file)
    return {key: value for key, value in config[section].items()}

def init(config):
    """Initializes the ZabbixAPI with the config.

    :param config: config to use, as returned by read_config
    :type config: dict
    :return: ZabbixAPI reference
    """
    logging.debug(config)
    zapi = ZabbixAPI(config['host'])
    zapi.login(config['username'], config['password'])
    return zapi

def trigger_info(zapi, trigger):
    """Retrieves the description, hostname, prevvalue and trigger_id for a 
    given trigger.

    :param zapi: reference to the ZabbixAPI
    :type zapi: ZabbixAPI
    :param trigger: dictionary of retrieved trigger
    :type trigger: dict
    :return: description, hostname, prevvalue, trigger_id
    """
    trigger_id = trigger['triggerid']
    priority = PRIORITY[int(trigger['priority'])]
    item = zapi.item.get(triggerids=trigger_id)[0]
    hostid = item['hostid']
    prevvalue = item['prevvalue']
    hostname = zapi.host.get(hostids=hostid)[0]['name']
    description = trigger['description']
    logging.debug('%s: %s, previous value: %s (trigger id: %s)', hostname, description, prevvalue, trigger_id)
    return {'hostname': hostname,
            'description': description,
            'priority': priority,
            'prevvalue': prevvalue, 
            'trigger_id': trigger_id}

def get_triggers(config):
    """Retrieves all the triggers from Zabbix

    :param config: config for zapi
    :type config: dict
    :return: list of triggers
    """
    zapi = init(config)
    all_triggers = zapi.trigger.get(only_true=1,
                                skipDependent=1,
                                monitored=1,
                                active=1,
                                output='extend',
                                expandDescription=1)
    triggers = []
    for trigger in all_triggers:
        if trigger['value'] == '1':
            triggers.append(trigger_info(zapi, trigger))

    return triggers

def get_unacked_triggers(config):
    """Retrieves the unacked triggers from Zabbix.

    :param config: config for zapi
    :type config: dict
    :return: list of triggers
    """
    zapi = init(config)
    all_triggers = zapi.trigger.get(only_true=1,
                                skipDependent=1,
                                monitored=1,
                                active=1,
                                output='extend',
                                expandDescription=1,
                                withLastEventUnacknowledged=1)
    triggers = []
    for trigger in all_triggers:
        if trigger['value'] == '1':
            triggers.append(trigger_info(zapi, trigger))

    return triggers

def get_acked_triggers(config):
    """Retrieves the acked triggers from Zabbix.

    :param config: config for zapi
    :type config: dict
    :return: list of triggers
    """
    all_triggers = get_triggers(config)
    unacked_triggers = get_unacked_triggers(config)
    triggers = []
    for trigger in all_triggers:
        if trigger not in unacked_triggers:
            triggers.append(trigger)

    return triggers

if __name__ == '__main__':
    args = flags()
    if args['debug'] is True:
        log.set_log_level('DEBUG')

    else:
        log.set_log_level()

    logging = log.logging
    logging.debug(args)

    if len(args['config']) == 1:
        args['config'].append('Zabbix')

    config = read_config(*args['config'])
    logging.debug('configuration:\n%s', config)

    triggers = []
    if args['show_acked'] is True:
        triggers = get_acked_triggers(config)

    elif args['show_all'] is True:
        triggers = get_triggers(config)

    # Todo: future work, support acking through bot
    # elif args['ack'] is not None:
    #     messages = ack_trigger(args['ack'], config)

    elif args['show_acked'] is False and args['show_all'] is False:
        triggers = get_unacked_triggers(config)

    pprint.pprint(triggers)
