"""Provides logging functions
"""
import imp
import logging
def set_log_level(level='INFO'):
    """Sets the log level of the notebook. Per default this is 'INFO' but
    can be changed.

    :param level: level to be passed to logging (defaults to 'INFO')
    :type level: str
    """
    imp.reload(logging)
    logging.basicConfig(format='%(asctime)s: %(levelname)8s - %(message)s',
                        level=level)
