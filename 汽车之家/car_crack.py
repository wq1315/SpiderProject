from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.common.by import By
from selenium import webdriver
from bs4 import BeautifulSoup
import pandas as ps
import numpy as np
import requests
import re
import json
import uuid
import math
import pymssql
import time
import warnings

warnings.filterwarnings('ignore')
import ssl
ssl._create_default_https_context = ssl._create_unverified_context

class carcollection(object):
    def __init__(self, user='', password='', database=''):   # 在这里修改数据库链接信息
        # 配置数据库
        self.conn = pymssql.connect(host = 'localhost:1433', user=user, password=password, database=database,autocommit = True)
        self.words = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'
        # 读取城市信息
        #         self.citycode = pd.read_excel('citycode.xls')
        self.header = self.__class__.setheader(self)

    def setheader(self):
        header = {
            'Referer': 'https://www.autohome.com.cn/car/',
            'Upgrade-Insecure-Requests': '1',
            'User-Agent': 'Mozilla/5.0 (Windows NT 6.1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.36'
        }
        return header

    def getdriver(self, softpath=r'C:\data\chromedriver_win32\chromedriver.exe'):
        option = webdriver.ChromeOptions()
        option.add_argument('--headless')
        option.add_argument('--disable-gpu')
        option.add_argument('disable-infobars')
        driver = webdriver.Chrome(softpath, chrome_options=option)
        driver.maximize_window()
        return driver

    # 一级页面采集方法
    # params: ip置换参数
    def collectcarlist(self, ip=None):
        cur = self.conn.cursor()
        proxies = {
            "http": ip,
            # "https": "https://221.228.17.172:8181",
        }
        for word in self.words:
            url = 'https://www.autohome.com.cn/grade/carhtml/{0}.html'.format(word)
            content = requests.get(url, headers=self.header, proxies=proxies).content
            soup = BeautifulSoup(content, "html.parser")
            for li in soup.find_all('li', attrs={'id': re.compile('s\d+')}):
                a = li.find_all('a')
                guid = str(uuid.uuid4())
                id = re.findall(r'\d+', a[0]['href'])[0]  # 车型id
                n = cur.execute("select * from original_001_carlist where k001_000001 =%s ", (id))
                if n > 0:
                    continue
                a2 = a[0].text  # 车型
                try:
                    a3 = a[0]['class'][0]  # 是否存在车主报价
                    a3 = 0
                except:
                    a3 = 1
                sql = ' insert into original_001_carlist(proj_url_id,collect_time,collect_url,k001_000001,k001_000002,k001_000003,regname,regtime,status)values(%s,%s,%s,%s,%s,%s,%s,%s,%s)'
                params = (guid, time.strftime('%Y%m%d'), url, id, a2, a3, '包子xia', time.strftime('%Y%m%d'), '1')
                cur.execute(sql, params)
            time.sleep(1)

    # 二级页面采集
    # params: ip置换参数
    def collectpriceinfo(self, ip=None):
        url = ''
        cur = self.conn.cursor()
        cur1 = self.conn.cursor()
        proxies = {
            "http": ip,
            # "https": "https://221.228.17.172:8181",
        }
        cur1.execute("select proj_url_id,k001_000001 from original_001_carlist where k001_000003= '1' order by id desc")
        for row in cur1.fetchall():
            guid = row[0]
            code = ''
            seriesId = row[1]  # 车型id
            #             for code in self.citycode['Id']:
            #                 code = code#城市id
            # 查看数据库中是否存在对应城市的对应车型，已存在时则不录入。
            n = cur.execute("select * from original_001_priceinfo where k001_000001=%s ", (seriesId))
            if n > 0:
                continue
            link1 = "https://jiage.autohome.com.cn/price/getspeclist?seriesId={0}&locid=&yearId=".format(seriesId)

            req = requests.get(link1, headers=self.header, proxies=proxies)
            try:
                content1 = req.json()['result']
            except:
                continue
            if len(content1) > 0:
                for name in content1:
                    name = name  # 性能类别
                    for item in content1[name]:
                        pjbusinessid = str(uuid.uuid4())
                        avgNakePrice = item['avgNakePrice']  # 车主裸车价
                        avgFullPrice = item['avgFullPrice']  # 车主购车全款
                        specName = item['specName']  # 款式类别
                        specid = item['id']  # 款式id
                        total = item['total']  # 报价数目
                        factoryPrice = item['factoryPrice']  # 厂家指导价
                        year = item['year']  # 年份
                        sql = ' insert into original_001_priceinfo(pjbusinessid,proj_url_id,collect_time,collect_url,k001_000001,k001_000002,k001_000003,k001_000004,k001_000005,k001_000006,k001_000007,k001_000008,k001_000009,k001_000010,regname,regtime,status)values(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)'
                        params = (
                        pjbusinessid, guid, time.strftime('%Y%m%d'), url, seriesId, code, name, specName, specid, total,
                        factoryPrice, year, avgNakePrice, avgFullPrice, '包子xia', time.strftime('%Y%m%d'), '1')
                        cur.execute(sql, params)
                        cur.commit()
            req.close()
        # 三级页面数据采集

    def getownerprice(self):
        cur = self.conn.cursor()
        cur1 = self.conn.cursor()
        driver = self.getdriver()
        cur1.execute(
            "SELECT  k001_000002,k001_000005,k001_000007,pjbusinessid,proj_url_id ,k001_000006 FROM original_001_priceinfo WHERE k001_000006 != '0'")
        #         cur1.execute("select proj_url_id,k001_000001 from original_001_carlist where k001_000003=1 order by id desc")
        for item in cur1.fetchall():
            city_code = item[0]
            car_id = item[1]
            fctPrice = item[2]
            pjbusinessid = item[3]
            n = cur.execute("select * from original_001_ownerprice where pjbusinessid=%s", (pjbusinessid))
            if n > 0:
                continue
            proj_url_id = item[4]
            number = item[5]
            num = math.ceil(int(number) / 10)
            for i in range(num):
                url = 'https://jiage.autohome.com.cn/price/carlist/p-{0}-1-0-0-0-0-{1}-0'.format(car_id, str(i + 1))
                driver.get(url)
                # car-lists-item-use-name-detail
                try:
                    locator = (By.LINK_TEXT, '车主价格官方账号')
                    ele = WebDriverWait(driver, 10, ignored_exceptions=True, poll_frequency=2).until(
                        EC.presence_of_element_located(locator))
                    time.sleep(0.5)
                except:
                    continue
                data = driver.execute_script("return result;")
                json_datas = data['specList']['list']
                for json_data in json_datas:
                    nakedPriceHide = json_data['nakedPriceHide']
                    useTax = json_data['useTax']
                    purchaseTax = json_data['purchaseTax']
                    trafficInsurance = json_data['trafficInsurance']
                    insurer = json_data['insurer']
                    licenseFee = json_data['licenseFee']
                    cityNameBuyCar = json_data['cityNameBuyCar']
                    shoppingTimeFormat = json_data['shoppingTimeFormat']
                    creatTime = json_data['creatTime']
                    fctPrice = fctPrice
                    try:
                        purchaseTax = purchaseTax.replace(',', '')
                    except:
                        pass
                    try:
                        insurer = insurer.replace(',', '')
                    except:
                        pass
                    try:
                        licenseFee = licenseFee.replace(',', '')
                    except:
                        pass
                    nakedPriceHide = float(nakedPriceHide)
                    useTax = float(useTax)
                    purchaseTax = float(purchaseTax)
                    trafficInsurance = float(trafficInsurance)
                    insurer = float(insurer)
                    licenseFee = float(licenseFee)
                    fullPrice = nakedPriceHide + useTax + purchaseTax + trafficInsurance + insurer + licenseFee
                    sql = "insert into original_001_ownerprice(pjbusinessid,proj_url_id,k001_000001,k001_000002,k001_000003,k001_000004,k001_000005,k001_000006,k001_000007,k001_000008,k001_000009,k001_000010,k001_000011) values(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)"
                    params = (pjbusinessid, proj_url_id, nakedPriceHide, useTax, purchaseTax, trafficInsurance, insurer,
                              licenseFee, cityNameBuyCar, shoppingTimeFormat, creatTime, fctPrice,
                              float('%.2f' % fullPrice))
                    cur.execute(sql, params)
                    cur.commit()


if __name__ == '__main__':
    # 数据库参数配置
    # 账号
    user = ''
    # 密码
    password = ''
    # 数据库名称
    database = ''
    car = carcollection(user=user, password=password, database=database)
    #ip
    ip = None
    car.collectcarlist(ip=ip)
    car.collectpriceinfo(ip=ip)
    car.getownerprice()


