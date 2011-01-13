# Unit testing for the Event socket
import unittest
import mox
import logging
import io
import random
import socket
import os
import errno

from eventsocket import EventSocket

class EventSocketTest(mox.MoxTestBase):
  
  def setUp(self):
    mox.MoxTestBase.setUp(self)

    # don't reference directly in tests, use property instead!
    self.__sock = None

  def __getSockInstance(self):
    '''Get a socket instance that has been built without calling __init__'''
    if self.__sock == None:
      self.__sock = EventSocket.__new__(EventSocket)

      self.__sock._EventSocket__debug = False
      self.__sock._EventSocket__logger = mox.MockObject(logging)
      self.__sock._EventSocket__peername = 'localhost:44444'
      self.__sock._EventSocket__sock = mox.MockObject( socket.socket )
    return self.__sock
  sock = property(fget=__getSockInstance)

  # TODO: Test initialization

#   def test_write_cb_handles_errno_11_when_debug_0(self):
#     self.sock._EventSocket__write_buf = ['foo']

#     self.mox.StubOutWithMock( self.sock._EventSocket__sock, 'send' )
#     self.sock._EventSocket__sock.send( 'foo' ).AndRaise( socket.error(11, os.strerror(11)) )

#     self.mox.StubOutWithMock( self.sock, '_EventSocket__flag_activity' )
#     self.sock._EventSocket__flag_activity()

#     self.mox.ReplayAll()

#     self.assertTrue( self.sock._EventSocket__write_cb() )

  def test_write_cb_handles_errno_EAGAIN_when_debug_1(self):
    self.sock._EventSocket__debug = True
    self.sock._EventSocket__write_buf = ['foo']

    self.mox.StubOutWithMock( self.sock._EventSocket__sock, 'send' )
    self.sock._EventSocket__sock.send( 'foo' ).AndRaise( socket.error(errno.EAGAIN, os.strerror(errno.EAGAIN)) )

    self.mox.StubOutWithMock( self.sock._EventSocket__logger, 'debug' )
    self.sock._EventSocket__logger.debug( \
      '"[Errno %d] Resource temporarily unavailable" raised, waiting to flush to localhost:44444'%(errno.EAGAIN) )
    
    self.sock._EventSocket__logger.debug( \
      'wrote 0/3 bytes to localhost:44444' )

    self.mox.StubOutWithMock( self.sock, '_EventSocket__flag_activity' )
    self.sock._EventSocket__flag_activity()

    self.mox.ReplayAll()

    self.assertTrue( self.sock._EventSocket__write_cb() )

