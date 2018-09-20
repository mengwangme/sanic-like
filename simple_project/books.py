from sanic import Blueprint
from sanic.response import html, redirect

from simple_project.config import env
from simple_project.models import Book, objects

books = Blueprint('book')

# 获取模板
template = env.get_template('index.html')

@books.route('/')
async def index(request):
    """
    展示图书
    """
    booklist = await objects.execute(Book.select())
    return html(template.render(booklist=booklist))

@books.route('/addbook', methods=['POST'])
async def add_book(request):
    """
    添加图书
    """
    bookname = request.form.get('bookname')
    author = request.form.get('author')
    pub_house = request.form.get('pub_house')
    pub_date = request.form.get('pub_date')
    if bookname != None and author != None and pub_house != None and pub_date != None:
        await objects.create(Book, bookname=bookname, author=author, pub_house=pub_house, pub_date=pub_date)
    return redirect('/')

@books.route('/deletebook/<id:int>', methods=['GET'])
async def delete_book(request, id):
    """
    删除图书
    """
    await objects.execute(Book.delete().where(Book.id == id))
    return redirect('/')


