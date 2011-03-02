# Unit testing for the Event socket
import unittest
import mox
import logging
import io
import random
import socket
import os
import errno
from collections import deque
from chai import Chai

import eventsocket
from eventsocket import EventSocket

#class EventSocketTest(mox.MoxTestBase):
class EventSocketTest(Chai):
  
  def setUp(self):
    #mox.MoxTestBase.setUp(self)
    super(EventSocketTest,self).setUp()

    # mock all event callbacks
    #self.mock( eventsocket, 'event' )

  # TODO: Test initialization

#   def test_write_cb_handles_errno_11_when_debug_0(self):
#     self.sock._EventSocket__write_buf = ['foo']

#     self.mox.StubOutWithMock( self.sock._EventSocket__sock, 'send' )
#     self.sock._EventSocket__sock.send( 'foo' ).AndRaise( socket.error(11, os.strerror(11)) )

#     self.mox.StubOutWithMock( self.sock, '_EventSocket__flag_activity' )
#     self.sock._EventSocket__flag_activity()

#     self.mox.ReplayAll()

#     self.assertTrue( self.sock._EventSocket__write_cb() )

  '''
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
  '''

  def test_init_without_args(self):
    sock = EventSocket()
    self.assertFalse( sock._debug )
    self.assertEqual( None, sock._logger )
    self.assertEqual( None, sock._read_event )
    self.assertEqual( None, sock._write_event )
    self.assertEqual( None, sock._accept_event )
    self.assertEqual( None, sock._pending_read_cb_event )
    self.assertEqual( 'unknown', sock._peername )
    self.assertTrue( isinstance(sock._sock, socket.socket) )
    self.assertEqual( sock.listen, sock._sock.listen )
    self.assertEqual( sock.setsockopt, sock._sock.setsockopt )
    self.assertEqual( sock.fileno, sock._sock.fileno )
    self.assertEqual( sock.getpeername, sock._sock.getpeername )
    self.assertEqual( sock.getsockname, sock._sock.getsockname )
    self.assertEqual( sock.getsockopt, sock._sock.getsockopt )
    self.assertEqual( sock.setblocking, sock._sock.setblocking )
    self.assertEqual( sock.settimeout, sock._sock.settimeout )
    self.assertEqual( sock.gettimeout, sock._sock.gettimeout )
    self.assertEqual( 0, sock._max_read_buffer )
    self.assertEqual( deque(), sock._write_buf )
    self.assertEqual( bytearray(), sock._read_buf )
    self.assertEqual( None, sock._parent_accept_cb )
    self.assertEqual( None, sock._parent_read_cb )
    self.assertEqual( None, sock._parent_error_cb )
    self.assertEqual( None, sock._parent_close_cb )
    self.assertEqual( None, sock._parent_output_empty_cb )
    self.assertEqual( None, sock._error_msg )
    self.assertFalse( sock._closed )
    self.assertEqual( None, sock._inactive_event )

    # TODO: mock instead that we're calling setinactivetimeout() ?
    self.assertEqual( 0, sock._inactive_timeout )

  # TODO: test with all possible args

  def test_closed_property(self):
    sock = EventSocket()
    sock._closed = 'yes'
    self.assertEquals( 'yes', sock.closed )

  # TODO: test close which needs mocks

  # don't test accept because it's a no-op

  def test_set_read_cb_when_no_reason_to_schedule_flush(self):
    sock = EventSocket()
    sock._set_read_cb( 'readit' )
    self.assertEquals( 'readit', sock._parent_read_cb )

  def test_set_read_cb_when_should_flush(self):
    sock = EventSocket()
    sock._read_buf = bytearray('somedata')
    sock._parent_read_cb = None
    sock._pending_read_cb_event = None

    self.expect(eventsocket.event.timeout).args(0, sock._protected_cb, sock._parent_read_timer_cb).returns('timeout_event')

    sock._set_read_cb( 'parent_read_cb' )
    self.assertEquals( 'parent_read_cb', sock._parent_read_cb )
    self.assertEquals( 'timeout_event', sock._pending_read_cb_event )

  def test_set_read_cb_when_data_to_flush_but_pending_read_event(self):
    sock = EventSocket()
    sock._read_buf = bytearray('somedata')
    sock._parent_read_cb = None
    sock._pending_read_cb_event = 'pending_event'

    sock._set_read_cb( 'parent_read_cb' )
    self.assertEquals( 'parent_read_cb', sock._parent_read_cb )
    self.assertEquals( 'pending_event', sock._pending_read_cb_event )

  def test_read_cb_property(self):
    sock = EventSocket()
    self.assertEquals( None, sock._parent_read_cb )
    sock.read_cb = 'read_cb'
    self.assertEquals( 'read_cb', sock._parent_read_cb )

  def test_accept_cb_property(self):
    sock = EventSocket()
    self.assertEquals( None, sock._parent_accept_cb )
    sock.accept_cb = 'accept_cb'
    self.assertEquals( 'accept_cb', sock._parent_accept_cb )

  def test_close_cb_property(self):
    sock = EventSocket()
    self.assertEquals( None, sock._parent_close_cb )
    sock.close_cb = 'close_cb'
    self.assertEquals( 'close_cb', sock._parent_close_cb )

  def test_error_cb_property(self):
    sock = EventSocket()
    self.assertEquals( None, sock._parent_error_cb )
    sock.error_cb = 'error_cb'
    self.assertEquals( 'error_cb', sock._parent_error_cb )

  def test_output_empty_cb_property(self):
    sock = EventSocket()
    self.assertEquals( None, sock._parent_output_empty_cb )
    sock.output_empty_cb = 'output_empty_cb'
    self.assertEquals( 'output_empty_cb', sock._parent_output_empty_cb )

  def test_bind_without_debugging(self):
    sock = EventSocket()
    sock._sock = self.mock()
    self.mock(sock, 'getsockname')
    
    self.expect(sock._sock.bind).args( 'arg1', 'arg2' )
    self.expect(sock.getsockname.__call__).returns( ('foo',1234) )
    self.expect(eventsocket.event.read).args( sock, sock._protected_cb, sock._accept_cb )

    sock.bind( 'arg1', 'arg2' )

  def test_bind_with_debugging(self):
    sock = EventSocket()
    sock._sock = self.mock()
    sock._debug = True
    sock._logger = self.mock()
    self.mock( sock, 'getsockname' )
    
    self.expect(sock._logger.debug).args( "binding to %s", str(('arg1','arg2')) )
    self.expect(sock._sock.bind).args( 'arg1', 'arg2' )
    self.expect(sock.getsockname.__call__).returns( ('foo',1234) )
    self.expect(eventsocket.event.read).args( sock, sock._protected_cb, sock._accept_cb ).returns('accept_event')

    sock.bind( 'arg1', 'arg2' )
    self.assertEquals( "foo:1234", sock._peername )
    self.assertEquals( 'accept_event', sock._accept_event )

    # TODO: test connect after merging connect() and connect_blocking()

  def test_set_inactive_timeout_when_turning_off(self):
    sock = EventSocket()
    sock._inactive_event = self.mock()
    
    self.expect( sock._inactive_event.delete )
    
    sock.set_inactive_timeout(0)
    self.assertEquals( None, sock._inactive_event )
    self.assertEquals( 0, sock._inactive_timeout )

  def test_set_inactive_timeout_when_turning_off(self):
    sock = EventSocket()
    sock._inactive_event = self.mock()
    
    self.expect( sock._inactive_event.delete )
    self.expect( eventsocket.event.timeout ).args( 32, sock._inactive_cb ).returns( 'new_timeout' )

    sock.set_inactive_timeout(32)
    self.assertEquals( 'new_timeout', sock._inactive_event )
    self.assertEquals( 32, sock._inactive_timeout )

  def test_set_inactive_timeout_on_stupid_input(self):
    sock = EventSocket()
    self.assertRaises( TypeError, sock.set_inactive_timeout, 'blah' )

  def test_handle_error_with_handler_and_err_msg(self):
    sock = EventSocket()
    sock._parent_error_cb = self.mock()
    sock._error_msg = 'isanerror'

    self.expect(sock._parent_error_cb.__call__).args( sock, 'isanerror', 'exception' )

    sock._handle_error( 'exception' )

  def test_handle_error_with_handler_and_no_err_msg(self):
    sock = EventSocket()
    sock._parent_error_cb = self.mock()

    self.expect(sock._parent_error_cb.__call__).args( sock, 'unknown error', 'exception' )

    sock._handle_error( 'exception' )

  def test_handle_error_no_handler_and_logger_and_err_msg(self):
    sock = EventSocket()
    sock._logger = self.mock()
    sock._error_msg = 'isanerror'

    self.expect(sock._logger.error).args( 'unhandled error isanerror', exc_info=True )

    sock._handle_error( 'exception' )

  def test_handle_error_no_handler_and_logger_and_no_err_msg(self):
    sock = EventSocket()
    sock._logger = self.mock()

    self.expect(sock._logger.error).args( 'unhandled unknown error', exc_info=True )

    sock._handle_error( 'exception' )

  def test_handle_error_no_handler_and_no_logger(self):
    sock = EventSocket()
    self.mock( eventsocket, 'traceback' )

    self.expect(eventsocket.traceback.print_exc)

    sock._handle_error( 'exception' )

  def test_protected_cb_when_no_error(self):
    sock = EventSocket()
    cb = self.mock()

    self.expect(cb.__call__).args( 'arg1', 'arg2', arg3='foo' ).returns( 'result' )

    self.assertEquals( 'result', 
      sock._protected_cb( cb, 'arg1', 'arg2', arg3='foo' ) )

  def test_protected_cb_when_an_error(self):
    sock = EventSocket()
    self.mock( sock, '_handle_error' )
    cb = self.mock()
    sock._error_msg = 'it broked'

    exc = RuntimeError('fale')
    self.expect(cb.__call__).args( 'arg1', 'arg2', arg3='foo' ).raises( exc )
    sock._handle_error( exc )

    self.assertEquals( None,
      sock._protected_cb( cb, 'arg1', 'arg2', arg3='foo' ) )
    self.assertEquals( None, sock._error_msg )

  def test_accept_cb_when_no_logger_and_no_parent_cb(self):
    sock = EventSocket()
    sock._sock = self.mock()
    sock._parent_read_cb = 'p_read_cb'
    sock._parent_error_cb = 'p_error_cb'
    sock._parent_close_cb = 'p_close_cb'
    sock._debug = False
    sock._logger = None
    sock._max_read_buffer = 42

    self.expect(sock._sock.accept).returns( ('connection', 'address') )
    self.expect(EventSocket.__init__).args( read_cb='p_read_cb', error_cb='p_error_cb',
      close_cb='p_close_cb', sock='connection', debug=False,
      logger=None, max_read_buffer=42 )

    self.assertTrue( sock._accept_cb() )
    self.assertEquals( 'error accepting new socket', sock._error_msg )

  def test_accept_cb_when_logger_and_parent_cb(self):
    sock = EventSocket()
    sock._sock = self.mock()
    sock._parent_accept_cb = 'p_accept_cb'
    sock._parent_read_cb = 'p_read_cb'
    sock._parent_error_cb = 'p_error_cb'
    sock._parent_close_cb = 'p_close_cb'
    sock._debug = True
    sock._logger = self.mock()
    sock._max_read_buffer = 42

    self.expect(sock._sock.accept).returns( ('connection', 'address') )
    self.expect(sock._logger.debug).args( "accepted connection from address" )
    self.expect(EventSocket.__init__).args( read_cb='p_read_cb', error_cb='p_error_cb',
      close_cb='p_close_cb', sock='connection', debug=True,
      logger=sock._logger, max_read_buffer=42 )
    self.expect(sock._protected_cb).args( 'p_accept_cb', self.instance_of(EventSocket) )

    self.assertTrue( sock._accept_cb() )

  def test_read_cb_simplest_case(self):
    sock = EventSocket()
    sock._sock = self.mock()
    self.mock( sock, 'getsockopt' )
    
    self.expect( sock.getsockopt.__call__ ).args( socket.SOL_SOCKET, socket.SO_RCVBUF ).returns( 42 )
    self.expect( sock._sock.recv ).args( 42 ).returns( 'sumdata' )
    self.expect( sock._flag_activity )
    
    self.assertTrue( sock._read_cb() )
    self.assertEquals( bytearray('sumdata'), sock._read_buf )
    self.assertEquals( 'error reading from socket', sock._error_msg )

  def test_read_cb_when_debugging_and_parent_cb_and_no_pending_event(self):
    sock = EventSocket()
    sock._sock = self.mock()
    sock._logger = self.mock()
    sock._peername = 'peername'
    sock._debug = True
    sock._parent_read_cb = 'p_read_cb'
    self.mock( sock, 'getsockopt' )
    
    self.expect( sock.getsockopt.__call__ ).args( socket.SOL_SOCKET, socket.SO_RCVBUF ).returns( 42 )
    self.expect( sock._sock.recv ).args( 42 ).returns( 'sumdata' )
    self.expect( sock._logger.debug ).args( 'read 7 bytes from peername' )
    self.expect( sock._flag_activity )
    self.expect( eventsocket.event.timeout ).args( 0, sock._protected_cb, sock._parent_read_timer_cb ).returns('pending_read')
    
    self.assertTrue( sock._read_cb() )
    self.assertEquals( bytearray('sumdata'), sock._read_buf )
    self.assertEquals( 'pending_read', sock._pending_read_cb_event )
  
  def test_read_cb_when_parent_cb_and_is_a_pending_event_and_already_buffered_data(self):
    sock = EventSocket()
    sock._read_buf = bytearray('foo')
    sock._sock = self.mock()
    sock._peername = 'peername'
    sock._parent_read_cb = 'p_read_cb'
    sock._pending_read_cb_event = 'pending_read'
    self.mock( sock, 'getsockopt' )
    
    self.expect( sock.getsockopt.__call__ ).args( socket.SOL_SOCKET, socket.SO_RCVBUF ).returns( 42 )
    self.expect( sock._sock.recv ).args( 42 ).returns( 'sumdata' )
    self.expect( sock._flag_activity )
    
    self.assertTrue( sock._read_cb() )
    self.assertEquals( bytearray('foosumdata'), sock._read_buf )

  def test_read_cb_when_buffer_overflow(self):
    sock = EventSocket()
    sock._sock = self.mock()
    sock._logger = self.mock()
    sock._peername = 'peername'
    sock._debug = True
    sock._max_read_buffer = 5
    self.mock( sock, 'getsockopt' )
    self.mock( sock, 'close' )
    
    self.expect( sock.getsockopt.__call__ ).args( socket.SOL_SOCKET, socket.SO_RCVBUF ).returns( 42 )
    self.expect( sock._sock.recv ).args( 42 ).returns( 'sumdata' )
    self.expect( sock._logger.debug ).args( 'read 7 bytes from peername' )
    self.expect( sock._flag_activity )
    self.expect( sock._logger.debug ).args( 'buffer for peername overflowed!' )
    self.expect( sock.close.__call__ )
    
    self.assertEquals( None, sock._read_cb() )
    self.assertEquals( bytearray(), sock._read_buf )

  def test_read_cb_when_no_data(self):
    sock = EventSocket()
    sock._sock = self.mock()
    self.mock( sock, 'getsockopt' )
    self.mock( sock, 'close' )
    
    self.expect( sock.getsockopt.__call__ ).args( socket.SOL_SOCKET, socket.SO_RCVBUF ).returns( 42 )
    self.expect( sock._sock.recv ).args( 42 ).returns( '' )
    self.expect( sock.close.__call__ )
    
    self.assertEquals( None, sock._read_cb() )

  def test_parent_read_timer_cb(self):
    sock = EventSocket()
    sock._pending_read_cb_event = 'foo'
    sock._parent_read_cb = self.create_mock_anything()

    sock._parent_read_cb( sock )

    self.replay_all()
    sock._parent_read_timer_cb()
    self.assertEquals( 'error processing socket input buffer', sock._error_msg )
    self.assertEquals( None, sock._pending_read_cb_event )

  def test_parent_read_timer_cb_when_closed(self):
    sock = EventSocket()
    sock._pending_read_cb_event = 'foo'
    sock._closed = True
    sock._parent_read_cb = self.create_mock_anything()

    sock._parent_read_timer_cb()
    self.assertEquals( None, sock._error_msg )
    self.assertEquals( 'foo', sock._pending_read_cb_event )

  def test_parent_read_timer_cb_when_read_cb_reset(self):
    sock = EventSocket()
    sock._pending_read_cb_event = 'foo'
    
    sock._parent_read_timer_cb()
    self.assertEquals( 'error processing socket input buffer', sock._error_msg )
    self.assertEquals( None, sock._pending_read_cb_event )

  def test_write_cb_with_no_data(self):
    sock = EventSocket()
    sock._sock = self.create_mock_anything()
    sock._parent_output_empty_cb = self.create_mock_anything()
    sock._debug = True
    sock._logger = self.create_mock_anything()
    self.mock( sock, '_flag_activity' )
    sock._write_buf = deque()

    self.assertEquals( None, sock._write_cb() )
    self.assertEquals( sock._error_msg, "error writing socket output buffer" )

  def test_write_cb_sends_all_data(self):
    sock = EventSocket()
    sock._sock = self.create_mock_anything()
    sock._parent_output_empty_cb = self.create_mock_anything()
    self.mock( sock, '_flag_activity' )
    sock._write_buf = deque(['data1','data2'])

    sock._sock.send( 'data1' ).AndReturn( 5 )
    sock._sock.send( 'data2' ).AndReturn( 5 )
    sock._flag_activity()
    sock._parent_output_empty_cb( sock )

    self.replay_all()
    self.assertEquals( None, sock._write_cb() )
    self.assertEquals( 0, len(sock._write_buf) )
