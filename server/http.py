#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright 2014-2015 jeffZhuo
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

from __future__ import absolute_import
from __future__ import division
from __future__ import generators
from __future__ import nested_scopes
from __future__ import print_function
from __future__ import unicode_literals
from __future__ import with_statement

from server.io_multiplex import IOMultiplex

import errno
import socket

from server.log import logging

try:
    import cStringIO as StringIO
except (Exception, ):
    import StringIO

server_software = "Test Server"


class WSGIServer(object):

    server_software = "Test Server"

    def __init__(self, handler, host=None, port=None):
        self.host = host
        self.port = port
        self.handler = handler

        self.server_name = ""

        self.__socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        self.base_environ = {}

        if host is not None and port is not None:
            self.__socket.bind((host, port))
            self.server_name = socket.getfqdn(host)
            self.setup_environ()

        self.__socket.listen(5)

        self.running = False

        self.application = None

        self.multiplex = IOMultiplex.initialized()

        self.connection_list = {}
        self.response_list = {}

    def start(self):

        self.multiplex.add_handler(fd=self.__socket.fileno(), handler=self.handle_connection,
                                   eventmask=IOMultiplex.READ)
        # while True:
        #
        #     accepted = False
        #     try:
        #         conn, addr = self.__socket.accept()
        #         accepted = True
        #     except socket.error as ex:
        #         # (errno, string)
        #         if ex[0] in (errno.EWOULDBLOCK,):
        #             pass
        #         else:
        #             raise
        #
        #     if accepted:
        #         rfile = conn.makefile("rb")
        #         wfile = conn.makefile("wb")
        #         request_handler = self.handler(self, rfile, wfile, addr)
        #
        #         request_handler.handle_one_request()
        #         conn.close()

    def handle_connection(self, fd, event):
        try:
            conn, addr = self.__socket.accept()
            conn.setblocking(0)
            self.connection_list[conn.fileno()] = (conn, addr)
            self.multiplex.add_handler(fd=conn.fileno(), handler=self.handle_read_request, eventmask=IOMultiplex.READ)
        except socket.error as ex:
            print(ex)
            if ex[0] in (errno.EWOULDBLOCK,):
                pass
            else:
                raise

    def handle_read_request(self, fd, event):
        """ Temporarily function """
        conn, addr = self.connection_list[fd]
        rfile = conn.makefile("rb")
        wfile = conn.makefile("wb")
        request_handler = self.handler(self, rfile, wfile, addr)
        response = request_handler.handle_one_request()
        self.multiplex.remove_handler(fd)

        self.response_list[fd] = response
        self.multiplex.add_handler(fd=fd, handler=self.hanlde_write_response, eventmask=IOMultiplex.WRITE)

    def hanlde_write_response(self, fd, event):
        conn, addr = self.connection_list[fd]
        wfile = conn.makefile("wb")
        response = self.response_list[fd]
        if response is not None:
            response.set_wfile(wfile)
            response.handle_response()
        else:
            print(response)

        del self.response_list[fd]
        self.multiplex.remove_handler(fd)

        # self.multiplex.add_handler(fd=conn.fileno(), handler=self.handle_read_request, eventmask=IOMultiplex.READ)

    def bind(self, host, port):
        """ Bind host and port to server socket """
        if self.running is False:
            self.__socket.bind((host, port))
            self.server_name = socket.getfqdn(host)
            self.setup_environ()

    def close(self):
        """ Close server socket """
        self.running = False
        self.__socket.close()

    def set_app(self, application):
        """ Set server app """
        self.application = application

    def setup_environ(self):
        # Set up base environment
        env = self.base_environ = {}
        env['SERVER_NAME'] = self.server_name
        env['GATEWAY_INTERFACE'] = 'CGI/1.1'
        env['SERVER_PORT'] = str(self.port)
        env['REMOTE_HOST'] = ''
        env['CONTENT_LENGTH'] = ''
        env['SCRIPT_NAME'] = ''
        env['HTTPS'] = 'off'

    def set_blocking(self, flag):
        if self.running is False:
            self.__socket.setblocking(flag)

