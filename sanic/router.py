import re
from collections import defaultdict, namedtuple
from functools import lru_cache

from sanic.config import Config
from sanic.exceptions import InvalidUsage, NotFound

# 路由元组
Route = namedtuple('Route', ['handler', 'methods', 'pattern', 'parameters'])
# 参数元组
Parameter = namedtuple('Parameter', ['name', 'cast'])

# 正则表达式，用于过滤数据类型
REGEX_TYPES = {
    'string': (str, r'[^/]+'),
    'int': (int, r'\d+'),
    'number': (float, r'[0-9\\.]+'),
    'alpha': (str, r'[A-Za-z]+'),
}


def url_hash(url):
    """
    辅助方法，计算 url 中`/`总数，
    """
    return url.count('/')


class RouteExists(Exception):
    """
    路由已存在
    """
    pass


class Router:
    """
    此路由支持附带参数和请求方式。
    Usage：
        @app.route('/my_url/<my_param:my_type>', methods=['GET', 'POST', ...])
        def my_route(request, my_param:my_type):
            do stuff...
    给的参数需要给定数据类型，若没有指定则默认为字符串类型。
    正则表达式同样可以作为数据类型来传递。
    赋予函数的实参始终为字符串，与数据类型无关。
    """
    routes_static = None            # 静态路由集合
    routes_dynamic = None           # 动态路由集和
    routes_always_check = None      # 检查路由列表

    def __init__(self):
        self.routes_all = {}        # 全部路由集合
        self.routes_static = {}     # 静态路由集合
        self.routes_dynamic = defaultdict(list) # 动态路由集合
        self.routes_always_check = []   # 检查路由列表
        # self.hosts = None

    def add(self, uri, methods, handler):
        """
        添加处理器到路由列表
        :param uri: 匹配的路径
        :param methods: 指定请求方式
        如没有定义 methods，则任意请求方式都可以
        :param handler: 处理请求函数
        """

        # 路由已存在
        if uri in self.routes_all:
            raise RouteExists("Route already registered: {}".format(uri))

        # 更快的查找字典
        if methods:
            methods = frozenset(methods)

        parameters = []
        properties = {"unhashable": None}

        def add_parameter(match):
            """
            添加参数，一共两种参数: NAME or NAME:PATTERN
            """
            name = match.group(1)
            pattern = 'string'
            if ':' in name:
                name, pattern = name.split(':', 1)

            default = (str, pattern)
            # 拉取先前设置的正则表达式
            _type, pattern = REGEX_TYPES.get(pattern, default)
            parameter = Parameter(name=name, cast=_type)
            parameters.append(parameter)

            if re.search('(^|[^^]){1}/', pattern):
                properties['unhashable'] = True
            elif re.search(pattern, '/'):
                properties['unhashable'] = True

            return '({})'.format(pattern)

        pattern_string = re.sub(r'<(.+?)>', add_parameter, uri)
        pattern = re.compile(r'^{}$'.format(pattern_string))

        # 设置路由
        route = Route(
            handler=handler, methods=methods, pattern=pattern,
            parameters=parameters
        )

        # 添加路由到对应字典集合
        self.routes_all[uri] = route
        if properties['unhashable']:
            self.routes_always_check.append(route)
        elif parameters:
            self.routes_dynamic[url_hash(uri)].append(route)
        else:
            self.routes_static[uri] = route

    def get(self, request):
        """
        将 URL 和处理器绑定在一起
        :param request:
        :return: handler, arguments, keyword arguments
        """

        return self._get(request.url, request.method,)

    @lru_cache(maxsize=Config.ROUTER_CACHE_SIZE)
    def _get(self, url, method):
        """
        get 的辅助方法
        :param url:
        :param method:
        :return: handler, arguments, keyword arguments
        """

        # 匹配静态路由集
        route = self.routes_static.get(url)
        if route:   # 匹配成功
            match = route.pattern.match(url)
        else:
            # 匹配动态路由集
            for route in self.routes_dynamic[url_hash(url)]:
                match = route.pattern.match(url)
                if match: # 匹配成功
                    break
            else:
                # 匹配所有路由集合
                for route in self.routes_always_check:
                    match = route.pattern.match(url)
                    if match:   # 匹配成功
                        break
                # 在所有集合里都没有匹配成功，抛出异常
                else:
                    # 此处在`exceptions.py` 中添加响应异常
                    raise NotFound('Requested URL {} not found'.format(url))

        # 若 method 不匹配，抛出异常
        if route.methods and method not in route.methods:
            raise InvalidUsage(
                'Method {} not allowed for URL {}'.format(
                    method, url), status_code=405)

        kwargs = {p.name: p.cast(value)
                  for value, p
                  in zip(match.groups(1), route.parameters)}
        return route.handler, [], kwargs




