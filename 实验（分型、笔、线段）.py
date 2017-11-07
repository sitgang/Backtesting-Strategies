# -*- coding: utf-8 -*-
import sys   
reload(sys) # Python2.5 初始化后会删除 sys.setdefaultencoding 这个方法，我们需要重新载入   
sys.setdefaultencoding('utf-8')
import pymongo,datetime,matplotlib
import pandas as pd 
import numpy as np
import matplotlib.pyplot as plt

"""===========================规整数据=============================="""

#dbClient = pymongo.MongoClient()
#collection = dbClient["VnTrader_1Min_Db"]["RB0000"]
#df =pd.DataFrame(list(collection.find({'datetime':{'$gte':datetime.datetime(2016,11,12,20)}})))
#df = df.drop_duplicates()
#del df['_id']
#df = df.sort_values('datetime')
#index = pd.Index(np.arange(df.count()[0]))
#df.index = index 
#df[['open','close','low','high']] = df[['open','close','low','high']].applymap(float)
#df[['volume']] = df[['volume']].applymap(int)


"""===========================绘图函数=============================="""
fig, ax = plt.subplots(figsize = (20,8))

def draw_candlestick(df):

    global fig,ax
    fig, ax = plt.subplots(figsize = (20,8))
    quotes=df[['datetime','open','high','low','close']].values
    tuples = [tuple(x) for x in quotes]
    qw=[]
        
    for things in tuples:
        date=matplotlib.dates.date2num(things[0])
        tuple1=(date,things[1],things[2],things[3],things[4])
        qw.append(tuple1)
    ax.xaxis_date()
    ax.grid(linestyle='-', linewidth=0.1)
    matplotlib.finance.candlestick_ohlc(ax, qw, colorup='r',colordown='g', alpha =.4, width=0.0005)
    plt.show()
   


"""===========================分型函数=============================="""
def fenxing(bar1,bar2,bar3):
    """
    用于确定顶分型和底分型
    """
    #顶分型
    if (bar2['high'] > bar1['high'] and bar2['high'] > bar3['high']
        and bar2['low'] > bar1['low'] and bar2['low'] > bar1['low']):
        return (bar2['datetime'],bar2['high'],-1)
    #底分型
    elif (bar2['high'] < bar1['high'] and bar2['high'] < bar3['high']
        and bar2['low'] < bar1['low'] and bar2['low'] < bar1['low']):
        return (bar2['datetime'],bar2['low'],1)
    #无分型
    else:
        return None
        
"""===========================包含函数=============================="""

def baohan(bar1,bar2):
    """
    存在包含条件的k线进行包含处理
    """
    
    return
    


"""===========================测试函数=============================="""
bars = []#序列长度32，用于放K线
dingfenxingTuples = []
difenxingTuples = []
def run():
    '''
    模拟喂入数据
    '''
    global df,bars,dingfenxingTuples,difenxingTuples
    lastFenxing = 0 #上一次分型是顶还是底
    fenxingCounter = 0 #用于确定无共用的K线
    for row in df.iterrows():
        
        bars.append(row[1])
        try:#保证至少有3K线
            [bar1,bar2,bar3] = bars[-3:]
        except ValueError:
            continue 
        ###################确定K线合并关系#######################
        
        if lastFenxing:
            if lastFenxing[2] == -1:
                if bar3['low']>bar2['low'] and bar3['high']<bar2['high']:
                    bar3['low']=bar2['low']
                    print "here hebing"
                    fenxingCounter -= 1
            if lastFenxing[2] == 1:
                if bar3['low']<bar2['low'] and bar3['high']>bar2['high']:
                    bar3['high']=bar2['high']
                    print "here hebing"
                    fenxingCounter -= 1
        
        ###################确定第一个分型#######################
        
        if not lastFenxing:
            ddfenxing = fenxing(bar1,bar2,bar3)
            if ddfenxing:
                fenxingCounter = 0 # 开始计时
                lastFenxing = ddfenxing
                if ddfenxing[2] == -1:#顶分型
                    dingfenxingTuples.append(ddfenxing)
                else:#底分型
                    difenxingTuples.append(ddfenxing)
            else:
                continue
        ###################确定后续分型#######################
                


        ddfenxing = fenxing(bar1,bar2,bar3)
        if ddfenxing == None:
            fenxingCounter += 1
            continue
        else:
            if ddfenxing[2] == lastFenxing[2]:#相同分型
                print "here"
                if lastFenxing[2] == -1:#如果之前就是一个顶分型，那么比较两个分型
                    if ddfenxing[1] > lastFenxing[1]:#保留高的一个
                        dingfenxingTuples[-1] = ddfenxing#替换上个分型
                        fenxingCounter = 0
                    else:
                        fenxingCounter += 1
                        continue
                if lastFenxing[2] == 1:#如果之前就是一个底分型，那么比较两个分型
                    if ddfenxing[1] < lastFenxing[1]:#保留低的一个
                        difenxingTuples[-1] = ddfenxing#替换上个分型
                        fenxingCounter = 0
                    else:
                        fenxingCounter += 1
                        continue
            else:#不相同分型
                print "here2"
                if fenxingCounter >= 3:
                    print "here3" , fenxingCounter,ddfenxing[2]
                    if ddfenxing[2] == -1:#顶分型
                        dingfenxingTuples.append(ddfenxing)
                    else:#底分型
                        difenxingTuples.append(ddfenxing)
                    fenxingCounter = 0
                else:
                    fenxingCounter += 1
                    continue
        
 
#run()
#
#dingfenxingTimes = [i[0] for i in dingfenxingTuples]
#dingfenxingPrices = [i[1] for i in dingfenxingTuples]
#difenxingTimes = [i[0] for i in difenxingTuples]
#difenxingPrices = [i[1] for i in difenxingTuples]
#
#def drawdingdi():
#    
#    draw_candlestick(df)
#    plt.scatter(difenxingTimes,difenxingPrices,marker='^',c='r',s=60)
#    plt.scatter(dingfenxingTimes,dingfenxingPrices,marker='v',c='g',s=60)
#    
#    plt.show()
#
#drawdingdi()
    
















