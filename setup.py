from setuptools import setup

setup(
    name='matrix-zabbix-bot',
    version='0.1',
    description='Bot for talking to the Zabbix API via Matrix.',
    author='Olivier van der Toorn',
    author_email='oliviervdtoorn@gmail.com',
    packages=['matrix-zabbix-bot'],
    install_requires=['matrix-bot-api', 'matrix-client', 'pyzabbix'],
)
