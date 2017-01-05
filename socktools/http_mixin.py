"""
Python Sock tools: http_mixin.py - mixin to read HTTP requests from sockets
Copyright (C) 2016 GarethNelson

This file is part of python-sock-tools

python-sock-tools is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 2 of the License, or
(at your option) any later version.

python-sock-tools is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with python-sock-tools.  If not, see <http://www.gnu.org/licenses/>.

This module provides a mixin that gets HTTP requests from sockets, the basis of every webserver. No client implementation is provided - urllib or python-requests serves that purpose just fine.

Although it'd be cool, this does not currently support HTTP over UDP. Use it with a TCP socket. The HTTP support is also very basic at present.

Warning:
   Avoid using send_msg() on HTTP server sockets, this may cause various subtle and tricky to debug issues. Instead use the request object to reply.

"""

import eventlet
eventlet.monkey_patch() # this should be done in all modules that use eventlet as the first import, just in case
import StringIO

class HTTPRequest(object):
   """Represents an HTTP request

   Instances of this class are generated by HTTPMixin and used in the msg_data field.

   To respond to the request, use the reply() method.
   """
   def __init__(self,verb='GET',path='/',headers={},client_sock=None,server_sock=None):
       self.verb        = verb
       self.path        = path
       self.client_sock = client_sock
       self.server_sock = server_sock
   def reply(self,status=(200,'OK'),body='',headers={}):
       _headers = {'Content-Length':len(body)}
       headers.update(_headers)
       self.client_sock.sendall('HTTP/1.0 %d %s\r\n' % status)
       for k,v in headers.items():
           self.client_sock.sendall('%s: %s\r\n' % (k,v))
       self.client_sock.sendall('\r\n%s\n' % body)
       self.client_sock.close()
       try:
          del self.server_sock.known_peers[self.client_sock.getpeername()]
       except Exception,e:
          pass

class HTTPMixin(object):
   """A mixin for implementing HTTP

   Use this to get HTTP requests from the socket

   """

   def parse_msg(self,args):
       client_addr,data = args
       buf = StringIO.StringIO(data)
       req_line  = buf.readline().strip('\r\n')
       split_req = req_line.split()
       verb,path = split_req[0],split_req[1]
       headers   = {}
       while self.active:
          in_line = buf.readline().strip('\r\n')
          if len(in_line)>1:
             header_k,header_v = in_line.split(': ')
             headers[header_k] = header_v
          else:
             break
       return verb,HTTPRequest(verb=verb,path=path,headers=headers,client_sock=self.known_peers[client_addr]['sock'],server_sock=self)

   def do_real_read(self,s):
       """ Read a single HTTP request

       This method will read a single HTTP request without parsing it and then close the socket.
       Essentially we just read until the socket closes - which is a bit of a cheat but works.
       """
       buf         = StringIO.StringIO()
       remote_peer = s.getpeername() #hackish

       while self.active and self.known_peers.has_key(remote_peer):
         eventlet.greenthread.sleep(0)
         try:
            in_data = s.recv(1024)
            if not in_data:
               break
            else:
               buf.write(in_data)
               if in_data.endswith('\r\n\r\n'): break
         except:
            break
       retval = buf.getvalue()
       buf.close()
       if len(retval)==0: return ''
       return [remote_peer,retval]
         