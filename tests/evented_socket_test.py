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
    mock( eventsocket, 'event' )

  def test_init_without_args(self):
    sock = EventSocket()
    assert_false( sock._debug )
    assert_equal( None, sock._logger )
    assert_equal( None, sock._read_event )
    assert_equal( None, sock._write_event )
    assert_equal( None, sock._accept_event )
    assert_equal( None, sock._pending_read_cb_event )
    assert_equal( 'unknown', sock._peername )
    assert_true( isinstance(sock._sock, socket.socket) )
    assert_equal( sock.listen, sock._sock.listen )
    assert_equal( sock.setsockopt, sock._sock.setsockopt )
    assert_equal( sock.fileno, sock._sock.fileno )
    assert_equal( sock.getpeername, sock._sock.getpeername )
    assert_equal( sock.getsockname, sock._sock.getsockname )
    assert_equal( sock.getsockopt, sock._sock.getsockopt )
    assert_equal( sock.setblocking, sock._sock.setblocking )
    assert_equal( sock.settimeout, sock._sock.settimeout )
    assert_equal( sock.gettimeout, sock._sock.gettimeout )
    assert_equal( sock.shutdown, sock._sock.shutdown )
    assert_equal( 0, sock._max_read_buffer )
    assert_equal( deque(), sock._write_buf )
    assert_equal( bytearray(), sock._read_buf )
    assert_equal( None, sock._parent_accept_cb )
    assert_equal( None, sock._parent_read_cb )
    assert_equal( None, sock._parent_error_cb )
    assert_equal( None, sock._parent_close_cb )
    assert_equal( None, sock._parent_output_empty_cb )
    assert_equal( None, sock._error_msg )
    assert_false( sock._closed )
    assert_equal( None, sock._inactive_event )

    # TODO: mock instead that we're calling setinactivetimeout() ?
    assert_equal( 0, sock._inactive_timeout )

  # TODO: test with all possible args

  def test_closed_property(self):
    sock = EventSocket()
    sock._closed = 'yes'
    assert_equals( 'yes', sock.closed )

  # TODO: test close which needs mocks

  # don't test accept because it's a no-op

  def test_set_read_cb_when_no_reason_to_schedule_flush(self):
    sock = EventSocket()
    sock._set_read_cb( 'readit' )
    assert_equals( 'readit', sock._parent_read_cb )

  def test_set_read_cb_when_should_flush(self):
    sock = EventSocket()
    sock._read_buf = bytearray('somedata')
    sock._parent_read_cb = None
    sock._pending_read_cb_event = None

    expect(eventsocket.event.timeout).args(0, sock._protected_cb, sock._parent_read_timer_cb).returns('timeout_event')

    sock._set_read_cb( 'parent_read_cb' )
    assert_equals( 'parent_read_cb', sock._parent_read_cb )
    assert_equals( 'timeout_event', sock._pending_read_cb_event )

  def test_set_read_cb_when_data_to_flush_but_pending_read_event(self):
    sock = EventSocket()
    sock._read_buf = bytearray('somedata')
    sock._parent_read_cb = None
    sock._pending_read_cb_event = 'pending_event'

    sock._set_read_cb( 'parent_read_cb' )
    assert_equals( 'parent_read_cb', sock._parent_read_cb )
    assert_equals( 'pending_event', sock._pending_read_cb_event )

  def test_read_cb_property(self):
    sock = EventSocket()
    assert_equals( None, sock._parent_read_cb )
    sock.read_cb = 'read_cb'
    assert_equals( 'read_cb', sock._parent_read_cb )

  def test_accept_cb_property(self):
    sock = EventSocket()
    assert_equals( None, sock._parent_accept_cb )
    sock.accept_cb = 'accept_cb'
    assert_equals( 'accept_cb', sock._parent_accept_cb )

  def test_close_cb_property(self):
    sock = EventSocket()
    assert_equals( None, sock._parent_close_cb )
    sock.close_cb = 'close_cb'
    assert_equals( 'close_cb', sock._parent_close_cb )

  def test_error_cb_property(self):
    sock = EventSocket()
    assert_equals( None, sock._parent_error_cb )
    sock.error_cb = 'error_cb'
    assert_equals( 'error_cb', sock._parent_error_cb )

  def test_output_empty_cb_property(self):
    sock = EventSocket()
    assert_equals( None, sock._parent_output_empty_cb )
    sock.output_empty_cb = 'output_empty_cb'
    assert_equals( 'output_empty_cb', sock._parent_output_empty_cb )

  def test_bind_without_debugging(self):
    sock = EventSocket()
    sock._sock = mock()
    mock(sock, 'getsockname')
    
    expect(sock._sock.bind).args( 'arg1', 'arg2' )
    expect(sock.getsockname).returns( ('foo',1234) )
    expect(eventsocket.event.read).args( sock, sock._protected_cb, sock._accept_cb )

    sock.bind( 'arg1', 'arg2' )

  def test_bind_with_debugging(self):
    sock = EventSocket()
    sock._sock = mock()
    sock._debug = True
    sock._logger = mock()
    mock( sock, 'getsockname' )
    
    expect(sock._logger.debug).args( "binding to %s", str(('arg1','arg2')) )
    expect(sock._sock.bind).args( 'arg1', 'arg2' )
    expect(sock.getsockname).returns( ('foo',1234) )
    expect(eventsocket.event.read).args( sock, sock._protected_cb, sock._accept_cb ).returns('accept_event')

    sock.bind( 'arg1', 'arg2' )
    assert_equals( "foo:1234", sock._peername )
    assert_equals( 'accept_event', sock._accept_event )

    # TODO: test connect after merging connect() and connect_blocking()

  def test_set_inactive_timeout_when_turning_off(self):
    sock = EventSocket()
    sock._inactive_event = mock()
    
    expect( sock._inactive_event.delete )
    
    sock.set_inactive_timeout(0)
    assert_equals( None, sock._inactive_event )
    assert_equals( 0, sock._inactive_timeout )

  def test_set_inactive_timeout_when_turning_off(self):
    sock = EventSocket()
    sock._inactive_event = mock()
    
    expect( sock._inactive_event.delete )
    expect( eventsocket.event.timeout ).args( 32, sock._inactive_cb ).returns( 'new_timeout' )

    sock.set_inactive_timeout(32)
    assert_equals( 'new_timeout', sock._inactive_event )
    assert_equals( 32, sock._inactive_timeout )

  def test_set_inactive_timeout_on_stupid_input(self):
    sock = EventSocket()
    assert_raises( TypeError, sock.set_inactive_timeout, 'blah' )

  def test_handle_error_with_handler_and_err_msg(self):
    sock = EventSocket()
    sock._parent_error_cb = mock()
    sock._error_msg = 'isanerror'

    expect(sock._parent_error_cb).args( sock, 'isanerror', 'exception' )

    sock._handle_error( 'exception' )

  def test_handle_error_with_handler_and_no_err_msg(self):
    sock = EventSocket()
    sock._parent_error_cb = mock()

    expect(sock._parent_error_cb).args( sock, 'unknown error', 'exception' )

    sock._handle_error( 'exception' )

  def test_handle_error_no_handler_and_logger_and_err_msg(self):
    sock = EventSocket()
    sock._logger = mock()
    sock._error_msg = 'isanerror'

    expect(sock._logger.error).args( 'unhandled error isanerror', exc_info=True )

    sock._handle_error( 'exception' )

  def test_handle_error_no_handler_and_logger_and_no_err_msg(self):
    sock = EventSocket()
    sock._logger = mock()

    expect(sock._logger.error).args( 'unhandled unknown error', exc_info=True )

    sock._handle_error( 'exception' )

  def test_handle_error_no_handler_and_no_logger(self):
    sock = EventSocket()
    mock( eventsocket, 'traceback' )

    expect(eventsocket.traceback.print_exc)

    sock._handle_error( 'exception' )

  def test_protected_cb_when_no_error(self):
    sock = EventSocket()
    cb = mock()

    expect( cb ).args( 'arg1', 'arg2', arg3='foo' ).returns( 'result' )

    assert_equals( 'result', 
      sock._protected_cb( cb, 'arg1', 'arg2', arg3='foo' ) )

  def test_protected_cb_when_an_error(self):
    sock = EventSocket()
    #mock( sock, '_handle_error' )
    cb = mock()
    sock._error_msg = 'it broked'

    exc = RuntimeError('fale')
    expect( cb ).args( 'arg1', 'arg2', arg3='foo' ).raises( exc )
    expect( sock._handle_error ).args( exc )

    assert_equals( None,
      sock._protected_cb( cb, 'arg1', 'arg2', arg3='foo' ) )
    assert_equals( None, sock._error_msg )

  def test_accept_cb_when_no_logger_and_no_parent_cb(self):
    sock = EventSocket()
    sock._sock = mock()
    sock._parent_read_cb = 'p_read_cb'
    sock._parent_error_cb = 'p_error_cb'
    sock._parent_close_cb = 'p_close_cb'
    sock._debug = False
    sock._logger = None
    sock._max_read_buffer = 42

    expect(sock._sock.accept).returns( ('connection', 'address') )
    expect(EventSocket.__init__).args( read_cb='p_read_cb', error_cb='p_error_cb',
      close_cb='p_close_cb', sock='connection', debug=False,
      logger=None, max_read_buffer=42 )

    assert_true( sock._accept_cb() )
    assert_equals( 'error accepting new socket', sock._error_msg )

  def test_accept_cb_when_logger_and_parent_cb(self):
    sock = EventSocket()
    sock._sock = mock()
    sock._parent_accept_cb = 'p_accept_cb'
    sock._parent_read_cb = 'p_read_cb'
    sock._parent_error_cb = 'p_error_cb'
    sock._parent_close_cb = 'p_close_cb'
    sock._debug = True
    sock._logger = mock()
    sock._max_read_buffer = 42

    expect(sock._sock.accept).returns( ('connection', 'address') )
    expect(sock._logger.debug).args( "accepted connection from address" )
    expect(EventSocket.__init__).args( read_cb='p_read_cb', error_cb='p_error_cb',
      close_cb='p_close_cb', sock='connection', debug=True,
      logger=sock._logger, max_read_buffer=42 )
    expect(sock._protected_cb).args( 'p_accept_cb', instance_of(EventSocket) )

    assert_true( sock._accept_cb() )

  def test_read_cb_simplest_case(self):
    sock = EventSocket()
    sock._sock = mock()
    mock( sock, 'getsockopt' )
    
    expect( sock.getsockopt ).args( socket.SOL_SOCKET, socket.SO_RCVBUF ).returns( 42 )
    expect( sock._sock.recv ).args( 42 ).returns( 'sumdata' )
    expect( sock._flag_activity )
    
    assert_true( sock._read_cb() )
    assert_equals( bytearray('sumdata'), sock._read_buf )
    assert_equals( 'error reading from socket', sock._error_msg )

  def test_read_cb_when_debugging_and_parent_cb_and_no_pending_event(self):
    sock = EventSocket()
    sock._sock = mock()
    sock._logger = mock()
    sock._peername = 'peername'
    sock._debug = True
    sock._parent_read_cb = 'p_read_cb'
    mock( sock, 'getsockopt' )
    
    expect( sock.getsockopt ).args( socket.SOL_SOCKET, socket.SO_RCVBUF ).returns( 42 )
    expect( sock._sock.recv ).args( 42 ).returns( 'sumdata' )
    expect( sock._logger.debug ).args( 'read 7 bytes from peername' )
    expect( sock._flag_activity )
    expect( eventsocket.event.timeout ).args( 0, sock._protected_cb, sock._parent_read_timer_cb ).returns('pending_read')
    
    assert_true( sock._read_cb() )
    assert_equals( bytearray('sumdata'), sock._read_buf )
    assert_equals( 'pending_read', sock._pending_read_cb_event )
  
  def test_read_cb_when_parent_cb_and_is_a_pending_event_and_already_buffered_data(self):
    sock = EventSocket()
    sock._read_buf = bytearray('foo')
    sock._sock = mock()
    sock._peername = 'peername'
    sock._parent_read_cb = 'p_read_cb'
    sock._pending_read_cb_event = 'pending_read'
    mock( sock, 'getsockopt' )
    
    expect( sock.getsockopt ).args( socket.SOL_SOCKET, socket.SO_RCVBUF ).returns( 42 )
    expect( sock._sock.recv ).args( 42 ).returns( 'sumdata' )
    expect( sock._flag_activity )
    
    assert_true( sock._read_cb() )
    assert_equals( bytearray('foosumdata'), sock._read_buf )

  def test_read_cb_when_buffer_overflow(self):
    sock = EventSocket()
    sock._sock = mock()
    sock._logger = mock()
    sock._peername = 'peername'
    sock._debug = True
    sock._max_read_buffer = 5
    mock( sock, 'getsockopt' )
    mock( sock, 'close' )
    
    expect( sock.getsockopt ).args( socket.SOL_SOCKET, socket.SO_RCVBUF ).returns( 42 )
    expect( sock._sock.recv ).args( 42 ).returns( 'sumdata' )
    expect( sock._logger.debug ).args( 'read 7 bytes from peername' )
    expect( sock._flag_activity )
    expect( sock._logger.debug ).args( 'buffer for peername overflowed!' )
    expect( sock.close )
    
    assert_equals( None, sock._read_cb() )
    assert_equals( bytearray(), sock._read_buf )

  def test_read_cb_when_no_data(self):
    sock = EventSocket()
    sock._sock = mock()
    mock( sock, 'getsockopt' )
    mock( sock, 'close' )
    
    expect( sock.getsockopt ).args( socket.SOL_SOCKET, socket.SO_RCVBUF ).returns( 42 )
    expect( sock._sock.recv ).args( 42 ).returns( '' )
    expect( sock.close )
    
    assert_equals( None, sock._read_cb() )

  def test_parent_read_timer_cb(self):
    sock = EventSocket()
    sock._pending_read_cb_event = 'foo'
    sock._parent_read_cb = mock()
    expect( sock._parent_read_cb ).args( sock )

    sock._parent_read_timer_cb()
    assert_equals( 'error processing socket input buffer', sock._error_msg )
    assert_equals( None, sock._pending_read_cb_event )

  def test_parent_read_timer_cb_when_closed(self):
    sock = EventSocket()
    sock._pending_read_cb_event = 'foo'
    sock._closed = True
    sock._parent_read_cb = mock()

    sock._parent_read_timer_cb()
    assert_equals( None, sock._error_msg )
    assert_equals( 'foo', sock._pending_read_cb_event )

  def test_parent_read_timer_cb_when_read_cb_reset(self):
    sock = EventSocket()
    sock._pending_read_cb_event = 'foo'
    
    sock._parent_read_timer_cb()
    assert_equals( 'error processing socket input buffer', sock._error_msg )
    assert_equals( None, sock._pending_read_cb_event )

  def test_write_cb_with_no_data(self):
    sock = EventSocket()
    sock._sock = mock()
    sock._parent_output_empty_cb = mock()
    sock._debug = True
    sock._logger = mock()
    mock( sock, '_flag_activity' )
    sock._write_buf = deque()

    assert_equals( None, sock._write_cb() )
    assert_equals( sock._error_msg, "error writing socket output buffer" )

  def test_write_cb_sends_all_data_and_theres_an_output_empty_cb(self):
    sock = EventSocket()
    sock._sock = mock()
    sock._parent_output_empty_cb = mock()
    sock._write_buf = deque(['data1','data2'])

    expect( sock._sock.send ).args( 'data1' ).returns( 5 )
    expect( sock._sock.send ).args( 'data2' ).returns( 5 )
    expect( sock._flag_activity )
    expect( sock._parent_output_empty_cb ).args( sock )

    assert_equals( None, sock._write_cb() )
    assert_equals( 0, len(sock._write_buf) )

  def test_write_cb_when_not_all_data_sent(self):
    sock = EventSocket()
    sock._sock = mock()
    sock._parent_output_empty_cb = mock()  # assert not called
    sock._write_buf = deque(['data1','data2'])

    expect( sock._sock.send ).args( 'data1' ).returns( 5 )
    expect( sock._sock.send ).args( 'data2' ).returns( 2 )
    expect( sock._flag_activity )

    assert_true( sock._write_cb() )
    assert_equals( deque(['ta2']), sock._write_buf )

  def test_write_cb_when_not_all_data_sent_and_logging(self):
    sock = EventSocket()
    sock._sock = mock()
    sock._peername = 'peer'
    sock._logger = mock()
    sock._debug = True
    sock._parent_output_empty_cb = mock()  # assert not called
    sock._write_buf = deque(['data1','data2'])

    expect( sock._sock.send ).args( 'data1' ).returns( 5 )
    expect( sock._sock.send ).args( 'data2' ).returns( 2 )
    expect( sock._logger.debug ).args( str, 7, 10, 'peer' )
    expect( sock._flag_activity )

    assert_true( sock._write_cb() )
    assert_equals( deque(['ta2']), sock._write_buf )

  def test_write_cb_when_eagain_raised(self):
    sock = EventSocket()
    sock._sock = mock()
    sock._parent_output_empty_cb = mock()  # assert not called
    sock._write_buf = deque(['data1','data2'])

    expect( sock._sock.send ).args( 'data1' ).raises(
      EnvironmentError(errno.EAGAIN,'try again') )
    expect( sock._flag_activity )

    assert_true( sock._write_cb() )
    assert_equals( deque(['data1','data2']), sock._write_buf )

  def test_write_cb_when_eagain_raised_and_logging(self):
    sock = EventSocket()
    sock._sock = mock()
    sock._peername = 'peer'
    sock._logger = mock()
    sock._debug = True
    sock._parent_output_empty_cb = mock()  # assert not called
    sock._write_buf = deque(['data1','data2'])

    expect( sock._sock.send ).args( 'data1' ).raises(
      EnvironmentError(errno.EAGAIN,'try again') )
    expect( sock._logger.debug ).args( str, EnvironmentError, 'peer' )
    expect( sock._logger.debug ).args( str, 0, 10, 'peer' )
    expect( sock._flag_activity )

    assert_true( sock._write_cb() )
    assert_equals( deque(['data1','data2']), sock._write_buf )

  def test_write_cb_when_other_environment_error_raised(self):
    sock = EventSocket()
    sock._sock = mock()
    sock._peername = 'peer'
    sock._logger = mock()
    sock._debug = True
    sock._parent_output_empty_cb = mock()  # assert not called
    sock._write_buf = deque(['data1','data2'])

    expect( sock._sock.send ).args( 'data1' ).raises(
      EnvironmentError(errno.ECONNABORTED,'try again') )

    assert_raises( EnvironmentError, sock._write_cb )

  def test_inactive_cb(self):
    sock = EventSocket()
    expect( sock.close )
    sock._inactive_cb()
    assert_equals( "error closing inactive socket", sock._error_msg )

  def test_flag_activity(self):
    sock = EventSocket()
    sock._inactive_event = mock()
    sock._inactive_timeout = 42
    
    expect( sock._inactive_event.delete )
    expect( eventsocket.event.timeout ).args( 42, sock._protected_cb, sock._inactive_cb ).returns( 'doitagain' )

    sock._flag_activity()
    assert_equals( 'doitagain', sock._inactive_event )

  def test_write_when_closed(self):
    sock = EventSocket()
    sock._closed = True

    assert_raises( socket.error, sock.read )

  def test_write_when_write_event_and_not_pending(self):
    sock = EventSocket()
    sock._write_event = mock()
    
    expect( sock._write_event.pending ).returns( False )
    expect( sock._write_event.add )
    expect( sock._flag_activity )

    sock.write( 'foo' )
    assert_equals( deque(['foo']), sock._write_buf )

  def test_write_when_write_event_is_pending_and_debugging(self):
    sock = EventSocket()
    sock._write_event = mock()
    sock._peername = 'peername'
    sock._write_buf = deque(['data'])
    sock._debug = 2
    sock._logger = mock()
    
    expect( sock._write_event.pending ).returns( True )
    expect( sock._logger.debug ).args(str, 3, 7, 'peername')
    expect( sock._flag_activity )

    sock.write( 'foo' )
    assert_equals( deque(['data', 'foo']), sock._write_buf )

  def test_read_when_closed(self):
    sock = EventSocket()
    sock._closed = True

    assert_raises( socket.error, sock.read )

  def test_read(self):
    sock = EventSocket()
    sock._read_buf = bytearray('datas')
    assert_equals( bytearray('datas'), sock.read() )
    assert_equals( bytearray(), sock._read_buf )

  def test_buffer_when_bytearray(self):
    sock = EventSocket()
    sock.buffer( bytearray('foo') )
    assert_equals( bytearray('foo'), sock._read_buf )

  def test_buffer_when_string(self):
    sock = EventSocket()
    sock._read_buf = bytearray('data')
    sock.buffer( 'foo' )
    assert_equals( bytearray('datafoo'), sock._read_buf )
