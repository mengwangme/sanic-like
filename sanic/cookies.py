from datetime import datetime
import re
import string

# ------------------------------------------------------------ #
#  SimpleCookie
# ------------------------------------------------------------ #

# 直接从 SimpleCookie 实现中截取，为实现此部分使用了黑魔法

# 合法字符
_LegalChars = string.ascii_letters + string.digits + "!#$%&'*+-.^_`|~:"
_is_legal_key = re.compile('[%s]+' % re.escape(_LegalChars)).fullmatch
# 未转义字符
_UnescapedChars = _LegalChars + ' ()/<=>?@[]{}'

# 翻译
_Translator = {n: '\\%03o' % n
               for n in set(range(256)) - set(map(ord, _UnescapedChars))}
_Translator.update({
    ord('"'): '\\"',
    ord('\\'): '\\\\',
})


def _quote(str):
    """
    引用一个字符串，用于 cookie 标题。
    如果字符串不需要双引号，则返回字符串。
    否则，使用双引号括起字符串并应用带 \ 的特殊字符。
    """
    if str is None or _is_legal_key(str):
        return str
    else:
        return '"' + str.translate(_Translator) + '"'


# ------------------------------------------------------------ #
#  Custom SimpleCookie
# ------------------------------------------------------------ #


class CookieJar(dict):
    """
    CookieJar 在添加和删除 cookie 时动态写入头部，
    通过使用 MultiHeader 类的 Set-Cookie来提供编码
    解决每个名字一个头部的限制
    """
    def __init__(self, headers):
        super().__init__()
        self.headers = headers
        self.cookie_headers = {}

    def __setitem__(self, key, value):
        """
        添加
        """
        cookie_header = self.cookie_headers.get(key)
        if not cookie_header:
            cookie = Cookie(key, value)
            cookie_header = MultiHeader("Set-Cookie")   #
            self.cookie_headers[key] = cookie_header
            self.headers[cookie_header] = cookie
            return super().__setitem__(key, cookie)
        else:   # 如果此 cookie 不存在，则添加它到头部 keys
            self[key].value = value

    def __delitem__(self, key):
        """
        删除
        """
        del self.cookie_headers[key]
        return super().__delitem__(key)


class Cookie(dict):
    """
    SimpleCookie 的精简版，CookieJar 的实现依赖
    """
    # cookie 保留字
    _keys = {
        "expires": "expires",   # 过期日期
        "path": "Path",         # 可访问此 cookie 的页面路径
        "comment": "Comment",   # 注释信息
        "domain": "Domain",     # 可访问此 cookie 的域名
        "max-age": "Max-Age",   # cookie 超时时间
        "secure": "Secure",     # 设置是否只能通过 https 来传递此 cookie
        "httponly": "HttpOnly", # 此属性代表只有在 HTTP 请求中会带有此 cookie 的信息
        "version": "Version",   # 版本
    }
    _flags = {'secure', 'httponly'}

    def __init__(self, key, value):
        if key in self._keys:       # cookie 保留字
            raise KeyError("Cookie name is a reserved word")
        if not _is_legal_key(key):  # cookie 中含有非法字符
            raise KeyError("Cookie key contains illegal characters")
        self.key = key
        self.value = value
        super().__init__()

    def __setitem__(self, key, value):
        if key not in self._keys:   # 关键字不在 cookie 的保留字中
            raise KeyError("Unknown cookie property")
        return super().__setitem__(key, value)

    def encode(self, encoding):
        """
        编码 cookie，将编码后的字符串放入 output
        """
        output = ['%s=%s' % (self.key, _quote(self.value))]
        for key, value in self.items():
            if key == 'max-age' and isinstance(value, int): # 存活时间
                output.append('%s=%d' % (self._keys[key], value))
            elif key == 'expires' and isinstance(value, datetime):  # 过期日期
                output.append('%s=%s' % (
                    self._keys[key],
                    value.strftime("%a, %d-%b-%Y %T GMT")
                ))
            elif key in self._flags:
                output.append(self._keys[key])
            else:
                output.append('%s=%s' % (self._keys[key], value))

        return "; ".join(output).encode(encoding)

# ------------------------------------------------------------ #
#  Header Trickery
# ------------------------------------------------------------ #


class MultiHeader:
    """
    允许给 response 设置拥有唯一键的头部
    """
    def __init__(self, name):
        self.name = name

    def encode(self):
        return self.name.encode()
