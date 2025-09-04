#!/usr/bin/env python3
##
## This code and all components (c) Copyright 2006 - 2025, Wowza Media Systems, LLC. All rights reserved.
## This code is licensed pursuant to the Wowza Public License version 1.0, available at www.wowza.com/legal.
##

"""Functions for sending and receiving individual lines of text over a socket.

A line is transmitted using one or more fixed-size packets of UTF-8 bytes
containing:

  - Zero or more bytes of UTF-8, excluding \n and \0, followed by

  - Zero or more \0 bytes as required to pad the packet to PACKET_SIZE

Originally from the UEDIN team of the ELITR project. 
"""

PACKET_SIZE = 65536


def send_one_line(socket, text, pad_zeros=False):
    """Sends a line of text over the given socket.

    The 'text' argument should contain a single line of text (line break
    characters are optional). Line boundaries are determined by Python's
    str.splitlines() function [1]. We also count '\0' as a line terminator.
    If 'text' contains multiple lines then only the first will be sent.

    If the send fails then an exception will be raised.

    [1] https://docs.python.org/3.5/library/stdtypes.html#str.splitlines

    Args:
        socket: a socket object.
        text: string containing a line of text for transmission.
    """
    text.replace('\0', '\n')
    lines = text.splitlines()
    first_line = '' if len(lines) == 0 else lines[0]
    # TODO Is there a better way of handling bad input than 'replace'?
    data = first_line.encode('utf-8', errors='replace') + b'\n' + (b'\0' if pad_zeros else b'')
    for offset in range(0, len(data), PACKET_SIZE):
        bytes_remaining = len(data) - offset
        if bytes_remaining < PACKET_SIZE:
            padding_length = PACKET_SIZE - bytes_remaining
            packet = data[offset:] + (b'\0' * padding_length if pad_zeros else b'')
        else:
            packet = data[offset:offset+PACKET_SIZE]
        socket.sendall(packet)


