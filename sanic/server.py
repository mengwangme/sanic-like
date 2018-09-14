import asyncio
from functools import partial
from signal import SIGINT, SIGTERM
from time import time

import uvloop as async_loop # 使用 uvloop 替代 asyncio
from multidict import CIMultiDict
from httptools import HttpRequestParser
from httptools.parser.errors import HttpParserError

from sanic.log import log
from sanic.request import Request
from sanic.exceptions import ServerError, RequestTimeout, PayloadTooLarge, InvalidUsage


class Signal:
    stopped = False


current_time = None


class HttpProtocol(asyncio.Protocol):
    """
    HTTP 协议
    """
    # 插槽
    __slots__ = (
        # 事件循环, 连接
        'loop', 'transport', 'connections', 'signal',
        # 请求参数
        'parser', 'request', 'url', 'headers',
        # 请求配置
        'request_handler', 'request_timeout', 'request_max_size',
        # 连接管理
        '_total_request_size', '_timeout_handler', '_last_communication_time')

    def __init__(self, *, loop, request_handler, error_handler,
                 signal=Signal(), connections={}, request_timeout=60,
                 request_max_size=None):
        self.loop = loop                            # 事件循环
        self.transport = None
        self.request = None                         # 请求
        self.parser = None
        self.url = None                             # 预留的路径
        self.headers = None                         # 请求头
        self.signal = signal                        # 标志是否结束
        self.connections = connections              # 连接集合
        self.request_handler = request_handler      # 请求处理器
        self.error_handler = error_handler          # 出错处理器
        self.request_timeout = request_timeout      # 请求超时时间
        self.request_max_size = request_max_size    # 请求最大大小
        self._total_request_size = 0
        self._timeout_handler = None
        self._last_request_time = None
        self._request_handler_task = None

    # -------------------------------------------- #
    # 连接部分
    # -------------------------------------------- #

    def connection_made(self, transport):
        """
        创建连接
        """
        self.connections.add(self)
        self._timeout_handler = self.loop.call_later(
            self.request_timeout, self.connection_timeout)
        self.transport = transport
        self._last_request_time = current_time

    def connection_lost(self, exc):
        """
        丢失连接
        """
        self.connections.discard(self)
        self._timeout_handler.cancel()
        self.cleanup()

    def connection_timeout(self):
        """
        连接超时
        """
        time_elapsed = current_time - self._last_request_time   # 计算与上次请求间隔
        if time_elapsed < self.request_timeout: # 未超时
            time_left = self.request_timeout - time_elapsed
            self._timeout_handler = \
                self.loop.call_later(time_left, self.connection_timeout)
        else:   # 超时
            if self._request_handler_task:
                self._request_handler_task.cancel()
            exception = RequestTimeout('Request Timeout')
            self.write_error(exception)

    # -------------------------------------------- #
    # 解析部分
    # -------------------------------------------- #

    def data_received(self, data):
        """
        接受数据
        """
        self._total_request_size += len(data)
        if self._total_request_size > self.request_max_size:    # 请求数据过大
            # 在`exceptions.py`中添加 PayloadTooLarge 错误
            exception = PayloadTooLarge('Payload Too Large')
            self.write_error(exception)

        # 如果是第一次接受数据，创建 parser
        if self.parser is None:
            assert self.request is None
            self.headers = []
            self.parser = HttpRequestParser(self)

        # 解析请求
        try:
            self.parser.feed_data(data)
        except HttpParserError:
            exception = InvalidUsage('Bad Request')
            self.write_error(exception)

    def on_url(self, url):
        """
        获得 url
        """
        self.url = url

    def on_header(self, name, value):
        """
        补全 HTTP 请求的 head 信息
        """
        if name == b'Content-Length' and int(value) > self.request_max_size:
            exception = PayloadTooLarge('Payload Too Large')
            self.write_error(exception)

        self.headers.append((name.decode(), value.decode('utf-8')))

    def on_headers_complete(self):
        """
        写入 HTTP 请求 head 信息
        """
        # 远程地址
        remote_addr = self.transport.get_extra_info('peername')
        if remote_addr:
            self.headers.append(('Remote-Addr', '%s:%s' % remote_addr))

        # HTTP 请求 head
        self.request = Request(
            url_bytes=self.url,
            headers=CIMultiDict(self.headers),
            version=self.parser.get_http_version(),
            method=self.parser.get_method().decode()
        )

    def on_body(self, body):
        """
        写入 HTTP 请求 body
        """
        if self.request.body:
            self.request.body += body
        else:
            self.request.body = body

    def on_message_complete(self):
        """
        创建 task
        """
        self._request_handler_task = self.loop.create_task(
            self.request_handler(self.request, self.write_response))

    # -------------------------------------------- #
    # 响应部分
    # -------------------------------------------- #

    def write_response(self, response):
        """
        编写 HTTP 响应
        """
        try:
            keep_alive = self.parser.should_keep_alive() \
                            and not self.signal.stopped
            # 输出响应
            self.transport.write(
                response.output(
                    self.request.version, keep_alive, self.request_timeout))
            if not keep_alive:
                self.transport.close()
            else:
                # 记录接收到的数据
                self._last_request_time = current_time
                self.cleanup()
        except Exception as e:
            self.bail_out(
                "Writing response failed, connection closed {}".format(e))

    def write_error(self, exception):
        """
        编写 HTTP 错误响应
        """
        try:
            response = self.error_handler.response(self.request, exception)
            version = self.request.version if self.request else '1.1'
            self.transport.write(response.output(version))
            self.transport.close()
        except Exception as e:
            self.bail_out(
                "Writing error failed, connection closed {}".format(e))

    def bail_out(self, message):
        """
        记录异常辅助方法
        """
        exception = ServerError(message)
        self.write_error(exception)
        log.error(message)

    def cleanup(self):
        """
        清空请求字段
        """
        self.parser = None
        self.request = None
        self.url = None
        self.headers = None
        self._request_handler_task = None
        self._total_request_size = 0

    def close_if_idle(self):
        """
        若没有发生或接受请求，则关闭连接
        :return: boolean - True 为关, false 为保持开启
        """
        if not self.parser:
            self.transport.close()
            return True
        return False


def update_current_time(loop):
    """
    更新当前时间，当前时间是一个全局变量
    因为在每个 keep-alive 请求结束后需要更新请求超时时间
    """
    global current_time
    current_time = time()
    loop.call_later(1, partial(update_current_time, loop))





def serve(host, port, request_handler, error_handler, debug=False,
          request_timeout=60, sock=None, request_max_size=None,
          reuse_port=False, loop=None, protocol=HttpProtocol, backlog=100):
    """
    在一个独立进程中启动异步 HTTP 服务器.
    :param host: 服务器地址
    :param port: 服务器端口
    :param request_handler: 请求处理器
    :param error_handler: 异常处理器
    :param debug: 开启 debug 输出
    :param request_timeout: 以秒为单位，请求超时时间
    :param sock: 接受连接的套接字
    :param request_max_size: 大小以字节为单位，`None`代表无限制
    :param reuse_port: `True` for multiple workers
    :param loop: 异步事件循环
    :param protocol: 异步协议类的子类
    """
    # 创建事件循环
    loop = loop or async_loop.new_event_loop()
    asyncio.set_event_loop(loop)

    # 开启 debug
    if debug:
        loop.set_debug(debug)



    connections = set()
    signal = Signal()
    # 配置 server 参数
    server = partial(
        protocol,
        loop=loop,
        connections=connections,
        signal=signal,
        request_handler=request_handler,
        error_handler=error_handler,
        request_timeout=request_timeout,
        request_max_size=request_max_size,
    )

    # 创建 server 协程
    server_coroutine = loop.create_server(
        server,
        host,
        port,
        reuse_port=reuse_port,
        sock=sock,
        backlog=backlog
    )

    # 每分钟都 pull time，而不是在每个请求结束后
    loop.call_soon(partial(update_current_time, loop))

    try:
        http_server = loop.run_until_complete(server_coroutine)     # 启动协程
    except Exception:
        log.exception("Unable to start server")
        return



    # Register signals for graceful termination
    for _signal in (SIGINT, SIGTERM):
        loop.add_signal_handler(_signal, loop.stop)

    # 启动服务器
    try:
        loop.run_forever()
    finally:
        log.info("Stop requested, draining connections...")



        # 事件循环解说后释放所有连接
        http_server.close()
        loop.run_until_complete(http_server.wait_closed())

        # 再循环中完成所有 tasks
        signal.stopped = True
        for connection in connections:
            connection.close_if_idle()

        while connections:
            loop.run_until_complete(asyncio.sleep(0.1))



        loop.close()
