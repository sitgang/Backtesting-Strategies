# encoding: UTF-8

from ctaBase import *
from ctaTemplate import CtaTemplate

import datetime
import pandas as pd
import talib
import numpy as np

#BERTREND
UP  = "UP"
DOWN = "DOWN"
DING = "DING"
DI = "DI"
FENXINGDISTANCE = 4#两分型（counter）之间距离大于等于4


########################################################################
class BeichiStrategy(CtaTemplate):
    """关于利用macd和bolling辅助判断背驰的第二买卖点交易策略"""
    className = 'BeichiStrategy'
    author = u'薛耕'

    # 策略参数
    initDays = 40           # 初始化数据所用的天数

    # 策略变量
    bar = None                  # K线对象
    barMinute = EMPTY_STRING    # K线当前的分钟
    bufferSize = 100                    # 需要缓存的数据的大小
    bufferCount = 0                     # 目前已经缓存了的数据的计数

    orderList = []                      # 保存委托代码的列表

    # 参数列表，保存了参数的名称
    paramList = ['name',
                 'className',
                 'author',
                 'vtSymbol']    

    # 变量列表，保存了变量的名称
    varList = ['inited',
               'trading',
               'pos']  

    #----------------------------------------------------------------------
    def __init__(self, ctaEngine, setting):
         
        """===========================申明变量=============================="""
        super(BeichiStrategy, self).__init__(ctaEngine, setting)
       
        ###测试变量
        self.start_time = datetime.datetime(2016,11,24)
        self.end_time = None
        
        ###指标变量
        self.closes = []
        self.macd_len = 34
        self.macd_area_buffer = []#分型出现就清空，添加入backup，macd数据加入areas
        self.macd_area_backup = []#替换不清空
        self.macd_areas = []#第一个分型不去比较红蓝柱子面积
        self.bolling_len = 5
        self.bolling_fenxing = []#布尔值数列，表示分型是否处在超强区域
        self.powerful_area = False#是否在超强区域
        
        self.last_fenxing_datetime = None
        self.last_fenxing_type = None
        
        ###交易变量
        self.last_fenxing_datetime2 = None
        self.volume = 1#新增分型购买手数，每替代一次手数加一
        self.ding_signal = False
        self.di_signal = False
       
        ###分型变量
        self.fenxing = None
        self.lastFenxing = None
        self.fenxingCounter = 0
        self.lastFenxingCounter = 0
        
        ###k线变量
        self.newBar = None
        self.firstBar = None
        self.middleBar = None
        self.lastBar = None
        self.barCounter = 0
        self.barTrend = None#改变为常量
        self.bars = []
        
        ###包含变量
        self.hasBaohan = False
        
        ###统计变量
        self.fenxingTuples = []
      
        
                

    #----------------------------------------------------------------------
    def onInit(self):
        """初始化策略（必须由用户继承实现）"""
        self.writeCtaLog(u'%s策略初始化' %self.name)
        # 载入历史数据，并采用回放计算的方式初始化策略数值
        
        initData = self.loadBar(self.initDays)
        for bar in initData:
            self.onBar(bar)

        self.putEvent()

    #----------------------------------------------------------------------
    def onStart(self):
        """启动策略（必须由用户继承实现）"""
        self.writeCtaLog(u'%s策略启动' %self.name)
        self.putEvent()

    #----------------------------------------------------------------------
    def onStop(self):
        """停止策略（必须由用户继承实现）"""
        self.writeCtaLog(u'%s策略停止' %self.name)
        self.putEvent()

    #----------------------------------------------------------------------
    
    def onAccount(self, account):
        """获取账户信息"""
        self.account = account  #VtAccountData
    
    #----------------------------------------------------------------------
    def onTick(self, tick):
        """收到行情TICK推送（必须由用户继承实现）"""
        # 计算K线
        tickMinute = tick.datetime.minute

        if tickMinute != self.barMinute:    
            if self.bar:
                self.onBar(self.bar)

            bar = CtaBarData()              
            bar.vtSymbol = tick.vtSymbol
            bar.symbol = tick.symbol
            bar.exchange = tick.exchange

            bar.open = tick.lastPrice
            bar.high = tick.lastPrice
            bar.low = tick.lastPrice
            bar.close = tick.lastPrice

            bar.date = tick.date
            bar.time = tick.time
            bar.datetime = tick.datetime    # K线的时间设为第一个Tick的时间

            self.bar = bar                  # 这种写法为了减少一层访问，加快速度
            self.barMinute = tickMinute     # 更新当前的分钟
        else:                               # 否则继续累加新的K线
            bar = self.bar                  # 写法同样为了加快速度

            bar.high = max(bar.high, tick.lastPrice)
            bar.low = min(bar.low, tick.lastPrice)
            bar.close = tick.lastPrice

    #----------------------------------------------------------------------
    def onBar(self, bar):
        """收到Bar推送（必须由用户继承实现）"""
        # 撤销之前发出的尚未成交的委托（包括限价单和停止单）
        """这个好，撤销之前的单"""
        for orderID in self.orderList:
            self.cancelOrder(orderID)
        self.orderList = []

       
        
        self.newBar = bar.__dict__
        self.process_baohan()
        self.process_fenxing()
        self.process_indextools()
        self.process_tradesignal()
        self.process_ordertrigger()
        self.newBar = None
        
        # 计算指标数值
      
        
        # 发出状态更新事件
        self.putEvent()
    
    def process_baohan(self):
        """===========================包含函数=================================="""
        """
        存在包含条件的k线进行包含处理
        """
        if self.lastFenxing and\
            self.newBar['low'] >= self.lastBar['low'] and\
            self.newBar['high'] <= self.lastBar['high']:#存在包含关系;分型之后才需要判断包含
                
            self.hasBaohan = True
        
        else:
            self.hasBaohan = False
            self.firstBar = self.middleBar
            self.middleBar = self.lastBar
            self.lastBar = self.newBar
            self.barCounter += 1
            self.bars.append(self.newBar)        
    
    def process_fenxing(self):
        """===========================分型函数=============================="""
        """
        用于确定顶分型和底分型
        """
        if self.firstBar == None:return
        #顶分型
        if (self.middleBar['high'] > self.firstBar['high'] and self.middleBar['high'] > self.lastBar['high']
            and self.middleBar['low'] > self.firstBar['low'] and self.middleBar['low'] > self.firstBar['low']):
            self.fenxing = (self.middleBar['datetime'],self.middleBar['high'],DING)
            self.fenxingCounter = self.barCounter
            
            try:#如果上个分型不存在，直接加入分型队列
                assert self.lastFenxing
            except AssertionError:
                self.fenxingTuples.append(self.fenxing)
                self.lastFenxing = self.fenxing
                self.lastFenxingCounter = self.fenxingCounter
            
            if self.lastFenxing[2] == DING:#如果上一个分型也是顶分型的话，保留高的那个
                if self.fenxing[1] >= self.lastFenxing[1]:#如果后来居上
                    self.fenxingTuples[-1] = self.fenxing
                    self.lastFenxing = self.fenxing
                    self.lastFenxingCounter = self.fenxingCounter
                else:#后者顶分型力度不够
                    pass
                    
            else:#上一个分型是底分型,无共用K线，就加入列表，确认分型
                if self.fenxingCounter - self.lastFenxingCounter >= FENXINGDISTANCE :#无共用k线
                    self.fenxingTuples.append(self.fenxing)
                    self.lastFenxing = self.fenxing
                    self.lastFenxingCounter = self.fenxingCounter
            
        #底分型
        elif (self.middleBar['high'] < self.firstBar['high'] and self.middleBar['high'] < self.lastBar['high']
            and self.middleBar['low'] < self.firstBar['low'] and self.middleBar['low'] < self.firstBar['low']):
            
            self.fenxing = (self.middleBar['datetime'],self.middleBar['low'],DI)
            self.fenxingCounter = self.barCounter
            
            try:#如果上个分型不存在，直接加入分型队列
                assert self.lastFenxing
            except AssertionError:
                self.fenxingTuples.append(self.fenxing)
                self.lastFenxing = self.fenxing
                self.lastFenxingCounter = self.fenxingCounter
            
            
            if self.lastFenxing[2] == DI:#如果上一个分型也是底分型的话，保留低的那个
                
                if self.fenxing[1] <= self.lastFenxing[1]:#如果后来居下
                    self.fenxingTuples[-1] = self.fenxing
                    self.lastFenxing = self.fenxing
                    self.lastFenxingCounter = self.fenxingCounter
                
                else:#后者底分型力度不够
                    pass
            else:#上一个分型是顶分型,无共用K线，就加入列表，确认分型
                if self.fenxingCounter - self.lastFenxingCounter >= FENXINGDISTANCE :#无共用k线
                    self.fenxingTuples.append(self.fenxing)
                    self.lastFenxing = self.fenxing
                    self.lastFenxingCounter = self.fenxingCounter
        #无分型
        else:
            pass
        
    
    def process_indextools(self):
        
        """======================更新辅助指标=================="""
        
        ###更新closes
        close = self.newBar['close']
        self.closes.append(close)
        if len(self.closes) < self.macd_len:return#如果收盘价列表不够用于计算，则继续添加
        if len(self.fenxingTuples)<=1:return#如果两个分型都没有，则继续等待分型
        now_fenxing = self.fenxingTuples[-1]
        ###判断分型是否更新
        ###未更新
        if self.last_fenxing_datetime == now_fenxing[0]:
            
            self.macd_area_buffer.append(talib.MACD(np.array(self.closes))[-1][-1])#buffer添加一个
            
            
        ###更新了
        else:
            ###替代前分型
            if self.last_fenxing_type == now_fenxing[2]:
                
                #macd处理
                self.macd_area_buffer.append(talib.MACD(np.array(self.closes))[-1][-1])#buffer添加一个
                self.macd_area_backup.extend(self.macd_area_buffer)#backup加入buffer
                macd_area = sum(self.macd_area_backup)#计算
                #self.macd_areas[-1] = macd_area#替换最后一个红蓝柱面积
                self.macd_areas[-1] = (now_fenxing[0],macd_area)#替换最后一个红蓝柱面积
                self.macd_area_buffer = []#清空buffer
                
                #bolling处理
                ceil = talib.BBANDS(np.array(self.closes))[0][-2]
                floor = talib.BBANDS(np.array(self.closes))[-1][-2]
                self.powerful_area = ((now_fenxing[1] > ceil) | (now_fenxing[1] < floor))
                #self.bolling_fenxing[-1] = self.powerful_area
                self.bolling_fenxing[-1] = (now_fenxing[0],self.powerful_area)
                
                #判断变量
                self.last_fenxing_datetime = now_fenxing[0]
                
            ###增加新的分型    
            else:
                
                #macd处理
                self.macd_area_backup = []#清空backup
                self.macd_area_buffer.append(talib.MACD(np.array(self.closes))[-1][-1])#buffer添加一个
                self.macd_area_backup.extend(self.macd_area_buffer)#backup加入buffer
                macd_area = sum(self.macd_area_backup)
                #self.macd_areas.append(sum(self.macd_area_backup))#增加一个红蓝柱面积
                self.macd_areas.append((now_fenxing[0],macd_area))#增加一个红蓝柱面积
                self.macd_area_buffer = []#清空buffer
                
                #bolling处理
                ceil = talib.BBANDS(np.array(self.closes))[0][-2]
                floor = talib.BBANDS(np.array(self.closes))[-1][-2]
                self.powerful_area = ((now_fenxing[1] > ceil) | (now_fenxing[1] < floor))
                #self.bolling_fenxing.append(self.powerful_area)
                self.bolling_fenxing.append((now_fenxing[0],self.powerful_area))
                
                #判断变量
                self.last_fenxing_datetime = now_fenxing[0]
                self.last_fenxing_type = now_fenxing[2]
    
    def process_tradesignal(self):
        
        """======================发出交易信号=================="""
        
        #至少第六个分型才能比较指标，因为这个策略是第二买卖点策略
        if len(self.fenxingTuples) < 7:return #如果六个分型都没有，则继续等待分型
        now_fenxing = self.fenxingTuples[-1]
        
        ###判断分型是否更新
        ###未更新
        if self.last_fenxing_datetime2 == now_fenxing[0]:
            return
            
        ###更新了
        else:
            ###不管替代前分型还是新增分型,满足条件的话，变一次买一次
            first_sell_macd = self.macd_areas[-3][-1]
            qian_fenxing_macd = self.macd_areas[-5][-1]
            macd_beichi = abs(first_sell_macd) < abs(qian_fenxing_macd)
            first_sell_bolling = self.bolling_fenxing[-3][-1]
            qian_fenxing_bolling = self.bolling_fenxing[-5][-1]
            bolling_beichi = (not first_sell_bolling) and qian_fenxing_bolling
            
            #对于这个分型是否是第二卖点的判断
            if now_fenxing[-1] == DING:
                first_sell_point = self.fenxingTuples[-3]
                qianding = self.fenxingTuples[-5]
                new_high = first_sell_point[1] > qianding[1]#创出新高
                no_trap1 = now_fenxing[1] < first_sell_point[1]
                if (no_trap1 and new_high) or (macd_beichi and bolling_beichi):
                    self.ding_signal = True
                    
            #对于这个分型是否是第二买点的判断
            elif now_fenxing[-1] == DI:
                first_buy_point = self.fenxingTuples[-3]
                qiandi = self.fenxingTuples[-5]
                new_low = first_buy_point[1] < qiandi[1]#创出新低
                no_trap2 = now_fenxing[1] > first_buy_point[1]
                if (no_trap2 and new_low) or (macd_beichi and bolling_beichi):
                    self.di_signal = True
                        
                            
            self.last_fenxing_datetime2 = now_fenxing[0]     
    
    def process_ordertrigger(self):
        
        """======================发出交易Order=================="""
        
        if self.di_signal:
            if self.pos < 0:
                orderID = self.cover(self.newBar['close'] + 1, -self.pos, stop=True)#平仓所有空头
                self.orderList.append(orderID)
                self.volume = 1
            #else:
            #if self.volume >=5:#最多买4+3+2+1手
            #    self.di_signal = False
            #    return
            self.buy(self.newBar['close']+1, self.volume)
            self.volume += 1
        elif self.ding_signal:
            if self.pos > 0:
                orderID = self.sell(self.newBar['close'] - 1, self.pos, stop=True)#平仓所有多头
                self.orderList.append(orderID)
                self.volume = 1
            #else:
            #if self.volume >=5:#最多做空4+3+2+1手
            #    self.ding_signal = False
            #    return
            self.short(self.newBar['close']-1, self.volume)
            self.volume += 1
        self.ding_signal = False
        self.di_signal = False
    
    #----------------------------------------------------------------------
    def onOrder(self, order):
        """收到委托变化推送（必须由用户继承实现）"""
        pass

    #----------------------------------------------------------------------
    def onTrade(self, trade):
        #print trade.volume
        
        pass

