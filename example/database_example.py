import sys
import asyncio

import peewee
import peewee_async


db = peewee_async.MySQLDatabase('sanic_testdb', user='root',
                                password='', host='127.0.0.1',
                                port=3306)

# 定义表
class Person(peewee.Model):
    name = peewee.CharField()

    class Meta:
        database = db   # 指定数据库

objects = peewee_async.Manager(db)

Person.create_table(True)

async def handler():
    await objects.create(Person, name='Bob')

loop = asyncio.get_event_loop()
loop.run_until_complete(handler())
loop.close()
if loop.is_closed():
    sys.exit(0)










