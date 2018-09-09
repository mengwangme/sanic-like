from aiofiles import open as open_async
from mimetypes import guess_type
from os import path

from ujson import dumps as json_dumps

from sanic.cookies import CookieJar

# 全部状态码
ALL_STATUS_CODES = {
    100: b'Continue',
    101: b'Switching Protocols',
    102: b'Processing',
    200: b'OK',
    201: b'Created',
    202: b'Accepted',
    203: b'Non-Authoritative Information',
    204: b'No Content',
    205: b'Reset Content',
    206: b'Partial Content',
    207: b'Multi-Status',
    208: b'Already Reported',
    226: b'IM Used',
    300: b'Multiple Choices',
    301: b'Moved Permanently',
    302: b'Found',
    303: b'See Other',
    304: b'Not Modified',
    305: b'Use Proxy',
    307: b'Temporary Redirect',
    308: b'Permanent Redirect',
    400: b'Bad Request',
    401: b'Unauthorized',
    402: b'Payment Required',
    403: b'Forbidden',
    404: b'Not Found',
    405: b'Method Not Allowed',
    406: b'Not Acceptable',
    407: b'Proxy Authentication Required',
    408: b'Request Timeout',
    409: b'Conflict',
    410: b'Gone',
    411: b'Length Required',
    412: b'Precondition Failed',
    413: b'Request Entity Too Large',
    414: b'Request-URI Too Long',
    415: b'Unsupported Media Type',
    416: b'Requested Range Not Satisfiable',
    417: b'Expectation Failed',
    422: b'Unprocessable Entity',
    423: b'Locked',
    424: b'Failed Dependency',
    426: b'Upgrade Required',
    428: b'Precondition Required',
    429: b'Too Many Requests',
    431: b'Request Header Fields Too Large',
    500: b'Internal Server Error',
    501: b'Not Implemented',
    502: b'Bad Gateway',
    503: b'Service Unavailable',
    504: b'Gateway Timeout',
    505: b'HTTP Version Not Supported',
    506: b'Variant Also Negotiates',
    507: b'Insufficient Storage',
    508: b'Loop Detected',
    510: b'Not Extended',
    511: b'Network Authentication Required'
}


class HTTPResponse:
    __slots__ = ('body', 'status', 'content_type', 'headers', '_cookies')

    def __init__(self, body=None, status=200, headers=None,
                 content_type='text/plain', body_bytes=b''):
        self.content_type = content_type    # 内容类型

        if body is not None:
            try:
                self.body = body.encode('utf-8')    # 默认编码
            except AttributeError:
                self.body = str(body).encode('utf-8')   # 异常编码，尝试转换成字符串
        else:
            self.body = body_bytes

        self.status = status            # 状态码
        self.headers = headers or {}    # 头部
        self._cookies = None            # cookie 内容

    def output(self, version="1.1", keep_alive=False, keep_alive_timeout=None):
        """
        返回一个标准的 HTTP 响应
        """
        timeout_header = b''
        if keep_alive and keep_alive_timeout: # 存活时间
            timeout_header = b'Keep-Alive: timeout=%d\r\n' % keep_alive_timeout

        headers = b''
        if self.headers:    # 头部信息
            for name, value in self.headers.items():
                try:
                    headers += (
                        b'%b: %b\r\n' % (name.encode(), value.encode('utf-8')))
                except AttributeError:
                    headers += (
                        b'%b: %b\r\n' % (
                            str(name).encode(), str(value).encode('utf-8')))

        status = ALL_STATUS_CODES.get(self.status)  # 获得状态码及其相应文本信息

        # 规范格式返回响应
        return (b'HTTP/%b %d %b\r\n'
                b'Content-Type: %b\r\n'
                b'Content-Length: %d\r\n'
                b'Connection: %b\r\n'
                b'%b%b\r\n'
                b'%b') % (
            version.encode(),           # HTTP 协议版本号
            self.status,                # HTTP 状态码
            status,                     # HTTP 状态码信息
            self.content_type.encode(), # HTTP 内容格式
            len(self.body),             # HTTP 内容长度
            b'keep-alive' if keep_alive else b'close',  # HTTP 连接状态
            timeout_header,             # 超时头部
            headers,                    # 头部
            self.body                   # HTTP 响应内容部分
        )

    # 返回 cookie 部分
    @property
    def cookies(self):
        if self._cookies is None:
            self._cookies = CookieJar(self.headers)
        return self._cookies

# HTTP 响应模块对外接口，根据 content_type 字段类型区分

# 返回 json 格式内容的 HTTP 响应
def json(body, status=200, headers=None):
    return HTTPResponse(json_dumps(body), headers=headers, status=status,
                        content_type="application/json")

# 返回 text 格式内容的 HTTP 响应
def text(body, status=200, headers=None):
    return HTTPResponse(body, status=status, headers=headers,
                        content_type="text/plain; charset=utf-8")

# 返回 html 格式内容的 HTTP 响应
def html(body, status=200, headers=None):
    return HTTPResponse(body, status=status, headers=headers,
                        content_type="text/html; charset=utf-8")

# 返回 file 格式内容的 HTTP 响应
async def file(location, mime_type=None, headers=None):
    """
    文件下载，通过 body_bytes 参数传递文件数据流
    异步实现：
        - 异步打开文件
        - 异步读取文件
    """
    filename = path.split(location)[-1]

    # 异步打开文件
    async with open_async(location, mode='rb') as _file:
        # 异步读取文件
        out_stream = await _file.read()

    # 文件类型
    mime_type = mime_type or guess_type(filename)[0] or 'text/plain'

    return HTTPResponse(status=200,
                        headers=headers,
                        content_type=mime_type,
                        body_bytes=out_stream)
