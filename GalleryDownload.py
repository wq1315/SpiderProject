from gevent import monkey
import gevent
monkey.patch_all()
from gevent.pool import Pool
p = Pool(150)
'''
上面的库一定要在开头导入
'''
from itertools import product
from contextlib import suppress
import pandas as pd
import numpy as np
import glob
from tqdm import tqdm
import pandas as pd
import random
import shutil
import os
import re
import requests
from requests.packages.urllib3.util import Retry
from requests.adapters import HTTPAdapter
from requests import Session, exceptions
s = Session()
s.mount('https://', HTTPAdapter(
    max_retries=Retry(total=5, status_forcelist=[500,404])
    ))
def download_file(down_url,filepath):
    if not os.path.exists(filepath):    #如果已经存在这个文件,就不作处理
        req = s.get(down_url)    #下载图片链接
        if req.status_code == 200:    #下载成功时候状态码为200
            folder,filename = os.path.split(filepath)    #分开文件夹路径和文件名
            if not os.path.isdir(folder):    #如果目标文件夹路径不存在,则层级创建下去
                os.makedirs(folder)
            
            content = req.content    #获取图片字节保存为文件
            with open(filepath,'wb') as f:
                f.write(content)
            req.close()

'''
根据图片名查看目标位置,和检查目标位置是否存在这个文件
'''           
def IsExists(item):
    image_name = item.image_name
    uuid = item.uuid
    pid = item.pid
    side = item.side
    rot_id = int(item.rot_id)
    if side=='1':
        folderPath = os.path.join(root_path,'texture2t',pid,f'{uuid}_{rot_id//4}')
    elif side=='5':
        folderPath = os.path.join(root_path,'texture5t',pid,f'{uuid}_{rot_id//4}')
    filePath = os.path.join(folderPath,image_name)
    return os.path.exists(filePath),filePath
    if os.path.exists(filePath):
        print(image_name,',',os.path.exists(filePath))

#查看所有的线上图片
def getImageName(scale = '1'):
    sql = f'SELECT image_name FROM product_image WHERE  vector_id >0 and type like "{scale}%"'
    n = cur.execute(sql)
    data = cur.fetchall()
    df = pd.DataFrame(data)
    df.columns = ['image_name']
    df['uuid'] = df['image_name'].apply(lambda image_name:re.findall(r'(\d+)_.*?_\d_\d_\d+',image_name)[0])
    #过滤不正确的pid图片
    result = filter(lambda item:re.findall(r'\d+_([0-9]{9}[A-Za-z]{0,2})_\d_\d_\d+',item['image_name']),df.to_dict('records'))
    df = pd.DataFrame(result)

    #获取每张图片的pid,正反面,拍摄角度信息
    df['side'] = df['image_name'].apply(lambda image_name:re.findall(r'\d+_.*?_(\d)_\d_\d+.jpg',image_name)[0])
    df['pid'] = df['image_name'].apply(lambda image_name:re.findall(r'\d+_(.*?)_\d_\d_\d+.jpg',image_name)[0])
    df['rot_id'] = df['image_name'].apply(lambda image_name:re.findall(r'\d+_.*?_\d_\d_(\d+).jpg',image_name)[0])
    #获取下载文件存储地址和目标文件是否已经下载
    df[['isexist','filepath']] = df.apply(lambda item:IsExists(item),axis=1,result_type='expand')   
    #获取下载链接
    df['file_url'] = df['image_name'].apply(lambda image_name:root_url+image_name)
    return df

'''
异步下载图片文件
'''
def asynchronous(image_file):
    threads = [p.spawn(download_file,k,v) for index,(k,v) in enumerate(image_file.items())]
    gevent.joinall(threads)

'''
查看线上的图片库所有图片和线下的开发图片进行比对,下载不存在线下的图片
'''
import pymysql
import re


conn = pymysql.connect(**args)
cur = conn.cursor()


if __name__=='__main__':
    #整理还没有下载的文件
    image_file = {}
    for scale in ['1','5']:
        df = getImageName(scale)
        for item in tqdm(list(df[df['isexist']==False].itertuples())):
            filepath = item.filepath
            file_url = item.file_url
            image_file[file_url] = filepath
    cur.close()
    conn.close()
    '''
    异步下载
    '''
    print('num:',len(image_file))
    asynchronous(image_file)
    print('下载完成......................')
