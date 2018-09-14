from sanic import Sanic

from simple_project.books import books


app = Sanic()
app.blueprint(books)

