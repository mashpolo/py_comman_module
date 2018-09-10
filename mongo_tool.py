#!/usr/bin/env python
# coding=utf-8
"""
@desc:   对pymongo模块的简单封装
@author: luluo
@date:   2018/9/10

"""

import pymongo
from pymongo import client_session


class MongoConn(object):
    """
    for mongodb
    """
    sep = ":"

    def __init__(self, conf=None):
        #uri = 'mongodb://{username}:{password}@{host}:{port}/'.format(**conf)
        uri = 'mongodb://localhost:27017'
        self.client = pymongo.MongoClient(uri)
        self.db = None
        self.coll = None

    def close(self):
        try:
            self.client.close()
        except DbException as e:
            self.client = None

    def choose_db(self, db_name):
        try:
            self.db = self.client[db_name]
            return True
        except DbException as e:
            return False

    def choose_coll(self, coll_name):
        if self.sep in coll_name:
            db, coll_name = coll_name.split(self.sep)
            if not self.choose_db(db):
                return False
        # if coll_name not in self.db.collection_names():
        #     return False
        self.coll = self.db[coll_name]
        return True

    def get_db(self, db_name=None):
        if db_name is not None:
            return self.client[db_name]
        return self.db

    # def insert(self, coll_name, info):
    #     self.coll = self.get_coll(coll_name)
    #     return self.coll.insert(info)

    def mset(self, coll_name, info):
        with self.client.start_session(causal_consistency=True) as session:
            self.coll = self.get_coll(coll_name)
            if isinstance(info, list):
                try:
                    return self.coll.insert_many(info, session=session)
                except Exception as e:
                    raise Exception("Can not write into database, already rollback!")
            elif isinstance(info, dict):
                try:
                    self.coll.insert_one(info, session=session)
                except Exception as e:
                    raise Exception("Can not write into database, already rollback!")
            else:
                raise Exception("It doesn't support this type of info")

    def get_coll(self, coll_name=None):
        if coll_name is not None:
            if self.sep in coll_name:
                db_name, coll_name = coll_name.split(self.sep)
                return self.client[db_name][coll_name]
            return self.db[coll_name]
        return self.coll

    def __getattr__(self, item, *args, **kwargs):
        return getattr(self.coll, item, *args, **kwargs)

