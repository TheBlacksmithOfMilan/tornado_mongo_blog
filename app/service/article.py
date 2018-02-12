#!/usr/bin/env python
#-*- coding:utf8 -*-
# Power by null 2018-02-09 10:06:22
from .base import BaseService
import pymongo
from bson import ObjectId
from tornado.gen import multi

class CommontData():
    _instance = None
    def __new__(cls, mongodb):
        if not cls._instance:
            cls._instance = super(CommontData, cls).__new__(cls)
            cls._instance.init(mongodb)
        return cls._instance
    
    def init(self, mongodb):
        self.mongodb = mongodb
        self.common = {}

    async def get_common(self):
        if not self.common:
           self.common['catagories'] = await self.mongodb.catagory.find({}, {"_id": 0}).to_list(1000)
           self.common['tags'] = await self.mongodb.tag.find({}, {"_id": 0}).to_list(1000)
            
        return self.common


class ArticleService(BaseService):
    def __init__(self):
        super(ArticleService, self).__init__()
        self.common = CommontData(self.mongodb)

    async def get_article_info(self, slug):
        info = await self.mongodb.article.find_one({"slug": slug}, {'_id':0})
        if not info:
            self.result['err'] = True
            self.result['msg'] = '文章链接:[{}]对应的文章不存在！'.format(slug)
        self.result['info'] = info

    def check_artile_info_valid(self, info):
        need_string = {'title':'标题', 'slug':'链接', 'status':'文章状态', 'content':'正文'} 
        for k, v in need_string.items():
            if k not in info or not info[k].strip():
                self.result['msg'] = '{}为必填项'.format(v)
                self.result['err'] = True
                break
        
    
    async def add_article(self, article_info):
        self.check_artile_info_valid(article_info)
        if self.result['err']:
            return
        try:
            await self.mongodb.article.insert(article_info)
        except pymongo.errors.DuplicateKeyError:
            self.result['err'] = True
            self.result['msg'] = '不能添加重复的文章链接'

    async def edit_article(self, slug, article_info):
        self.check_artile_info_valid(article_info)
        if self.result['err']:
            return
        original_doc = await self.mongodb.article.find_one_and_replace({"slug": slug}, article_info)
        if not original_doc:
            self.result['err'] = True
            self.result['msg'] = '要编辑的文章不存在'

    async def get_articles_by_next_prev(self, prev=False, last_id=''):
        ''' 
        @param prev: False 请求上一页，True 请求下一页
        @param last_id: 此页的最前一个和最后一个，如果为空则代表取首页
        '''
        limit = 20
        if not last_id:
            articles = await self.mongodb.article.find({}, {'content': 0}).sort([('_id', -1)]).to_list(limit)
        else:
            obj_id = None
            try:
                obj_id = ObjectId(last_id) 
            except:
                self.result['err'] = True
                self.result['msg'] = '参数错误'
                return
            id_filter_string = '$lt'
            sort_list = [('_id', -1)]
            if prev:
                id_filter_string = '$gt'
                sort_list = [('_id', 1)]
            articles = await self.mongodb.article.find({'_id':{id_filter_string: obj_id}}, {'content': 0}).sort(sort_list).to_list(limit) 
            if prev:
                articles = articles[::-1]
        if not articles:
            self.result['err'] = True
            self.result['msg'] = '参数错误'
            return
        last_id = articles[-1]['_id']
        first_id = articles[0]['_id']
        return_list = await multi([self.mongodb.article.find({'_id':{'$gte':first_id}}, {'_id':1}).\
                sort([('_id', 1)]).to_list(1),
            self.mongodb.article.find({'_id':{'$lte':last_id}}, {'_id':1}).sort([('_id', -1)]).to_list(1)])
        pre_v = nex_t = None
        if return_list[0]:
            pre_v = str(return_list[0][0]['_id'])
        if return_list[1]:
            nex_t = str(return_list[1][-1]['_id'])
        self.result['info'] = {'articles': articles, 'prev':pre_v if pre_v else '', 'next':nex_t if nex_t else ''}

