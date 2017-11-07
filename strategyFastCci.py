# encoding: UTF-8
"""
大于100,小于130时买入，回到一百到115之间卖出；小于-100做空，回到-100回补，很有效果
"""
from ctaBase import *
from ctaTemplate import CtaTemplate
from Queue import Queue

import talib
import numpy as np


########################################################################
class FastCciStrategy(CtaTemplate):
    """结合CCI指标的一个分钟线交易策略"""
    className = 'FastCciStrategy'
    author = u'老耕'

    # 策略参数
    cciN = 100
    cciLongEntry = cciN                 # CCI的开多信号
    cciShortEntry = -cciN               # CCI的开空信号
    cciIntraLong = cciN                   # 建仓后最高CCI
    cciIntraShort = -cciN                  # 建仓后最低CCI
    
    initDays = 1                       # 初始化数据所用的天数

    # 风控参数
    
    # 重采样变量
    barList = []                     # 对于k线重采样的list
    # 重采样参数
    BARLEVEL = 5                        # 分钟线级别
    
    # 策略变量
    bar = None                  # K线对象
    account = None              # VtAccount对象
    barMinute = EMPTY_STRING    # K线当前的分钟

    bufferSize = 14                    # 需要缓存的数据的大小
    bufferCount = 0                     # 目前已经缓存了的数据的计数
    highArray = np.zeros(bufferSize)    # K线最高价的数组
    lowArray = np.zeros(bufferSize)     # K线最低价的数组
    closeArray = np.zeros(bufferSize)   # K线收盘价的数组
    
    cciCount = 0                        # 目前已经缓存了的CCI的计数
    cciArray = np.zeros(bufferSize)     # CCI指标的数组
    cciValue = 0                        # 最新的CCI指标数值
    orderList = []                      # 保存委托代码的列表
    
    # 测试变量
    posmax = 0                             # 最大持仓量

    # 参数列表，保存了参数的名称
    paramList = ['name',
                 'className',
                 'author',
                 'vtSymbol',
                 'bufferSize',
                 'cciEntry',]    

    # 变量列表，保存了变量的名称
    varList = ['inited',
               'trading',
               'pos',
               'cciValue']  

    #----------------------------------------------------------------------
    def __init__(self, ctaEngine, setting):
        """Constructor"""
        super(FastCciStrategy, self).__init__(ctaEngine, setting)
        
        # 注意策略类中的可变对象属性（通常是list和dict等），在策略初始化时需要重新创建，
        # 否则会出现多个策略实例之间数据共享的情况，有可能导致潜在的策略逻辑错误风险，
        # 策略类中的这些可变对象属性可以选择不写，全都放在__init__下面，写主要是为了阅读
        # 策略时方便（更多是个编程习惯的选择）        

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
#        print account.available

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
        
        # 重采样K线
        #bar = self.minuteBarFacory(bar)
        #if not bar:return      
        
        # 保存K线数据
        self.closeArray[0:self.bufferSize-1] = self.closeArray[1:self.bufferSize]
        self.highArray[0:self.bufferSize-1] = self.highArray[1:self.bufferSize]
        self.lowArray[0:self.bufferSize-1] = self.lowArray[1:self.bufferSize]
        
        self.closeArray[-1] = bar.close
        self.highArray[-1] = bar.high
        self.lowArray[-1] = bar.low
        
        self.bufferCount += 1
        if self.bufferCount < self.bufferSize:
            return

        # 计算指标数值
        self.cciValue = talib.CCI(self.highArray, 
                                  self.lowArray, 
                                  self.closeArray,
                                  self.bufferSize)[-1]
        self.cciArray[0:self.bufferSize-1] = self.cciArray[1:self.bufferSize]
        self.cciArray[-1] = self.cciValue

        if not self.cciValue:
            return
        # 判断是否要进行交易
        #print self.cciValue
        pos = abs(self.pos)
#        self.posmax = max(pos,self.posmax)
        if self.posmax < pos:
            print str(self.pos) + " ==> $ " + str(bar.close)
            self.posmax = pos
        # 当前无仓位
        v = 0
        if self.pos == 0:
            if self.cciValue > self.cciLongEntry:
                v = int(self.cciValue - self.cciLongEntry)*2
                self.buy(bar.close + 1 , v)
            
            elif self.cciValue < self.cciShortEntry:
                v = int(self.cciShortEntry - self.cciValue )*2
                self.short(bar.close - 1, v)
            
        # 持有多头仓位
        elif self.pos > 0:
            if self.cciValue > self.cciIntraLong:
                v = int(self.cciValue - self.cciLongEntry)*2
                self.buy(bar.close + 1 , v)
                self.cciIntraLong = self.cciValue
            elif self.cciValue < self.cciIntraLong:
                orderID = self.sell(bar.close, self.pos, stop=True)
                self.cciIntraLong = self.cciN
                self.orderList.append(orderID)
        # 持有空头仓位
        elif self.pos < 0:
            if self.cciValue < self.cciIntraShort:
                v = int(self.cciShortEntry - self.cciValue)*2
                self.short(bar.close - 1, v)
                self.cciIntraShort = self.cciValue

            elif self.cciValue > self.cciIntraShort:
                orderID = self.cover(bar.close, - self.pos, stop=True)
                self.cciIntraShort = -self.cciN
                self.orderList.append(orderID)
        # 发出状态更新事件
        self.putEvent()
    
    #============================== methods ===============================
    @classmethod
    def regulateVolume(self,v):
        """"""
    def minuteBarFacory(self,bar):
        """对分钟线进行重采样"""
        self.barList.append(bar)
        if len(self.barList) == self.BARLEVEL:
            openL,highL,lowL,closeL,volumeL = [],[],[],[],[]
            for ibar in self.barList:
                openL.append(ibar.open)
                highL.append(ibar.high)
                lowL.append(ibar.low)
                closeL.append(ibar.close)
                volumeL.append(ibar.volume)
            newBar = bar
            newBar.open = openL[0]
            newBar.high = max(highL)
            newBar.low = min(lowL)
            newBar.close = closeL[-1]
            newBar.volume = sum(volumeL)
            self.barList = []
            return newBar
        else:
            if len(self.barList)>5:
                raise RuntimeError
            else:
                if bar:
                    self.barList.append(bar)
            return None

    #======================================================================
    
    #----------------------------------------------------------------------
    def onOrder(self, order):
        """收到委托变化推送（必须由用户继承实现）"""
        pass

    #----------------------------------------------------------------------
    def onTrade(self, trade):
        pass

