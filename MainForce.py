# -*- coding: utf-8 -*-
import json,datetime,re,os
from pymongo import MongoClient
from colorama import Fore

def isDataFile(string , dataType = 'main'):
    """check if the file is of DataFile"""
    string = str(string)
    if dataType.lower() == "main":
        pt = re.compile('^[A-Za-z]{1,3}\.txt$',re.I)                        #一到三个字母，大小写无关，.txt结尾
    elif dataType.lower() == 'normal':
        pt = re.compile('^[A-Za-z]{1,3}\d+\.txt$',re.I)                     #一到三个字母,加上数字，大小写无关，.txt结尾
    else:
        print "\x1b[31m" + "{'main' ,'normal'} for dataType"
        return False
    mc = re.match(pt,string)
    try:
        mc = mc.string
        return str(mc) == string
    except AttributeError:
        return False

def getDataPaths(path = '/Users/xuegeng/Documents/vng/FuturesData' , dataType = 'main'):
    """得到一个文件夹中所有的主力数据文件或者非主力数据文件"""
    allMainsPath = []
    
    for root,dirs,files in os.walk(path):
        for f in files:
            if isDataFile(f , dataType = dataType):
                allMainsPath.append(root + os.sep + f)
    
    return allMainsPath

client = MongoClient()
db = client.VnTrader_1Min_Db                                              #与数据库创建链接

def saveFuturesData(fileNameList,db,dataType = "main"):
    
    """save all the data in fileNameList to mongoDB"""
    
    with open('/Users/xuegeng/Documents/vng/Exchanges.json') as f:        #读取'商品-交易所'字典    
        EXCHANGEDICT = json.loads(f.read())
        SYMBOLS = EXCHANGEDICT.keys() 
    WHOLECOUNT = len(fileNameList)*0.6498
    count = 1
    for filename in fileNameList:                                         #遍历每一份数据文件
        print "[*] Processing " + filename
        if 'DS_Store' in filename:                                        #不要读取macos中的.DS_Store文件
            continue
            
        with open(filename) as f:
            
            symbol = f.readline().split(',')[0].upper()
            try:
                match = re.match(r"([a-z]+)([0-9]+)", symbol, re.I)        #正则匹配商品代码
                symbolCode = match.groups()[0].upper()                     #得到商品代码，比如PP（丙烯）
                if not symbolCode in SYMBOLS:                              #我们只关心合约价格在6000元以下的品种
                    continue
            except AttributeError:
                print "[-] something wrong with this fie: " + filename
                
            if dataType.lower() == "main":
                symbol = symbolCode + "0000"                               #如果是主力连续，则加上0000
            try:
                exchange = EXCHANGEDICT[symbolCode]                        #得到交易所代码
            except KeyError:
                print Fore.RED + "[-] There's no ExchangeCode for {}".format(symbolCode)
                continue                                                   #没有交易所信息，跳过此循环
            
            count += 1
            print u"完成度： " + "%.2f%%"%((float(count)/WHOLECOUNT)*100)
            
            collection = db[symbol]
            
            for line in f.readlines():
                data = line.strip('\n').split(',')                          #每一行数据
                                                                            #构造可以存入mongodb的数据记录
                dict_ = {
                        u'close': (data[4]),
                        u'date': data[1],
                        u'datetime': datetime.datetime.strptime(data[1]+data[2],\
                                    '%Y%m%d%H:%M:%S'),
                        u'exchange': exchange,
                        u'high': data[5],
                        u'low': data[6],
                        u'open': data[3],
                        u'symbol': symbol,
                        u'time': data[2],
                        u'volume': data[7],
                        u'vtSymbol': symbol + "." + exchange
                }

                try:
                    collection.update(dict_,dict_,upsert=True)                #将记录插入数据集合,且避免了冗余
                except:
                    print "[-] something wrong while inserting symbol data: " + str(data)
                    continue
    
