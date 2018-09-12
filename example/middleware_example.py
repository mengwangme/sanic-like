from sanic.app import Sanic
from sanic.response import html

app = Sanic()


@app.middleware('request')
async def print_on_request(request):
    print("I print when a request is received by the server")

@app.route('/', methods=['GET'])
async def index(request):
    return html("<h1>This is index</h1>")

@app.middleware('response')
async def print_on_response(request, response):
    print("I print when a response is returned by the server")


if __name__ == '__main__':
    app.run(debug=True)