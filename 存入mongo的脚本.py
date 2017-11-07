# -*- coding: utf-8 -*-
import pandas as pd
from pymongo import MongoClient

client = MongoClient()
db = client.VnTrader_5Min_Db
collection = db.ML0


#df = pd.read_csv('/Users/xuegeng/Downloads/vnpy-master 2/vn.trader/ctaAlgo/IF0000_1min.csv')
#df.columns=[u'date', u'time', u'open', u'high', u'low', u'close', u'volume']
#df['datetime'] = df['date']+ ' ' +df['time']
#df['datetime'] = pd.to_datetime(df['datetime'])
#df['symbol'] = 'ZN0000'
#df['exchange'] = 'DFE'
#df['vtSymbol'] = df['symbol'] + '.' + df['exchange']


#for i in range(df.count()[0]):
#    dict_ = df.ix[i].to_dict()
#    collection.insert_one(dict_)
    

#collection.delete_many({})
initCursor = collection.find({})      
initData =[]
        # 将数据从查询指针中读取出，并生成列表
for d in initCursor:
    data = d
    initData.append(data)      
client.close()

df = pd.DataFrame(initData)
del df['_id']
df = df.set_index('datetime').drop_duplicates()

def mongo2DF(dbName = 'VnTrader_1Min_Db',collName = '', query = {}):
    from pymongo import MongoClient
    client = MongoClient()
    db = client[dbName]
    collection = db[collName]
    initCursor = collection.find(query)      
    initData =[]
    for d in initCursor:
        data = d
        initData.append(data)      
    client.close()
    
    df = pd.DataFrame(initData)
    del df['_id']
    df = df.set_index('datetime').drop_duplicates()
    
    return df
    
    
    