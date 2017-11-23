# Matrix Zabbix bot
This is a simple project of making the Zabbix API available into Matrix.

For this the pyzabbix[1] and the matrix-python-sdk[2] are used.

Currently only the Matrix SDK wrapper is available. This script makes sending
messages to a Matrix room easier. For example:

`python3 matrix.py -c matrix_example.conf Hello I am a test message`

Send a test message to the room configured in the matrix_example.conf file.

[1]: https://github.com/lukecyca/pyzabbix
[2]: https://github.com/matrix-org/matrix-python-sdk
