# -*- coding: utf-8 -*-
"""本脚本的目的是将DATAPATH中的文件数据都存入Mongo"""
import json,datetime,re
from os import walk,sep
from pymongo import MongoClient

#DATAPATH = '/Users/xuegeng/Documents/vng/Folder2Collect'

client = MongoClient()
db = client.VnTrader_1Min_Db#与数据库创建链接

def saveFuturesData(fileNameList,db,dataType = "main"):
    
    """save all the data in fileNameList to mongoDB"""
    
    with open('/Users/xuegeng/Documents/vng/Exchanges.json') as f:#读取'商品-交易所'字典    
        EXCHANGEDICT = json.loads(f.read())
    for filename in fileNameList:#遍历每一份数据文件
        if 'DS_Store' in filename:#不要读取macos中的.DS_Store文件
            continue
            
        with open(filename) as f:
            
            symbol = f.readline().split(',')[0].upper()
            match = re.match(r"([a-z]+)([0-9]+)", symbol, re.I)#正则匹配商品代码
            symbolCode = match.groups()[0].upper()#得到商品代码，比如PP（丙烯）
            if dataType.lower() == "main":
                symbol = symbolCode + "0000"    #如果
            try:
                exchange = EXCHANGEDICT[symbolCode]#得到交易所代码
            except KeyError:
                print "There's no ExchangeCode for {}".format(symbolCode)
                continue
                
            collection = db[symbol]
            
            #count = 0#用于调试时控制输出量
            for line in f.readlines():
                data = line.strip('\n').split(',')#每一行数据
                
                #构造可以存入mongodb的数据记录
                dict_ = {
                        u'close': (data[4]),
                        u'date': data[1],
                        'datetime': datetime.datetime.strptime(data[1]+data[2],'%Y%m%d%H:%M:%S'),
                        'exchange': exchange,
                        u'high': data[5],
                        u'low': data[6],
                        u'open': data[3],
                        'symbol': symbol,
                        u'time': data[2],
                        u'volume': data[7],
                        'vtSymbol': symbol + "." + exchange
                }
                try:
                    collection.insert_one(dict_)#将记录插入数据集合
                except:
                    print "something wrong while inserting symbol data"
                    continue