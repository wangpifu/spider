#-*- coding: utf-8 -*-
import bisect
import socket
import urllib2
import re,os,sys
import zlib
import htmllib,formatter,string
from googleresult import pygoogle
from os.path import join, getsize
import robotparser

class PriorityQueue(list):
    #"优先级队列,用于存储url,及它的优先级"
    def __init__(self):
        list.__init__(self)
        self.map = {}
        
    def push(self, item):
    # 按顺序插入，防止重复元素;若要按升序排列，可使用bisect.insort_left
        if self.count(item) == 0:
            bisect.insort(self, item)
            self.map[ item[1] ] = item
        
    def pop(self):
        r = list.pop(self)
        del self.map[ r[1] ]
        return r
        
    def getitem(self,url):
        if self.map.has_key( url ):
            return self.map[url]
        else :
            return None
        
    def empty(self):
        return len(self) == 0
        
    def remove(self,item):
        list.remove(self, item)
        del self.map[ item[1] ]
    
    def count(self,item):
        if len(self) == 0 :
            return 0
        #二分查找
        left = 0
        right = len(self)-1
        mid = -1
        while left <= right:
            mid = (left+right)/2
            if self[mid] < item :
                left = mid + 1
            elif self[mid] > item :
                right = mid -1
            else :
                break

        return self[mid] == item and 1 or 0

    def unVisitedpqDeQuence(self):
        try:
            return self.pq.pop()[1]
        except:
            return None

class linkQuence:
    def __init__(self):
     #已访问的url集合
        self.visted=[]
     #待访问的url集合
        self.unVisited=[]
    #获取访问过的url队列
    def getVisitedUrl(self):
        return self.visted
    #获取未访问的url队列
    def getUnvisitedUrl(self):
        return self.unVisited
    #添加到访问过得url队列中
    def addVisitedUrl(self,url):
        self.visted.append(url)
    #移除访问过得url
    def removeVisitedUrl(self,url):
        self.visted.remove(url)
    #未访问过得url出队列
    def unVisitedUrlDeQuence(self):
        try:
            return self.unVisited.pop()
        except:
            return None
    #保证每个url只被访问一次
    def addUnvisitedUrl(self,url):
        if url!="" and url not in self.visted and url not in self.unVisited:
            self.unVisited.insert(0,url)
    #获得已访问的url数目
    def getVisitedUrlCount(self):
        return len(self.visted)
    #获得未访问的url数目
    def getUnvistedUrlCount(self):
        return len(self.unVisited)
    #判断未访问的url队列是否为空
    def unVisitedUrlsEnmpy(self):
        return len(self.unVisited)==0

class GetLinks(htmllib.HTMLParser):
    def __init__(self):
        self.links={}
        f = formatter.NullFormatter()
        htmllib.HTMLParser.__init__(self,f)
        self.body=False
        self.gate=True
    
    def anchor_bgn(self,href,name,type):
        self.save_bgn()
        self.link=href
            
    def anchor_end(self):
        text=string.strip(self.save_end())
        if self.link and text:
            self.links[text]=self.link

class BodyContentOnly(htmllib.HTMLParser):
    
    def __init__(self):
        self.links={}
        f = formatter.NullFormatter()
        htmllib.HTMLParser.__init__(self,f)
        self.body=False
        self.gate=True
        self.content=""

    def handle_starttag(self, tag, method, attrs):
        if tag=='body':
            self.body=True
        elif tag=='script':
            self.gate=False

    def handle_endtag(self, tag, method):
        if tag=='body':
            self.body=False
        elif tag=='script':
            self.gate=True

    def handle_data(self, data):
        if self.body and self.gate and not data is None:
            self.content+=data+" "

class MyCrawler:
    def __init__(self,seeds,query,dicPath = os.path.abspath(os.path.dirname(sys.argv[0]))+"\\page_downloads"):
        self.current_deepth = 1           #初始化当前抓取的深度,目前未启用
        self.pq=PriorityQueue()           #初始化优先队列
        self.linkQuence=linkQuence()
        if isinstance(seeds,str):
            self.linkQuence.addUnvisitedUrl(seeds)
        if isinstance(seeds,list):
            for i in seeds:
                self.linkQuence.addUnvisitedUrl(i)
        self.query=query                   #调用查询词
        self.pageCount=1                   #初始化下载文件名称
        self.dicPath = dicPath             #初始化下载目录
    
    def crawling(self,seeds,crawl_deepth,query):                       #抓取过程主函数,可以启用深度抓取，默认为按数量抓取
        amount=int(input('please input how many files you want to crawl(interger): '))
        if os.path.exists(self.dicPath) == False :
            os.makedirs(self.dicPath)
        #循环条件：待抓取的链接不空且不多于规定要求
        while (not self.linkQuence.unVisitedUrlsEnmpy() or not self.pq.empty() ) and self.linkQuence.getVisitedUrlCount()<amount:
            if not self.linkQuence.unVisitedUrlsEnmpy() :             #队头url出原始队列
                visitUrl=self.linkQuence.unVisitedUrlDeQuence()
            if not self.pq.empty():                                   #队列头出优先队列
                try:
                    visitUrl=self.pq.pop()[1]
                except:
                    continue
            
            if visitUrl is None or visitUrl=="":
                continue

            if visitUrl in self.linkQuence.visted:                     #已经访问
                continue
            #print visitUrl
            rp=robotparser.RobotFileParser()
            rp.set_url(visitUrl)
            rp.read()
            if not rp.can_fetch('*',visitUrl):
                continue
            data=self.getPageSource(visitUrl)
            if data is None or data[1] is None:
                continue
            links = self.getHyperLinks(visitUrl,data)                       #获取超链接
            if links is None:
                continue
            key_freq = self.getkeywordfreq(visitUrl,query,data)             #获取query频率
            try:
                filePath = self.dicPath+"\\"+str(self.pageCount)+".html"
                self.pageCount += 1
                file = open(filePath,'w')
                file.write(data[1])
                file.close()
            except:
                print "file write error" 
            unpriolist = []                                            #过渡列表，存储权值和url
            for link in links:
                unpriolist.append((key_freq,link))

            print str(self.linkQuence.getVisitedUrlCount()+1)+'  '+str(visitUrl)+'  '+str(key_freq)
            self.linkQuence.addVisitedUrl(visitUrl)                    #已访问的url入列

            for link in unpriolist:                                    #将国度列表push进优先队列
                self.pq.push(link)

        self.current_deepth += 1                                       #为深度准备，现在未启用
        print 'spider finished work'
        print 'there are %.3f Mbs files and amount of these files is %s' %(self.getdirsize(self.dicPath)[0]/1024/1024,self.getdirsize(self.dicPath)[1])
    
    def getdirsize(self,dir):
        size = 0.000
        amount=0
        for root, dirs, files in os.walk(dir):
            size += sum([getsize(join(root, name)) for name in files])
        amount = sum([len(files) for root,dirs,files in os.walk(dir)])
        return [size,amount]     
    
    #获取源码中得超链接    
    def getHyperLinks(self,url,data):
        links=[]
        data=data#self.getPageSource(url)
        if data[0]=="200":           
            try:
                from bs4 import BeautifulSoup
                soup=BeautifulSoup(data[1])
                a=soup.findAll("a",{"href":re.compile('^http|^/')})
                for i in a:
                    if i["href"].find("http://")!=-1:
                        links.append(i["href"])
                return links
            except :
                try:
                    self.getLinks=GetLinks()
                    #print data[1]
                    self.getLinks.feed(data[1])
                    self.getLinks.close()
                    for href,link in self.getLinks.links.iteritems():
                        if link.find("http://")!=-1:
                            links.append(link)
                    return links
                except:
                    return None

    #获取源码中的关键字
    def getkeywordfreq(self,url,query,data):
        key_freq=0
        content=""
        data=data #self.getPageSource(url)
        self.getContent=BodyContentOnly()
        self.getContent.feed(data[1])
        self.getContent.close()
        content=self.getContent.content
        #print content
        content=re.sub(r'\s+',' ',content)
        tokens=content.split(" ")
        key_freq=0
        for keyword in query:
            keyword=keyword.lower()
            b=content.count(keyword)
            key_freq+=b
        return key_freq
 
    #获取网页源码
    def getPageSource(self,url,timeout=100,coding=None):
        try:
            socket.setdefaulttimeout(timeout)
            req = urllib2.Request(url)
            req.add_header('User-agent', 'Mozilla/4.0 (compatible; MSIE 6.0; Windows NT 5.1)')
            response = urllib2.urlopen(req)
            page = '' 
            htmlpattern=re.compile(r'^text/html')
            doctype=response.headers.get('Content-Type')
            if not htmlpattern.match(doctype):
                #print response.headers.get('Content-Type')
                return  None
            #print response.headers.get('Content-Type')
            if response.headers.get('Content-Encoding') == 'gzip': 
                page = zlib.decompress(page, 16+zlib.MAX_WBITS) 
         
            if coding is None:   
                coding= response.headers.getparam("charset")   
            #如果获取的网站编码为None 
            if coding is None:   
                page=response.read()   
            #获取网站编码并转化为utf-8 
            else:           
                page=response.read()   
                page=page.decode(coding).encode('utf-8')  
            return ["200",page]
        except Exception,e:
            print str(e)
            return [str(e),None]

def excited(seeds,crawl_deepth,query):
    craw=MyCrawler(seeds,query)
    craw.crawling(seeds,crawl_deepth,query)




if __name__=="__main__":
    inputquery=input('enter query here in quotes,seperated by space: ')
    inputquery=inputquery.lower()
    Firsten=[]
    g = pygoogle(inputquery)
    g.pages = 2
    for url in g.get_urls()[0:10]:
        Firsten.append(url)
    query=inputquery.split()
    excited(Firsten,3,query)
