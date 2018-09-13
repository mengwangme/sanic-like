from collections import defaultdict


class BlueprintSetup:
    """
    调用 Sanic 对象实现其基本功能：路由，中间件，异常...
    """

    def __init__(self, blueprint, app, options):
        self.app = app
        self.blueprint = blueprint
        self.options = options

        # 路由前缀
        url_prefix = self.options.get('url_prefix')
        if url_prefix is None:
            url_prefix = self.blueprint.url_prefix

        # 前缀应用于此蓝图的所有 URL
        self.url_prefix = url_prefix

    #
    # 以下方法都是调用 Sanic 对象实现
    #

    def add_route(self, handler, uri, methods):
        """
        注册路由。
        """
        if self.url_prefix:
            uri = self.url_prefix + uri

        self.app.route(uri=uri, methods=methods)(handler)

    def add_exception(self, handler, *args, **kwargs):
        """
        注册异常处理。
        """
        self.app.exception(*args, **kwargs)(handler)

    def add_middleware(self, middleware, *args, **kwargs):
        """
        注册中间件。
        """
        if args or kwargs:
            self.app.middleware(*args, **kwargs)(middleware)
        else:
            self.app.middleware(middleware)


class Blueprint:
    """
    蓝图，实现了与 Sanic 一样的调用方法。
    """
    def __init__(self, name, url_prefix=None):
        """
        创建一个新蓝图
        :param name: 蓝图名称
        :param url_prefix:  所有 URLs 的前缀
        """
        self.name = name                    # 蓝图名，唯一
        self.url_prefix = url_prefix        # 路由前缀
        self.deferred_functions = []        # 推迟执行的函数集合

    def record(self, func):
        """
        登记延迟调用的函数
        """
        self.deferred_functions.append(func)

    def make_setup_state(self, app, options):
        """
        调用 BlueprintSetup，构建对象
        """
        return BlueprintSetup(self, app, options)

    def register(self, app, options):
        """
        执行前面登记的的延迟调用函数
        """
        state = self.make_setup_state(app, options)
        for deferred in self.deferred_functions:
            deferred(state)
    #
    # 以下方法都使用了匿名函数 -- lambda
    #   - s 代表 BlueprintSetup 对象
    #
    
    def route(self, uri, methods=None):
        """
        路由装饰器
        """
        def decorator(handler):
            self.record(lambda s: s.add_route(handler, uri, methods))
            return handler
        return decorator

    def add_route(self, handler, uri, methods=None):
        """
        添加路由非装饰器方法
        """
        self.record(lambda s: s.add_route(handler, uri, methods))
        return handler

    def middleware(self, *args, **kwargs):
        """
        中间件装饰器
        """
        def register_middleware(middleware):
            self.record(
                lambda s: s.add_middleware(middleware, *args, **kwargs))
            return middleware

        # 判断是哪种方式调用的， `@middleware` or `@middleware('AT')`
        if len(args) == 1 and len(kwargs) == 0 and callable(args[0]):
            middleware = args[0]
            args = []
            return register_middleware(middleware)
        else:
            return register_middleware

    def exception(self, *args, **kwargs):
        """
        异常处理装饰器
        """
        def decorator(handler):
            self.record(lambda s: s.add_exception(handler, *args, **kwargs))
            return handler
        return decorator




