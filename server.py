from sanic.app import Sanic
from sanic.response import html, text


app = Sanic()

@app.route('/', methods=['GET'])
async def index(request):
    return html("<h1>This is index</h1>")

if __name__ == '__main__':
    app.run()