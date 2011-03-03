# Unit testing for the Event socket
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

class EventSocketTest(Chai):
  
  def setUp(self):
    super(EventSocketTest,self).setUp()

    # mock all event callbacks
    self.mock( eventsocket, 'event' )

  # TODO: Test initialization

#   def test_write_cb_handles_errno_11_when_debug_0(self):
#     self.sock._EventSocket__write_buf = ['foo']

#     self.mox.StubOutWithMock( self.sock._EventSocket__sock, 'send' )
#     self.sock._EventSocket__sock.send( 'foo' ).AndRaise( socket.error(11, os.strerror(11)) )

#     self.mox.StubOutWithMock( self.sock, '_EventSocket__flag_activity' )
#     self.sock._EventSocket__flag_activity()

#     self.mox.ReplayAll()

#     self.assert_true( self.sock._EventSocket__write_cb() )

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

    self.assert_true( self.sock._EventSocket__write_cb() )
  '''

  def test_init_without_args(self):
    sock = EventSocket()
    self.assert_false( sock._debug )
    self.assert_equal( None, sock._logger )
    self.assert_equal( None, sock._read_event )
    self.assert_equal( None, sock._write_event )
    self.assert_equal( None, sock._accept_event )
    self.assert_equal( None, sock._pending_read_cb_event )
    self.assert_equal( 'unknown', sock._peername )
    self.assert_true( isinstance(sock._sock, socket.socket) )
    self.assert_equal( sock.listen, sock._sock.listen )
    self.assert_equal( sock.setsockopt, sock._sock.setsockopt )
    self.assert_equal( sock.fileno, sock._sock.fileno )
    self.assert_equal( sock.getpeername, sock._sock.getpeername )
    self.assert_equal( sock.getsockname, sock._sock.getsockname )
    self.assert_equal( sock.getsockopt, sock._sock.getsockopt )
    self.assert_equal( sock.setblocking, sock._sock.setblocking )
    self.assert_equal( sock.settimeout, sock._sock.settimeout )
    self.assert_equal( sock.gettimeout, sock._sock.gettimeout )
    self.assert_equal( 0, sock._max_read_buffer )
    self.assert_equal( deque(), sock._write_buf )
    self.assert_equal( bytearray(), sock._read_buf )
    self.assert_equal( None, sock._parent_accept_cb )
    self.assert_equal( None, sock._parent_read_cb )
    self.assert_equal( None, sock._parent_error_cb )
    self.assert_equal( None, sock._parent_close_cb )
    self.assert_equal( None, sock._parent_output_empty_cb )
    self.assert_equal( None, sock._error_msg )
    self.assert_false( sock._closed )
    self.assert_equal( None, sock._inactive_event )

    # TODO: mock instead that we're calling setinactivetimeout() ?
    self.assert_equal( 0, sock._inactive_timeout )

  # TODO: test with all possible args

  def test_closed_property(self):
    sock = EventSocket()
    sock._closed = 'yes'
    self.assert_equals( 'yes', sock.closed )

  # TODO: test close which needs mocks

  # don't test accept because it's a no-op

  def test_set_read_cb_when_no_reason_to_schedule_flush(self):
    sock = EventSocket()
    sock._set_read_cb( 'readit' )
    self.assert_equals( 'readit', sock._parent_read_cb )

  def test_set_read_cb_when_should_flush(self):
    sock = EventSocket()
    sock._read_buf = bytearray('somedata')
    sock._parent_read_cb = None
    sock._pending_read_cb_event = None

    self.expect(eventsocket.event.timeout).args(0, sock._protected_cb, sock._parent_read_timer_cb).returns('timeout_event')

    sock._set_read_cb( 'parent_read_cb' )
    self.assert_equals( 'parent_read_cb', sock._parent_read_cb )
    self.assert_equals( 'timeout_event', sock._pending_read_cb_event )

  def test_set_read_cb_when_data_to_flush_but_pending_read_event(self):
    sock = EventSocket()
    sock._read_buf = bytearray('somedata')
    sock._parent_read_cb = None
    sock._pending_read_cb_event = 'pending_event'

    sock._set_read_cb( 'parent_read_cb' )
    self.assert_equals( 'parent_read_cb', sock._parent_read_cb )
    self.assert_equals( 'pending_event', sock._pending_read_cb_event )

  def test_read_cb_property(self):
    sock = EventSocket()
    self.assert_equals( None, sock._parent_read_cb )
    sock.read_cb = 'read_cb'
    self.assert_equals( 'read_cb', sock._parent_read_cb )

  def test_accept_cb_property(self):
    sock = EventSocket()
    self.assert_equals( None, sock._parent_accept_cb )
    sock.accept_cb = 'accept_cb'
    self.assert_equals( 'accept_cb', sock._parent_accept_cb )

  def test_close_cb_property(self):
    sock = EventSocket()
    self.assert_equals( None, sock._parent_close_cb )
    sock.close_cb = 'close_cb'
    self.assert_equals( 'close_cb', sock._parent_close_cb )

  def test_error_cb_property(self):
    sock = EventSocket()
    self.assert_equals( None, sock._parent_error_cb )
    sock.error_cb = 'error_cb'
    self.assert_equals( 'error_cb', sock._parent_error_cb )

  def test_output_empty_cb_property(self):
    sock = EventSocket()
    self.assert_equals( None, sock._parent_output_empty_cb )
    sock.output_empty_cb = 'output_empty_cb'
    self.assert_equals( 'output_empty_cb', sock._parent_output_empty_cb )

  def test_bind_without_debugging(self):
    sock = EventSocket()
    sock._sock = self.mock()
    self.mock(sock, 'getsockname')
    
    self.expect(sock._sock.bind).args( 'arg1', 'arg2' )
    self.expect(sock.getsockname).returns( ('foo',1234) )
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
    self.expect(sock.getsockname).returns( ('foo',1234) )
    self.expect(eventsocket.event.read).args( sock, sock._protected_cb, sock._accept_cb ).returns('accept_event')

    sock.bind( 'arg1', 'arg2' )
    self.assert_equals( "foo:1234", sock._peername )
    self.assert_equals( 'accept_event', sock._accept_event )

    # TODO: test connect after merging connect() and connect_blocking()

  def test_set_inactive_timeout_when_turning_off(self):
    sock = EventSocket()
    sock._inactive_event = self.mock()
    
    self.expect( sock._inactive_event.delete )
    
    sock.set_inactive_timeout(0)
    self.assert_equals( None, sock._inactive_event )
    self.assert_equals( 0, sock._inactive_timeout )

  def test_set_inactive_timeout_when_turning_off(self):
    sock = EventSocket()
    sock._inactive_event = self.mock()
    
    self.expect( sock._inactive_event.delete )
    self.expect( eventsocket.event.timeout ).args( 32, sock._inactive_cb ).returns( 'new_timeout' )

    sock.set_inactive_timeout(32)
    self.assert_equals( 'new_timeout', sock._inactive_event )
    self.assert_equals( 32, sock._inactive_timeout )

  def test_set_inactive_timeout_on_stupid_input(self):
    sock = EventSocket()
    self.assert_raises( TypeError, sock.set_inactive_timeout, 'blah' )

  def test_handle_error_with_handler_and_err_msg(self):
    sock = EventSocket()
    sock._parent_error_cb = self.mock()
    sock._error_msg = 'isanerror'

    self.expect(sock._parent_error_cb).args( sock, 'isanerror', 'exception' )

    sock._handle_error( 'exception' )

  def test_handle_error_with_handler_and_no_err_msg(self):
    sock = EventSocket()
    sock._parent_error_cb = self.mock()

    self.expect(sock._parent_error_cb).args( sock, 'unknown error', 'exception' )

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

    self.expect( cb ).args( 'arg1', 'arg2', arg3='foo' ).returns( 'result' )

    self.assert_equals( 'result', 
      sock._protected_cb( cb, 'arg1', 'arg2', arg3='foo' ) )

  def test_protected_cb_when_an_error(self):
    sock = EventSocket()
    #self.mock( sock, '_handle_error' )
    cb = self.mock()
    sock._error_msg = 'it broked'

    exc = RuntimeError('fale')
    self.expect( cb ).args( 'arg1', 'arg2', arg3='foo' ).raises( exc )
    self.expect( sock._handle_error ).args( exc )

    self.assert_equals( None,
      sock._protected_cb( cb, 'arg1', 'arg2', arg3='foo' ) )
    self.assert_equals( None, sock._error_msg )

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

    self.assert_true( sock._accept_cb() )
    self.assert_equals( 'error accepting new socket', sock._error_msg )

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

    self.assert_true( sock._accept_cb() )

  def test_read_cb_simplest_case(self):
    sock = EventSocket()
    sock._sock = self.mock()
    self.mock( sock, 'getsockopt' )
    
    self.expect( sock.getsockopt ).args( socket.SOL_SOCKET, socket.SO_RCVBUF ).returns( 42 )
    self.expect( sock._sock.recv ).args( 42 ).returns( 'sumdata' )
    self.expect( sock._flag_activity )
    
    self.assert_true( sock._read_cb() )
    self.assert_equals( bytearray('sumdata'), sock._read_buf )
    self.assert_equals( 'error reading from socket', sock._error_msg )

  def test_read_cb_when_debugging_and_parent_cb_and_no_pending_event(self):
    sock = EventSocket()
    sock._sock = self.mock()
    sock._logger = self.mock()
    sock._peername = 'peername'
    sock._debug = True
    sock._parent_read_cb = 'p_read_cb'
    self.mock( sock, 'getsockopt' )
    
    self.expect( sock.getsockopt ).args( socket.SOL_SOCKET, socket.SO_RCVBUF ).returns( 42 )
    self.expect( sock._sock.recv ).args( 42 ).returns( 'sumdata' )
    self.expect( sock._logger.debug ).args( 'read 7 bytes from peername' )
    self.expect( sock._flag_activity )
    self.expect( eventsocket.event.timeout ).args( 0, sock._protected_cb, sock._parent_read_timer_cb ).returns('pending_read')
    
    self.assert_true( sock._read_cb() )
    self.assert_equals( bytearray('sumdata'), sock._read_buf )
    self.assert_equals( 'pending_read', sock._pending_read_cb_event )
  
  def test_read_cb_when_parent_cb_and_is_a_pending_event_and_already_buffered_data(self):
    sock = EventSocket()
    sock._read_buf = bytearray('foo')
    sock._sock = self.mock()
    sock._peername = 'peername'
    sock._parent_read_cb = 'p_read_cb'
    sock._pending_read_cb_event = 'pending_read'
    self.mock( sock, 'getsockopt' )
    
    self.expect( sock.getsockopt ).args( socket.SOL_SOCKET, socket.SO_RCVBUF ).returns( 42 )
    self.expect( sock._sock.recv ).args( 42 ).returns( 'sumdata' )
    self.expect( sock._flag_activity )
    
    self.assert_true( sock._read_cb() )
    self.assert_equals( bytearray('foosumdata'), sock._read_buf )

  def test_read_cb_when_buffer_overflow(self):
    sock = EventSocket()
    sock._sock = self.mock()
    sock._logger = self.mock()
    sock._peername = 'peername'
    sock._debug = True
    sock._max_read_buffer = 5
    self.mock( sock, 'getsockopt' )
    self.mock( sock, 'close' )
    
    self.expect( sock.getsockopt ).args( socket.SOL_SOCKET, socket.SO_RCVBUF ).returns( 42 )
    self.expect( sock._sock.recv ).args( 42 ).returns( 'sumdata' )
    self.expect( sock._logger.debug ).args( 'read 7 bytes from peername' )
    self.expect( sock._flag_activity )
    self.expect( sock._logger.debug ).args( 'buffer for peername overflowed!' )
    self.expect( sock.close )
    
    self.assert_equals( None, sock._read_cb() )
    self.assert_equals( bytearray(), sock._read_buf )

  def test_read_cb_when_no_data(self):
    sock = EventSocket()
    sock._sock = self.mock()
    self.mock( sock, 'getsockopt' )
    self.mock( sock, 'close' )
    
    self.expect( sock.getsockopt ).args( socket.SOL_SOCKET, socket.SO_RCVBUF ).returns( 42 )
    self.expect( sock._sock.recv ).args( 42 ).returns( '' )
    self.expect( sock.close )
    
    self.assert_equals( None, sock._read_cb() )

  def test_parent_read_timer_cb(self):
    sock = EventSocket()
    sock._pending_read_cb_event = 'foo'
    sock._parent_read_cb = self.mock()
    self.expect( sock._parent_read_cb ).args( sock )

    sock._parent_read_timer_cb()
    self.assert_equals( 'error processing socket input buffer', sock._error_msg )
    self.assert_equals( None, sock._pending_read_cb_event )

  def test_parent_read_timer_cb_when_closed(self):
    sock = EventSocket()
    sock._pending_read_cb_event = 'foo'
    sock._closed = True
    sock._parent_read_cb = self.mock()

    sock._parent_read_timer_cb()
    self.assert_equals( None, sock._error_msg )
    self.assert_equals( 'foo', sock._pending_read_cb_event )

  def test_parent_read_timer_cb_when_read_cb_reset(self):
    sock = EventSocket()
    sock._pending_read_cb_event = 'foo'
    
    sock._parent_read_timer_cb()
    self.assert_equals( 'error processing socket input buffer', sock._error_msg )
    self.assert_equals( None, sock._pending_read_cb_event )

  def test_write_cb_with_no_data(self):
    sock = EventSocket()
    sock._sock = self.mock()
    sock._parent_output_empty_cb = self.mock()
    sock._debug = True
    sock._logger = self.mock()
    self.mock( sock, '_flag_activity' )
    sock._write_buf = deque()

    self.assert_equals( None, sock._write_cb() )
    self.assert_equals( sock._error_msg, "error writing socket output buffer" )

  def test_write_cb_sends_all_data(self):
    sock = EventSocket()
    sock._sock = self.mock()
    sock._parent_output_empty_cb = self.mock()
    sock._write_buf = deque(['data1','data2'])

    self.expect( sock._sock.send ).args( 'data1' ).returns( 5 )
    self.expect( sock._sock.send ).args( 'data2' ).returns( 5 )
    self.expect( sock._flag_activity )
    self.expect( sock._parent_output_empty_cb ).args( sock )

    self.assert_equals( None, sock._write_cb() )
    self.assert_equals( 0, len(sock._write_buf) )
