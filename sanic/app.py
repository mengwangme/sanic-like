from os import set_inheritable
from socket import socket, SOL_SOCKET, SO_REUSEADDR
from asyncio import get_event_loop
from inspect import isawaitable, stack, getmodulename
from multiprocessing import Process, Event
from signal import signal, SIGTERM, SIGINT
from traceback import format_exc
import logging


from sanic.config import Config
from sanic.exceptions import Handler, ServerError
from sanic.log import log
from sanic.response import HTTPResponse
from sanic.server import serve, HttpProtocol


class Sanic:
    def __init__(self, name=None, router=None,
                 error_handler=None, logger=None):
        if logger is None:
            logging.basicConfig(
                level=logging.INFO,
                format="%(asctime)s: %(levelname)s: %(message)s"
            )
        if name is None:
            frame_records = stack()[1]
            name = getmodulename(frame_records[1])
        self.name = name
        # self.router = router or Router()                    # 路由
        self.error_handler = error_handler or Handler(self)   # 错误处理
        self.config = Config()                                # 默认配置项
        # self.request_middleware = deque()
        # self.response_middleware = deque()
        # self.blueprints = {}
        # self._blueprint_order = []
        self.loop = None
        self.debug = None
        self.sock = None
        self.processes = None


    # -------------------------------------------------------------------- #
    # 处理请求
    # -------------------------------------------------------------------- #

    # def converted_response_type(self, response):
    #     pass

    async def handle_request(self, request, response_callback):
        """
        从 HTTP 服务器获取请求，并发送可异步的响应对象，
        因为 HTTP 服务器只期望发送响应对象，所以需要在这里进行异常处理
        :param request: HTTP 请求对象
        :param response_callback: 可异步的 response 回调函数
        """
        try:
            # -------------------------------------------- #
            # Request Middleware
            # -------------------------------------------- #

            response = False


            if not response:
                # -------------------------------------------- #
                # 执行处理器
                # -------------------------------------------- #

                # Fetch handler from router
                handler, args, kwargs = self.router.get(request)
                if handler is None:
                    raise ServerError(
                        ("'None' was returned while requesting a "
                         "handler from the router"))




                # Run response handler
                response = handler(request, *args, **kwargs)
                if isawaitable(response):
                    response = await response

        except Exception as e:
            # -------------------------------------------- #
            # 生成响应失败
            # -------------------------------------------- #

            try:
                response = self.error_handler.response(request, e)  # 异常处理部分
                if isawaitable(response):
                    response = await response   # 异步返回异常
            except Exception as e:
                if self.debug:
                    response = HTTPResponse(
                        "Error while handling error: {}\nStack: {}".format(
                            e, format_exc()))
                else:
                    response = HTTPResponse(
                        "An error occured while handling an error")

        # 回调函数处理 response
        response_callback(response)

    # -------------------------------------------------------------------- #
    # 执行
    # -------------------------------------------------------------------- #

    def run(self, host="127.0.0.1", port=8000, debug=False, sock=None,
            workers=1, loop=None, protocol=HttpProtocol, backlog=100,
            stop_event=None):
        """
        运行 HTTP 服务器并一直监听，直到收到键盘终端操作或终止信号。
        在终止时，在关闭时释放所有连接。
        :param host: 服务器地址
        :param port: 服务器端口
        :param debug: 开启 debug 输出
        :param sock: 服务器接受数据的套接字
        :param workers: 进程数
        received before it is respected
        :param loop: 异步事件循环
        :param protocol: 异步协议子类
        """
        self.error_handler.debug = True
        self.debug = debug
        self.loop = loop

        # 配置 server 参数
        server_settings = {
            'protocol': protocol,
            'host': host,
            'port': port,
            'sock': sock,
            'debug': debug,
            'request_handler': self.handle_request,
            'error_handler': self.error_handler,
            'request_timeout': self.config.REQUEST_TIMEOUT,
            'request_max_size': self.config.REQUEST_MAX_SIZE,
            'loop': loop,
            'backlog': backlog
        }

        if debug:
            log.setLevel(logging.DEBUG)

        # 启动服务进程
        log.info('Goin\' Fast @ http://{}:{}'.format(host, port))

        try:
            if workers == 1:
                serve(**server_settings)    # 传入 server 参数
            else:
                log.info('Spinning up {} workers...'.format(workers))

                self.serve_multiple(server_settings, workers, stop_event)

        except Exception as e:
            log.exception(
                'Experienced exception while trying to serve')

        log.info("Server Stopped")

    def stop(self):
        """
        停止服务
        """
        if self.processes is not None:
            for process in self.processes:
                process.terminate()
            self.sock.close()
        get_event_loop().stop()


    def serve_multiple(self, server_settings, workers, stop_event=None):
        """
        同时启动多个服务器进程。一直监听直到收到键盘终端操作或终止型号。
        在终止时，在关闭时释放所有连接。
        :param server_settings: 服务配置参数
        :param workers: 进程数
        :param stop_event: 终止事件
        :return:
        """
        server_settings['reuse_port'] = True

        # Create a stop event to be triggered by a signal
        if stop_event is None:
            stop_event = Event()
        signal(SIGINT, lambda s, f: stop_event.set())
        signal(SIGTERM, lambda s, f: stop_event.set())

        self.sock = socket()
        self.sock.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1)
        self.sock.bind((server_settings['host'], server_settings['port']))
        set_inheritable(self.sock.fileno(), True)
        server_settings['sock'] = self.sock
        server_settings['host'] = None
        server_settings['port'] = None

        self.processes = []
        for _ in range(workers):
            process = Process(target=serve, kwargs=server_settings)
            process.daemon = True
            process.start()
            self.processes.append(process)

        for process in self.processes:
            process.join()

        # 上面的进程直到它们停止前将会阻塞
        self.stop()
