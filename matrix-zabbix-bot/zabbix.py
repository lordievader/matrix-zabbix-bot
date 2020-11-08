#!/usr/bin/env python3
"""Author:      Olivier van der Toorn <oliviervdtoorn@gmail.com>
Description:    Wrapper around pyzabbix for use in the matrix-zabbix-bot.
"""
import argparse
import configparser
import logging
import os
import pprint
import re
from pyzabbix import ZabbixAPI, ZabbixAPIException
from matrix import set_log_level

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
    parser.add_argument('-r', '--realm', type=str, dest='realm',
                        nargs='+', default='home',
                        help=('specifies the realm of which Zabbix server '
                              'to use'))
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
    description = re.sub('({HOST.HOST}|{HOST.NAME})',
                         hostname,
                         trigger['description'])
    logging.debug('%s: %s, previous value: %s (trigger id: %s)',
                  hostname, description, prevvalue, trigger_id)
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
    return [trigger_info(zapi, trigger) for trigger in all_triggers]


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


def ack(config, triggerid):
    """Ack the given trigger id.

    :param config: config for zapi
    :type config: dict
    :param triggerid: id of the trigger to ack
    :type triggerid: str
    """
    zapi = init(config)
    event = zapi.event.get(objectids=triggerid)
    try:
        msg = zapi.event.acknowledge(
            eventids=event[-1]['eventid'],
            action=2,
            message='Acknowledged by the Matrix-Zabbix bot')
        return_string = "Trigger {0} acknowledged. {1}".format(
            triggerid, msg)

    except ZabbixAPIException as error:
        return_string = str(error)

    return return_string

def hosts(config):
    """Retrieves the monitored hosts.

    :param config: config for zapi
    :type config: dict
    """
    zapi = init(config)
    info = zapi.host.get(monitored=True)
    hosts = []
    pprint.pprint(hosts)
    for host in info:
        hosts.append({'hostname': host['name'],
                         'description': host['description'],
                         'status': host['status'],
                         'hostid': host['hostid']})

    return hosts

def _hostgroup_to_id(zapi, hostgroup):
    """Retrieves the hostgroup id for a given group.

    :param zapi: reference to the zabbix api
    :type zapi: zabbix api
    :param hostgroup: specifies the host group
    :type hostgroup: str
    :return: list of hosts
    """
    groups = zapi.hostgroup.get(monitored_hosts=True)
    for group in groups:
        if group['name'] == hostgroup:
            groupid = group['groupid']
            break

    else:
        groupid = None

    return groupid


def _get_hosts_in_groups(zapi, hostgroup):
    """Retrieves the hosts from a specific group.

    :param config: config for zapi
    :type config: dict
    :param hostgroup: specifies the host group
    :type hostgroup: str
    :return: list of hosts
    """
    groupid = _hostgroup_to_id(zapi, hostgroup)
    if groupid is None:
        return

    hosts = zapi.host.get(groupids=groupid)
    return hosts


def get_hosts_in_groups(config, hostgroup):
    """Retrieves the hosts from a specific group.

    :param config: config for zapi
    :type config: dict
    :param hostgroup: specifies the host group
    :type hostgroup: str
    :return: list of hosts
    """
    zapi = init(config)
    return _get_hosts_in_groups(zapi, hostgroup)


def _get_itemvalue(zapi, hostid, keys):
    """Retrieves the value for a hostid - key combination.

    :param zapi: the zabbix api reference
    :type zapi: zapi
    :param hostid: the id of the host
    :type hostid: str
    :param keys: keys to retrieve
    :type keys: str or list
    """
    if isinstance(keys, str):
        keys = [keys]

    data = []
    for key in keys:
        value = zapi.item.get(hostids=hostid, search={'key_': key})
        if value:
            data.append(value[0]['lastvalue'])

    return data


def get_itemvalue(config, host, keys):
    """Retrieves the value for a host - key combination.

    :param config: config for zapi
    :type config: dict
    :param host: host to query for
    :type host: dict
    :param keys: keys to retrieve
    :type keys: string or list
    """
    zapi = init(config)
    return _get_itemvalue(zapi, host['hostid'], keys)


def get_itemvalues_for_group(config, hostgroup, keys):
    """Retrieves the key for an entire group.

    :param config: config for zapi
    :type config: dict
    :param hostgroup: hostgroup to query for
    :type hostgroup: str
    :param keys: keys to retrieve
    :type keys: string or list
    """
    data = {}
    zapi = init(config)
    hosts = _get_hosts_in_groups(zapi, hostgroup)
    if hosts is not None:
        for host in hosts:
            value = _get_itemvalue(zapi, host['hostid'], keys)
            data[host['name']] = value

    return data


if __name__ == '__main__':
    args = flags()
    if args['debug'] is True:
        set_log_level('DEBUG')

    else:
        set_log_level()

    logging.debug(args)

    config = read_config(args['config'], args['realm'])
    logging.debug('configuration:\n%s', config)

    values = get_itemvalues_for_group(
        config, 'Clustermanagers',
        ['cms.chunks_left', 'agent.ping'])
    for name, value in sorted(values.items()):
        print("{0:10s}: {1}".format(name, value))

    # triggers = []
    # if args['show_acked'] is True:
    #     triggers = get_acked_triggers(config)

    # elif args['show_all'] is True:
    #     triggers = get_triggers(config)

    # # Todo: future work, support acking through bot
    # # elif args['ack'] is not None:
    # #     messages = ack_trigger(args['ack'], config)

    # elif args['show_acked'] is False and args['show_all'] is False:
    #     triggers = get_unacked_triggers(config)

    # pprint.pprint(triggers)
