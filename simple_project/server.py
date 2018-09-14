from sanic import Sanic, Blueprint
from sanic.response import html, redirect

from simple_project.config import db, env
from simple_project.models import Book


app = Sanic()
books = Blueprint('book')

# 获取模板
template = env.get_template('index.html')

@books.route('/')
async def index(request):
    """
    展示图书
    """
    booklist = Book.select()
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
    q = Book.create(bookname=bookname, author=author, pub_house=pub_house, pub_date=pub_date)
    q.save()
    return redirect('/')

@books.route('/deletebook/<bookname:string>', methods=['GET'])
async def delete_book(request, bookname):
    """
    删除图书
    """
    q = Book.delete().where(Book.bookname == bookname)
    q.execute()
    return redirect('/')

# 注册蓝图
app.blueprint(books)

