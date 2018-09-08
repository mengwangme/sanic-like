from cgi import parse_header
from collections import namedtuple
from http.cookies import SimpleCookie
from httptools import parse_url
from urllib.parse import parse_qs
from ujson import loads as json_loads

from sanic.exceptions import InvalidUsage
from sanic.log import log


DEFAULT_HTTP_CONTENT_TYPE = "application/octet-stream"
# 基于 HTP/1.1: https://www.w3.org/Protocols/rfc2616/rfc2616-sec7.html#sec7.2.1
# 若媒体类型仍未知，则将其作为默认类型 "application/octet-stream"


class RequestParameters(dict):
    """
    字典存储请求参数
    """

    def get(self, name, default=None):
        """除了给定key是列表时，只返回指定key的第一个值"""
        return super().get(name, [default])[0]

    def getlist(self, name, default=None):
        """返回整个列表"""
        return super().get(name, default)


class Request(dict):
    """一个 HTTP 请求的属性，包括 URL, headers 等"""

    # 插槽，阻止动态创建属性
    __slots__ = (
        'url', 'headers', 'version', 'method', '_cookies',
        'query_string', 'body',
        'parsed_json', 'parsed_args', 'parsed_form', 'parsed_files',
    )

    def __init__(self, url_bytes, headers, version, method):
        url_parsed = parse_url(url_bytes)
        self.url = url_parsed.path.decode('utf-8')
        self.headers = headers
        self.version = version
        self.method = method
        self.query_string = None
        if url_parsed.query:
            self.query_string = url_parsed.query.decode('utf-8')

        # Init but do not inhale
        self.body = None
        self.parsed_json = None
        self.parsed_form = None
        self.parsed_files = None
        self.parsed_args = None
        self._cookies = None

    @property
    def json(self):
        """
        使用 json 序列化消息体
        """
        if self.parsed_json is None:
            try:
                self.parsed_json = json_loads(self.body)
            except Exception:   # 无效用法
                raise InvalidUsage("Failed when parsing body as json")

        return self.parsed_json

    @property
    def token(self):
        """
        返回 request 头部的 token
        """
        auth_header = self.headers.get('Authorization')
        if auth_header is not None:
            return auth_header.split()[1]
        return auth_header

    @property
    def form(self):
        """
        返回解析头部表单的信息
        """
        if self.parsed_form is None:
            self.parsed_form = RequestParameters()
            self.parsed_files = RequestParameters()
            content_type = self.headers.get(
                'Content-Type', DEFAULT_HTTP_CONTENT_TYPE)  # 设为默认的媒体类型
            content_type, parameters = parse_header(content_type)
            try:
                if content_type == 'application/x-www-form-urlencoded': # GET 方式提交表单
                    self.parsed_form = RequestParameters(
                        parse_qs(self.body.decode('utf-8')))
                elif content_type == 'multipart/form-data': # POST 方式提交表单
                    boundary = parameters['boundary'].encode('utf-8')
                    self.parsed_form, self.parsed_files = (
                        parse_multipart_form(self.body, boundary))  # 此解析方法后面实现
            except Exception:
                log.exception("Failed when parsing form")   # 日志记录异常信息

        return self.parsed_form

    @property
    def files(self):
        if self.parsed_files is None:
            self.form  # 通过表单获取文件

        return self.parsed_files

    @property
    def args(self):
        if self.parsed_args is None:
            if self.query_string:
                self.parsed_args = RequestParameters(
                    parse_qs(self.query_string))
            else:
                self.parsed_args = {}

        return self.parsed_args

    @property
    def cookies(self):
        if self._cookies is None:
            cookie = self.headers.get('Cookie') or self.headers.get('cookie')
            if cookie is not None:
                cookies = SimpleCookie()
                cookies.load(cookie)
                self._cookies = {name: cookie.value
                                 for name, cookie in cookies.items()}
            else:
                self._cookies = {}
        return self._cookies


# 定义文件为 namedtuple
File = namedtuple('File', ['type', 'body', 'name'])


# 解析 POST 请求表单
def parse_multipart_form(body, boundary):
    """
    解析请求消息体并返回字段和文件
    :param body: 请求消息体
    :param boundary: 分隔符
    """
    files = RequestParameters()
    fields = RequestParameters()

    form_parts = body.split(boundary)
    for form_part in form_parts[1:-1]:
        file_name = None
        file_type = None
        field_name = None
        line_index = 2
        line_end_index = 0
        while not line_end_index == -1:
            line_end_index = form_part.find(b'\r\n', line_index)
            form_line = form_part[line_index:line_end_index].decode('utf-8')
            line_index = line_end_index + 2

            if not form_line:
                break

            colon_index = form_line.index(':')
            form_header_field = form_line[0:colon_index]
            form_header_value, form_parameters = parse_header(
                form_line[colon_index + 2:])

            if form_header_field == 'Content-Disposition':
                if 'filename' in form_parameters:
                    file_name = form_parameters['filename']
                field_name = form_parameters.get('name')
            elif form_header_field == 'Content-Type':
                file_type = form_header_value

        post_data = form_part[line_index:-4]
        if file_name or file_type:
            file = File(type=file_type, name=file_name, body=post_data)
            if field_name in files:
                files[field_name].append(file)
            else:
                files[field_name] = [file]
        else:
            value = post_data.decode('utf-8')
            if field_name in fields:
                fields[field_name].append(value)
            else:
                fields[field_name] = [value]

    return fields, files
