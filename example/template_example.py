from sanic import Sanic
from sanic.response import html
from jinja2 import Template, Environment, PackageLoader

# Sanic
app = Sanic()


# Jinja2
env = Environment(loader=PackageLoader('example','templates'))
template = env.get_template('index.html')

@app.route('/')
async def index(request):
    users = ['Jack', 'Sakamoto', 'Michael', 'Chen']
    return html(template.render(users=users))

if __name__ == '__main__':
    app.run()
