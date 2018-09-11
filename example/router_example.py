from sanic.app import Sanic
from sanic.response import html


app = Sanic()

@app.route('/')
async def index(request):
    return html("<h1>This is index</h1>")

@app.route('/router')
async def new_router(reqeust):
    return html("<h1>New router</h1>")

if __name__ == '__main__':
    app.run()