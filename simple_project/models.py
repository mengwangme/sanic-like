import datetime

import peewee
import peewee_async

from simple_project.config import db


class Book(peewee.Model):
    bookname = peewee.CharField()
    author = peewee.CharField()
    pub_house = peewee.CharField()
    pub_date = peewee.DateField(default=datetime.datetime.now())

    class Meta:
        database = db


objects = peewee_async.Manager(db)

Book.create_table(True)

