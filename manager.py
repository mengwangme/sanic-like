from sanic import Sanic
from sanic.response import json
from sanic import Blueprint

app = Sanic()
bp = Blueprint('my_blueprint')


@bp.route('/')
async def bp_root(request):
    return json({'my': 'blueprint'})

if __name__ == '__main__':
    app.blueprint(bp)
    # app.run()