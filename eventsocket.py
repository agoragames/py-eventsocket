"""
A socket wrapper that uses Event IO.
"""

import socket
import event
import time
import logging
import errno
import traceback
import os
from collections import deque

# TODO: Use new io objects from 2.6
# 26 July 10 - I looked into this and a potential problem with io.StringIO is
# that it assumes all text is unicode.  Without a full test and probably lots
# of code updated elsewhere, the older StringIO is probably the better choice
# to fix the bug @AW
#   https://agora.lighthouseapp.com/projects/47111/tickets/628-odd-amqp-error
from cStringIO import StringIO

class EventSocket(object):
  """
  A socket wrapper which uses libevent.
  """

  def __init__( self, family=socket.AF_INET, type=socket.SOCK_STREAM, \
                protocol=socket.IPPROTO_IP, read_cb=None, accept_cb=None, \
                close_cb=None, error_cb=None, output_empty_cb=None, sock=None, \
                debug=False, logger=None, max_read_buffer=0, **kwargs):
    """
    Initialize the socket.  If no read_cb defined, socket will only be used
    for reading.  If this socket will be used for accepting new connections,
    set read_cb here and it will be passed to new sockets.  You can also set
    accept_cb and be notified with an EventSocket object on accept().  The
    error_cb will be called if there are any errors on the socket.  The args
    to it will be this socket, an error message, and an optional exception.
    The close_cb will be called when this socket closes, with this socket as
    its argument.  If needed, you can wrap an existing socket by setting the
    sock argument to a socket object.
    """
    self._debug = debug
    self._logger = logger
    if self._debug and not self._logger:
      print 'WARNING: to debug EventSocket, must provide a logger'
      self._debug = False

    # There various events we may or may not schedule    
    self._read_event = None
    self._write_event = None
    self._accept_event = None
    self._connect_event = None
    self._pending_read_cb_event = None

    # Cache the peername so we can include it in logs even if the socket
    # is closed.  Note that connect() and bind() have to be the ones to do
    # that work.
    self._peername = 'unknown'

    if sock:
      self._sock = sock
  
      try:
        self._peername = "%s:%d"%self._sock.getpeername()
        # Like connect(), only initialize these if the socket is already connected.
        self._read_event = event.read( self._sock, self._protected_cb, self._read_cb )
        self._write_event = event.write( self._sock, self._protected_cb, self._write_cb )
      except socket.error, e:
        # unconnected
        pass
    else:
      self._sock = socket.socket(family, type, protocol)

    # wholesale binding of stuff we don't need to alter or intercept
    self.listen = self._sock.listen
    self.setsockopt = self._sock.setsockopt
    self.fileno = self._sock.fileno
    self.getpeername = self._sock.getpeername
    self.getsockname = self._sock.getsockname
    self.getsockopt = self._sock.getsockopt
    self.setblocking = self._sock.setblocking  # is this correct?
    self.settimeout = self._sock.settimeout
    self.gettimeout = self._sock.gettimeout
    self.shutdown = self._sock.shutdown

    self._max_read_buffer = max_read_buffer
    #self._write_buf = []
    self._write_buf = deque()
    #self._read_buf = StringIO()
    self._read_buf = bytearray()

    self._parent_accept_cb = accept_cb
    self._parent_read_cb = read_cb
    self._parent_error_cb = error_cb
    self._parent_close_cb = close_cb
    self._parent_output_empty_cb = output_empty_cb

    # This is the pending global error message.  It's sort of a hack, but it's
    # used for __protected_cb in much the same way as errno.  This prevents
    # having to pass an error message around, when the best way to do that is
    # via kwargs that the event lib is itself trying to interpret and won't
    # allow to pass to __protected_cb.
    self._error_msg = None
    self._closed = False

    self._inactive_event = None
    self.set_inactive_timeout( 0 )

  @property
  def closed(self):
    '''
    Return whether this socket is closed.
    '''
    return self._closed

  def close(self):
    """
    Close the socket.
    """
    # if self._debug:
    #   self._logger.debug(\
    #     "closing connection %s to %s"%(self._sock.getsockname(), self._peername) )

    # Unload all our events
    if self._read_event:
      self._read_event.delete()
      self._read_event = None
    if self._accept_event:
      self._accept_event.delete()
      self._accept_event = None
    if self._inactive_event:
      self._inactive_event.delete()
      self._inactive_event = None
    if self._write_event:
      self._write_event.delete()
      self._write_event = None
    if self._connect_event:
      self._connect_event.delete()
      self._connect_event = None

    if self._sock:
      self._sock.close()
      self._sock = None
    
    # Flush any pending data to the read callbacks as appropriate.  Do this
    # manually as there is a chance for the following race condition to occur:
    #   pending data read by cb
    #   callback reads 1.1 messages, re-buffers .1 msg back
    #   callback disconnects from socket based on message, calling close()
    #   we get back to this code and find there's still data in the input buffer
    #     and the read cb hasn't been cleared.  ruh roh.
    #if self._parent_read_cb and self._read_buf.tell()>0:
    if self._parent_read_cb and len(self._read_buf)>0:
      cb = self._parent_read_cb
      self._parent_read_cb = None
      self._error_msg = "error processing remaining socket input buffer"
      self._protected_cb( cb, self )

    # Only mark as closed after socket is really closed, we've flushed buffered
    # input, and we're calling back to close handlers.
    self._closed = True
    if self._parent_close_cb:
      self._parent_close_cb( self )
    
    if self._pending_read_cb_event: 
      self._pending_read_cb_event.delete()
      self._pending_read_cb_event = None
    
    if self._inactive_event:
      self._inactive_event.delete()
      self._inactive_event = None
    
    # Delete references to callbacks to help garbage collection
    self._parent_accept_cb = None
    self._parent_read_cb = None
    self._parent_error_cb = None
    self._parent_close_cb = None
    self._parent_output_empty_cb = None
    
    # Clear buffers
    self._write_buf = None
    self._read_buf = None

  def accept(self):
    """
    No-op as we no longer perform blocking accept calls.
    """
    pass

  def _set_read_cb(self, cb):
    """
    Set the read callback.  If there's data in the output buffer, immediately
    setup a call.
    """
    self._parent_read_cb = cb
    #if self._read_buf.tell()>0 and self._parent_read_cb!=None and self._pending_read_cb_event==None:
    if len(self._read_buf)>0 and self._parent_read_cb!=None and self._pending_read_cb_event==None:
      self._pending_read_cb_event = \
        event.timeout( 0, self._protected_cb, self._parent_read_timer_cb )

  # Allow someone to change the various callbacks.
  read_cb =   property( fset=_set_read_cb )
  accept_cb = property( fset=lambda self,func: setattr(self, '_parent_accept_cb', func ) )
  close_cb =  property( fset=lambda self,func: setattr(self, '_parent_close_cb', func ) )
  error_cb =  property( fset=lambda self,func: setattr(self, '_parent_error_cb', func ) )
  output_empty_cb = property( fset=lambda self,func: setattr(self, '_parent_output_empty_cb',func) )

  def bind(self, *args):
    """
    Bind the socket.
    """
    if self._debug:
      self._logger.debug( "binding to %s", str(args) )

    self._sock.bind( *args )
    self._peername = "%s:%d"%self.getsockname()

    self._accept_event = event.read( self, self._protected_cb, self._accept_cb )

  def connect(self, *args, **kwargs):
    '''
    Connect to the socket. If currently non-blocking, will return immediately
    and call close_cb when the timeout is reached. If timeout_at is a float,
    will wait until that time and then call the close_cb. Otherwise, it will
    set timeout_at as time()+timeout, where timeout is a float argument or the
    current timeout value of the socket. The check interval for successful
    connection on a non-blocking socket is 100ms.

    IMPORTANT: If you want the socket to timeout at all in non-blocking mode,
    you *must* pass in either a relative timout in seconds, or an absolute 
    value in timeout_at. Otherwise, the socket will forever try to connect. 

    Passes *args on to socket.connect_ex, and **kwargs are used for local
    control of `timeout` and `timeout_at`.
    '''
    timeout_at = kwargs.get('timeout_at')
    timeout = kwargs.get('timeout')
    if not isinstance(timeout_at, float):
      if not isinstance(timeout,(int,long,float)):
        timeout = self._sock.gettimeout()
      if timeout>0:
        timeout_at = time.time()+timeout

    self._connect_cb(timeout_at, *args, immediate_raise=True)

  def _connect_cb(self, timeout_at, *args, **kwargs):
    '''
    Local support for synch and asynch connect. Required because 
    `event.timeout` doesn't support kwargs. They are spec'd though so that
    we can branch how exceptions are handled. 
    '''
    err = self._sock.connect_ex( *args )

    if not err:
      self._peername = "%s:%d"%self._sock.getpeername()
      self._read_event = event.read( self._sock, self._protected_cb, self._read_cb )
      self._write_event = event.write( self._sock, self._protected_cb, self._write_cb )
      
      if self._connect_event:
        self._connect_event.delete()
        self._connect_event = None

    elif err in (errno.EINPROGRESS,errno.EALREADY):
      # Only track timeout if we're about to re-schedule. Should only receive
      # these on a non-blocking socket.
      if isinstance(timeout_at,float) and time.time()>timeout_at:
        self._error_msg = 'timeout connecting to %s'%str(args)
        self.close()
        return
      
      if self._connect_event:
        self._connect_event.delete()

      # Checking every 100ms seems to be a reasonable amount of frequency. If
      # requested this too can be configurable.
      self._connect_event = event.timeout(0.1, self._connect_cb, 
        timeout_at, *args)
    else:
      if self._connect_event:
        self._connect_event.delete()

      self._error_msg = os.strerror(err)
      serr = socket.error( err, self._error_msg )

      if kwargs.get('immediate_raise'):
        raise serr
      else:
        self._handle_error( serr )

  def set_inactive_timeout(self, t):
    """
    Set the inactivity timeout.  If is None or 0, there is no activity timeout.
    If t>0 then socket will automatically close if there has been no activity
    after t seconds (float supported).  Will raise TypeError if <t> is invalid.
    """
    if t==None or t==0:
      if self._inactive_event:
        self._inactive_event.delete()
        self._inactive_event = None
      self._inactive_timeout = 0
    elif isinstance(t,(int,long,float)):
      if self._inactive_event:
        self._inactive_event.delete()
      self._inactive_event = event.timeout( t, self._inactive_cb )
      self._inactive_timeout = t
    else:
      raise TypeError( "invalid timeout %s"%(str(t)) )
   
  ### Private support methods
  def _handle_error(self, exc):
    '''
    Gracefully handle errors.
    '''
    if self._parent_error_cb:
      if self._error_msg!=None:
        self._parent_error_cb( self, self._error_msg, exc )
      else:
        self._parent_error_cb( self, "unknown error", exc )
    else:
      if self._error_msg!=None:
        msg = "unhandled error %s"%(self._error_msg)
      else:
        msg = "unhandled unknown error"
      if self._logger:
        self._logger.error( msg, exc_info=True )
      else:
        traceback.print_exc()
    
  def _protected_cb(self, cb, *args, **kwargs):
    """
    Wrap any callback from libevent so that we can be sure that exceptions are
    handled and errors forwarded to error_cb.
    """
    rval = None

    try:
      rval = cb(*args, **kwargs)
    except Exception, e:
      self._handle_error( e )

    self._error_msg = None
    return rval

  def _accept_cb(self):
    """
    Accept callback from libevent.
    """
    self._error_msg = "error accepting new socket"
    (conn, addr) = self._sock.accept()
    if self._debug:
      self._logger.debug("accepted connection from %s"%(str(addr)))


    evsock = EventSocket( read_cb=self._parent_read_cb,
                            error_cb=self._parent_error_cb,
                            close_cb=self._parent_close_cb, sock=conn,
                            debug=self._debug, logger=self._logger,
                            max_read_buffer=self._max_read_buffer )

    if self._parent_accept_cb:
      # 31 march 09 aaron - We can't call accept callback asynchronously in the
      # event that the socket is quickly opened and closed.  What happens is
      # that a read event gets scheduled before __parent_accept_cb is run, and
      # since the socket is closed, it calls the __parent_close_cb.  If the
      # socket has not been correctly initialized though, we may encounter
      # errors if the close_cb is expected to be changed during the accept
      # callback.  This is arguably an application-level problem, but handling
      # that situation entirely asynchronously would be a giant PITA and prone
      # to bugs.  We'll avoid that.
      self._protected_cb( self._parent_accept_cb, evsock )

    # Still reschedule event even if there was an error.
    return True

  def _read_cb(self):
    """
    Read callback from libevent.
    """
    # We should be able to use recv_into for speed and efficiency, but sadly
    # this was broken after 2.6.1 http://bugs.python.org/issue7827
    self._error_msg = "error reading from socket"
    data = self._sock.recv( self.getsockopt(socket.SOL_SOCKET,socket.SO_RCVBUF) )
    if len(data)>0:
      if self._debug:
        self._logger.debug( "read %d bytes from %s"%(len(data), self._peername) )
      # 23 Feb 09 aaron - There are cases where the client will have started
      # pushing data right away, and there's a chance that async handling of
      # accept will cause data to be read before the callback function has been
      # set.  I prefer to ignore data if no read callback defined, but it's
      # better to just limit the overall size of the input buffer then to use
      # a synchronous callback to __parent_accept_cb.
      # TODO: So what is the best way of handling this problem, and if sticking
      # with a max input buffer size, what's the correct algorithm?  Maybe better
      # approach is to raise a notice to a callback and let the callback decide
      # what to do.
      self._flag_activity()
      self._read_buf.extend( data )

      if self._max_read_buffer and len(self._read_buf) > self._max_read_buffer:
        if self._debug:
          self._logger.debug( "buffer for %s overflowed!"%(self._peername) )

        # Clear the input buffer so that the callback flush code isn't called in close
        self._read_buf = bytearray()
        self.close()
        return None
  
      # Callback asynchronously so that priority is given to libevent to
      # allocate time slices.
      if self._parent_read_cb!=None and self._pending_read_cb_event==None:
        self._pending_read_cb_event = \
          event.timeout( 0, self._protected_cb, self._parent_read_timer_cb )

    else:
      self.close()
      return None
    return True

  def _parent_read_timer_cb(self):
    """
    Callback when we want the parent to read buffered data.
    """
    # Shouldn't need to check closed state because all events should be
    # cancelled, but there seems to be a case where that can happen so deal
    # with it gracefully. Possibly a bug or edge case in libevent when tons
    # of events are in play as this only happened during extreme testing.
    if not self._closed:
      self._error_msg = "error processing socket input buffer"

      # allow for __close_cb and __read_cb to do their thing.
      self._pending_read_cb_event = None

      # Catch edge case where this could have been cleared after _read_cb
      if self._parent_read_cb:
        self._parent_read_cb( self )

    # never reschedule
    return None

  def _write_cb(self):
    """
    Write callback from libevent.
    """
    self._error_msg = "error writing socket output buffer"

    # If no data, don't reschedule
    if len(self._write_buf)==0:
      return None

    # 7 April 09 aaron - Changed this algorithm so that we continually send
    # data from the buffer until the socket didn't accept all of it, then
    # break.  This should be a bit faster.
    if self._debug:
      total_sent = 0
      total_len = sum( map(len,self._write_buf) )

    while len(self._write_buf)>0:
      cur = self._write_buf.popleft()
      
      # Catch all env errors since that should catch OSError, IOError and
      # socket.error.
      try:
        bytes_sent = self._sock.send( cur )
      except EnvironmentError, e:
        # For now this seems to be the only error that isn't fatal.  It seems
        # to be used only for nonblocking sockets and implies that it can't
        # buffer any more data right now.
        if e.errno==errno.EAGAIN:
          self._write_buf.appendleft( cur )
          if self._debug:
            self._logger.debug( '"%s" raised, waiting to flush to %s', e, self._peername )
          break
        else:
          raise

      if self._debug:
        total_sent += bytes_sent

      if bytes_sent < len(cur):
        # keep the first entry and set to all remaining bytes.
        self._write_buf.appendleft( cur[bytes_sent:] )
        break
    
    if self._debug:
      self._logger.debug( "wrote %d/%d bytes to %s", total_sent,total_len,self._peername )
      
    # also flag activity here?  might not be necessary, but in some cases the
    # timeout could still be small enough to trigger between accesses to the
    # socket output.
    self._flag_activity()
    
    if len(self._write_buf)>0:
      return True

    if self._parent_output_empty_cb!=None:
      self._parent_output_empty_cb( self )
    return None

  def _inactive_cb(self):
    """
    Timeout when a socket has been inactive for a long time.
    """
    self._error_msg = "error closing inactive socket"
    self.close()

  def _flag_activity(self):
    """
    Flag that this socket is active.
    """
    # is there a better way of reseting a timer?
    if self._inactive_event:
      self._inactive_event.delete()
      self._inactive_event = event.timeout( self._inactive_timeout, self._protected_cb, self._inactive_cb )

  def write(self, data):
    """
    Write some data.  Will raise socket.error if connection is closed.
    """
    if self._closed:
      raise socket.error('write error: socket is closed')

    # Always append the data to the write buffer, even if we're not connected
    # yet.  
    self._write_buf.append( data )

    # 21 July 09 aaron - I'm not sure if this has a significant benefit, but in
    # trying to improve throughput I confirmed that this doesn't break anything
    # and keeping the event queue cleaner is certainly good.
    if self._write_event and not self._write_event.pending():
      self._write_event.add()
  
    if self._debug > 1:
      self._logger.debug("buffered %d bytes (%d total) to %s",
        len(data), sum(map(len,self._write_buf)), self._peername )

    # Flag activity here so we don't timeout in case that event is ready to
    # fire and we're just now writing.
    self._flag_activity()

  def read(self):
    """
    Return the current read buffer.  Will return a bytearray object.
    """
    if self._closed:
      raise socket.error('read error: socket is closed')

    rval = self._read_buf
    self._read_buf = bytearray()
    return rval

  def buffer(self, s):
    '''
    Re-buffer some data. If it's a bytearray will assign directly as the current
    input buffer, else will add to the current buffer. Assumes that re-buffered
    data is happening in the same cycle as read() was called, as anything other
    than that would be nearly impossible to handle inside an application.
    '''
    if isinstance(s, bytearray):
      self._read_buf = s
    else:
      self._read_buf.extend( s )
