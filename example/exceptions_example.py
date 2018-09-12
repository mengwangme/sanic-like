from sanic.app import Sanic
from sanic.response import text
from sanic.exceptions import NotFound

app = Sanic()


@app.exception(NotFound)
def ignore_404s(request, exception):
    return text("Yep, I totally found the page: {}".format(request.url))

if __name__ == '__main__':
    app.run(debug=True)