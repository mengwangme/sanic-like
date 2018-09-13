from peewee import *
from datetime import date

db = MySQLDatabase('sanic_db', user='root', password='', host='127.0.0.1', port=3306)

# 定义表
class Person(Model):
    name = CharField()
    birthday = DateField()

    class Meta:
        database = db


if __name__ == '__main__':

    # 连接数据库
    db.connect()
    # 创建表
    db.create_tables([Person])
    uncle_bob = Person(name='Bob', birthday=date(1960, 1, 15))
    uncle_bob.save()

