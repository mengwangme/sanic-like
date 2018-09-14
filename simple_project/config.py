from peewee import MySQLDatabase
from jinja2 import Environment, PackageLoader


# database
db = MySQLDatabase('sanic_project_db', user='root', password='', host='127.0.0.1', port=3306)


# Jinja2
env = Environment(loader=PackageLoader('simple_project','templates'))


