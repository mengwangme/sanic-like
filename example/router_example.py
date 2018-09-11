from sanic.app import Sanic
from sanic.response import html,text


app = Sanic()

@app.route('/', methods=['GET'])
async def index(request):
    return html("<h1>This is index</h1>")

@app.route('/router', methods=['GET', 'POST'])
async def new_router(reqeust):
    return html("<h1>New router</h1>")

@app.route('/my/<name:string>', methods=['GET'])
async def name(request, name):
    return text('My name is {}'.format(name))

if __name__ == '__main__':
    app.run()