import json

from crawler.imdb_crawler import *


conf_path = 'imdb.conf'
conf_file = open(conf_path, encoding='UTF-8')
conf = json.load(conf_file)
conf_file.close()

link_path = 'E:\\workspace\\fdu\\MovieLens\\ml-20m\\links.csv'
links_file = open(link_path, encoding='UTF-8')
links = links_file.readlines()
links_file.close()

ic = IMDBCrawler(conf, links, 'E:\\workspace\\fdu\\MovieLens\\ml-20m\\data\\')
ic.crawl()
