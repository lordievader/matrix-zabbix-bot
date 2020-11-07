# Matrix Zabbix bot
This is a simple project of making the Zabbix API available into Matrix.

For this the [pyzabbix][1] and the [matrix-python-sdk][2] are used.

## Matrix SDK wrapper
The Matrix SDK wrapper script makes sending
messages to a Matrix room easier. For example:

`python3 matrix.py -c matrix_example.yaml Hello I am a test message`

Sends a test message to the room configured in the matrix_example.yaml file.

## Zabbix API wrapper
While the pyzabbix itself is a wrapper, I wrote a wrapper for pyzabbix to make
the code for the bot itself easier. In the `zabbix.py` file all the
functions for retrieving the triggers and acknowledging them are defined.

## Matrix Zabbix bot
The actual bot is defined in `zabbix_bot.py`. This bot listens for any message
beginning with `!zabbix`. Without any argument it lists the unacknowledged
triggers. `!zabbix all` list all triggers, acknowledged and unacknowledged.
`!zabbix acked` lists only the acknowledged triggers.
The format of each trigger line is:

`{priority} {hostname} {description} {lastvalue} ({trigger-id})`

This trigger-id can be used to acknowledge triggers by issuing:

`!zabbix ack {trigger-id}`

[1]: https://github.com/lukecyca/pyzabbix
[2]: https://github.com/matrix-org/matrix-python-sdk
