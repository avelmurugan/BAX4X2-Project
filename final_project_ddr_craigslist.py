#!/usr/bin/env python
# coding: utf-8

# In[6]:


from bs4 import BeautifulSoup
from urllib.request import Request, urlopen
import requests
import re
import numpy as np
import pandas as pd
import time
from selenium.webdriver.common.by import By
from selenium import webdriver
import codecs
import os
from selenium.webdriver.support.ui import WebDriverWait
from pymongo import MongoClient
from selenium.webdriver.support import expected_conditions
import http.client, urllib.parse
from datetime import datetime


# In[7]:


#num_page=72 for SF
#num_page=33 for San Diego
#num_page=61 for LA

#function to scrape full craigslist page
def scrape_full_page(region, num_page, fp_full_page):
    #set region url
    url='https://'+region+'.craigslist.org/search/cta?hasPic=1&purveyor=owner#search=1~gallery~0~0'
    #get selenium web driver
    browser=webdriver.Chrome('chromedriver')
        #set browser wait
    browser.implicitly_wait(1)
            # Make first search
    #get url
    bc_search = browser.get(url)
    #set 'next' button
    button_path='//*[@id="search-toolbars-2"]/div[1]/button[3]'
    #loop through all pages
    for i in range(0, num_page):
        #wait ten seconds for page to load
        time.sleep(10)
        #download page to disk
        with open(fp_full_page+"/craigslist"+str(i+1)+".html", "w", encoding = 'utf-8') as f:
                    f.write(browser.page_source)
        #sleep system
        time.sleep(5)
        #click 'next' button
        browser.find_element(By.XPATH, button_path).click()
    #quit browser
    browser.quit()


# In[8]:


#Function to get all individual pages
def get_page_url(num_page, fp_full_page):
    #create empty list
    url_list=[]
    #loop through all individual pages
    for i in range(0,num_page):
        #open full page object
        htmlfile=open(fp_full_page+"/craigslist"+str(i+1)+".html", "r").read()
        #Convert to soup object
        soup=BeautifulSoup(htmlfile, 'html.parser')
        #loop through all href
        for i in soup.find_all('a',{'class':'titlestring'}):
            #append to url list
            url_list.append(i.get('href'))
    #return url list
    return url_list


# In[9]:


#function to download indiv pages
def get_individual_page(num_page, fp_indiv_page, fp_full_page):
    #pause loop for page to load
    time.sleep(5)
    #get urls
    url_list=get_page_url(num_page, fp_full_page)
    #loop through URLS
    for i in range(0, len(url_list)):
        #set header
        hdr = {'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.11 (KHTML, like Gecko) Chrome/23.0.1271.64 Safari/537.11',
          'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
          'Accept-Charset': 'ISO-8859-1,utf-8;q=0.7,*;q=0.3',
          'Accept-Encoding': 'none',
          'Accept-Language': 'en-US,en;q=0.8',
          'Connection': 'keep-alive'}
        #open url and parse result 
        page = requests.get(url_list[i], headers=hdr)
        soup = BeautifulSoup(page.content, 'html.parser')
        #write result to disk
        with open(fp_indiv_page+"/craigslist_car_page"+str(i+1)+'.html', "w", encoding = 'utf-8') as file:
                    # prettify the soup object and convert it into a string  
                    file.write(str(soup))
        time.sleep(3)


# In[10]:


#function to get all attributes from individual pages
def get_att(collection, fp_indiv_page, num_page, fp_full_page):
    #call individual page function
    get_individual_page(num_page, fp_indiv_page, fp_full_page)
    #set client
    mo_c = MongoClient()
    client = MongoClient('localhost', 27017)
    #create new database
    db = client["craigslist_cars"]
    #set desired collection
    collection=collection
    #get the url list
    url_list=get_page_url(num_page, fp_full_page)
    print('got url list')
    #set brand list of 24 brands
    brand_list=['audi', 'ford', 'chevy',
               'lexus','nissan','dodge','chevrolet','mazda',
               'acura','volkswagen','mercedes','gmc','kia','honda',
               'porsche','infiniti','scion','jeep','vw','subaru','mitsubishi',
               'toyota','hyundai','tesla','fiat','mini cooper','infiniti']
    print('starting loop')
    #loop through url list
    for i in range(0, len(url_list)):
        #create empty dic
        dic={}
        #get url
        dic['url']=url_list[i]
        #open indiv page and convert to soup object
        html_file=open(fp_indiv_page+"/craigslist_car_page"+str(i+1)+".html", "r").read()
        soup=BeautifulSoup(html_file, 'html.parser')
        #set empty attributes list 
        attributes=[]
        #loop through all attribute objects
        for att in soup.find_all('p',{'class':'attrgroup'}):
            for d in att.find_all('span'):
                #append to list
                attributes.append(d.text)
        print(attributes)
        #set function to retrieve attribute values from previous list
        def get_attribute(el):
            return [i for i in attributes if el in i][0]
        #try and except statements to account for situations where the brand isn't present
        try:
            #get full listing title
            full_car_brand=soup.find('span',{'id':'titletextonly'}).text
            dic['full_car_brand']=full_car_brand
            title=full_car_brand.lower()
            #get year with regex
            dic['year']=float(re.findall(r'.*([1-3][0-9]{3})', title)[0])
        except:
            pass
        try:
            #find if any of the brands are in the title
            dic['brand']=[brand for brand in brand_list if(brand in title)][0]
        except:
            dic['brand']=np.nan

        try:
            #find fuel attribute
            fuel=get_attribute('fuel')
            #clean up valie
            fuel=fuel.replace('fuel: ','')
            dic['fuel']=fuel
        except:
            pass
        try:
            #get odometer value and clean up
            odo=get_attribute('odometer')
            odo=float(odo.replace('odometer: ',''))
            dic['odo']=float(odo)
        except:
            pass
        try:
            #get condition value and clean up
            cond=get_attribute('condition')
            cond=cond.replace('condition: ','')
            dic['cond']=cond
        except:
            pass
        try:
            #get paint value and clean up
            paint=get_attribute('paint color')
            paint=paint.replace('paint color: ','')
            dic['paint']=paint
        except:
            pass
        try:
            #get size value and clean it up
            size=get_attribute('size')
            size=size.replace('size: ','')
            dic['size']=size
        except:
            pass
        try:
            #get cylinders value and clean it up
            cyl=get_attribute('cylinders')
            cyl=cyl.replace('cylinders','')
            cyl=float(cyl.replace(':',''))
            dic['cyl']=cyl
        except:
            pass
        try:
            #get title value and clean it up
            title=get_attribute('title')
            title=title.replace('title status: ','')
            dic['title']=title
        except:
            pass
        try:
            #get transmission value and clean it up
            trans=get_attribute('transmission')
            trans=trans.replace('transmission: ','')
            dic['trans']=trans
        except:
            pass
        try:
            #get drive value and clean it up
            drive=get_attribute('drive')
            drive=drive.replace('drive: ','')
            dic['drive']=drive
        except:
            pass
        try:
            #get body type value and clean it up
            body_type=get_attribute('type')
            body_type=body_type.replace('type: ','')
            dic['body_type']=body_type
        except:
            pass
        try:
            #get image url
            dic['img_url']=soup.find('img').get('src')
        except:
            pass
        try:
            #get price and clean it up
            price=soup.find('span',{'class':'price'}).text
            price=price.replace('$','')
            price=price.replace(',','')
            dic['price']=float(price)
        except:
            pass
        try:
            #empty dic for nested documents
            time_dic={}
            object_id=[]
            #find all time values
            for i in soup.find_all('time',{'class':'date timeago'}):
                object_id.append(i.text.split())
            #convert to datetime and append to dictionary
            time_dic['posted_time']=pd.to_datetime(object_id[0][1])
            time_dic['last_updated_time']=pd.to_datetime(object_id[1][1])
            #append whole dictionary to outer dictionary
            dic['posted_stats']=time_dic
        except:
            pass
        #insert a value to collection
        collection.insert_one(dic)
        print(i)
        print(dic)
    #set index
    collection.create_index('brand')


# In[11]:


#create new collection 'bayc'
mo_c = MongoClient()
client = MongoClient('localhost', 27017)
#create new database
db = client["craigslist_cars"]
collection_bay = db["bay_area"]
collection_sd=db['sd']
collection_la=db['los_angeles']


# In[ ]:


#num_page=72 for SF
#num_page=33 for San Diego
#num_page=61 for Los Angeles
#region is sfbay, sandiego, and losangeles
if __name__ == '__main__':
    scrape_full_page('losangeles', 61,'full_page_la')
    get_att(collection_la, 'individual_page_la', 61, 'full_page_la')


# # Note
# 
# This code takes a long time to run. I have provided the full result of the scrape, feel free to verify that it worked with the provided files.
