from traceback import format_exc

from sanic.response import text
from sanic.log import log


class SanicException(Exception):
    def __init__(self, message, status_code=None):
        super().__init__(message)
        if status_code is not None:
            self.status_code = status_code

class InvalidUsage(SanicException):
    """
    无效用法异常
    """
    status_code = 400

class ServerError(SanicException):
    """
    服务器异常
    """
    status_code = 500

class RequestTimeout(SanicException):
    """
    请求超时
    """
    status_code = 408

class PayloadTooLarge(SanicException):
    """
    请求数据大小超过限制
    """
    status_code = 413

class NotFound(SanicException):
    """
    无法找到目标
    """
    status_code = 404

# 异常处理器
class Handler:
    handlers = None

    def __init__(self, sanic):
        self.handlers = {}
        self.sanic = sanic

    def add(self, exception, handler):
        self.handlers[exception] = handler

    def response(self, request, exception):
        """
        获取并执行异常处理程序并返回响应
        """
        handler = self.handlers.get(type(exception), self.default)
        try:
            response = handler(request=request, exception=exception)
        except:
            if self.sanic.debug:    # 是否开启了 debug 模式，将会在后面代码讲到
                response_message = (
                    'Exception raised in exception handler "{}" '
                    'for uri: "{}"\n{}').format(
                        handler.__name__, request.url, format_exc())
                log.error(response_message)
                return text(response_message, 500)
            else:
                return text('An error occurred while handling an error', 500)
        return response

    def default(self, request, exception):
        """
        判断异常类型，如果是框架自身的异常，返回状态码 500
        """
        if issubclass(type(exception), SanicException):
            return text(
                'Error: {}'.format(exception),
                status=getattr(exception, 'status_code', 500))
        elif self.sanic.debug:
            response_message = (
                'Exception occurred while handling uri: "{}"\n{}'.format(
                    request.url, format_exc()))
            log.error(response_message)
            return text(response_message, status=500)
        else:
            return text(
                'An error occurred while generating the response', status=500)



