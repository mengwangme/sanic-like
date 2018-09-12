from sanic.app import Sanic
from sanic.response import text, json
from sanic.blueprints import Blueprint
from sanic.exceptions import NotFound

app = Sanic()
bp = Blueprint('my_blueprint')

@bp.route('/')
async def bp_root(request):
    return json({'my': 'blueprint'})

@bp.middleware
async def print_on_request(request):
    print("I am a spy")

@bp.middleware('request')
async def halt_request(request):
    print('I halted the request')

@bp.middleware('response')
async def halt_response(request, response):
    print('I halted the response')

@bp.exception(NotFound)
def ignore_404s(request, exception):
    return text("Yep, I totally found the page: {}".format(request.url))

if __name__ == '__main__':
    app.blueprint(bp)
    app.run()