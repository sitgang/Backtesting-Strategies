# -*- coding: utf-8 -*-
url = 'http://stock2.finance.sina.com.cn/futures/api/json.php/IndexService.getInnerFuturesMiniKLine5m?symbol=M0'
import requests
import pandas as pd
from pymongo import MongoClient

client = MongoClient()
db = client.VnTrader_5Min_Db
collection = db.ML0


pd.options.display.max_rows = 10
r = requests.get(url)
df = pd.DataFrame(r.json(),columns = ["datetime","open","high","low","close","volume"])


#df.columns=[u'date', u'time', u'open', u'high', u'low', u'close', u'volume']
#df['datetime'] = df['date']+ ' ' +df['time']
df['symbol'] = 'ML0'
df['exchange'] = "DCE"#(大连商品)#'DFE'#(郑州商品)#SHFE#(上海商品)
df['vtSymbol'] = df['symbol'] + '.' + df['exchange']

df = df.apply(lambda x: pd.to_numeric(x, errors='ignore'))
df['datetime'] = pd.to_datetime(df['datetime'])


for i in range(df.count()[0]):
    dict_ = df.ix[i].to_dict()
    collection.insert_one(dict_)


def washCollection(cname):
    """to drop duplicates"""
    collection = db.get_collection(cname)
    initCursor = collection.find({})      
    initData =[]
    for d in initCursor:
        data = d
        initData.append(data)      
    client.close()
    df = pd.DataFrame(initData)
    del df['_id']
    df = df.set_index('datetime')
    df = df.drop_duplicates()
    db.drop_collection(cname)
    collection = db.create_collection(cname)
    
    for i in range(df.count()[0]):
        dict_ = df.ix[i].to_dict()
        collection.insert_one(dict_)
