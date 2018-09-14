import datetime

from peewee import *

from simple_project.config import db


class Book(Model):
    bookname = CharField()
    author = CharField()
    pub_house = CharField()
    pub_date = DateField(default=datetime.datetime.now())

    class Meta:
        database = db


db.connect()
db.create_tables([Book])