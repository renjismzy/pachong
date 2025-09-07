# -*- coding: utf-8 -*-
"""
腾讯CSDN博客爬虫模块
"""

import datetime
import time
from feishu_api import insert_to_feishu, get_feishu_token
from config import FEISHU_APP_ID, FEISHU_APP_SECRET, SELENIUM_CONFIG, LOG_CONFIG
from utils import get_details

def crawl_tencent():
    """爬取腾讯CSDN博客比赛信息"""
    print(f"{LOG_CONFIG['start_emoji']} 开始爬取腾讯CSDN博客比赛信息...")
    success_count = 0
    failed_count = 0
    
    # 检查飞书配置
    if not FEISHU_APP_ID or not FEISHU_APP_SECRET:
        print(f"{LOG_CONFIG['error_emoji']} 飞书配置缺失！请检查.env文件中的FEISHU_APP_ID和FEISHU_APP_SECRET")
        print(f"{LOG_CONFIG['info_emoji']} 请访问 https://open.feishu.cn/app 创建应用并获取配置信息")
        return
    
    # 测试飞书连接
    test_token = get_feishu_token()
    if not test_token:
        print(f"{LOG_CONFIG['error_emoji']} 无法连接到飞书，请检查配置")
        return
    
    print(f"{LOG_CONFIG['success_emoji']} 飞书连接正常，开始逐个导入比赛数据...")
    
    try:
        from selenium import webdriver
        from selenium.webdriver.chrome.options import Options
        from selenium.webdriver.common.by import By
        from selenium.webdriver.support.ui import WebDriverWait
        from selenium.webdriver.support import expected_conditions as EC
        from bs4 import BeautifulSoup
        
        options = Options()
        options.headless = SELENIUM_CONFIG['headless']
        for arg in SELENIUM_CONFIG['chrome_options']:
            options.add_argument(arg)
        
        driver = webdriver.Chrome(options=options)
        url = 'https://blog.csdn.net/QcloudCommunity/article/list'
        
        print(f"{LOG_CONFIG['page_emoji']} 正在访问: {url}")
        driver.get(url)
        
        # 等待页面加载
        WebDriverWait(driver, SELENIUM_CONFIG['wait_timeout']).until(
            EC.presence_of_element_located((By.CLASS_NAME, "article-item-box"))
        )
        
        # 获取页面源码并解析
        soup = BeautifulSoup(driver.page_source, 'html.parser')
        articles = soup.find_all('div', class_='article-item-box')
        
        print(f"{LOG_CONFIG['page_emoji']} 找到 {len(articles)} 篇文章")
        
        for article in articles:
            try:
                # 获取文章标题和链接
                title_elem = article.find('h4')
                if not title_elem:
                    continue
                    
                link_elem = title_elem.find('a')
                if not link_elem:
                    continue
                    
                name = title_elem.get_text().strip()
                link = link_elem.get('href', '')
                
                # 只处理包含"赛"字的文章
                if '赛' not in name:
                    continue
                
                # 确保链接是完整的URL
                if link.startswith('/'):
                    link = 'https://blog.csdn.net' + link
                elif not link.startswith('http'):
                    continue
                
                print(f"{LOG_CONFIG['processing_emoji']} 处理文章: {name}")
                
                # 获取文章简介
                intro_elem = article.find('p', class_='content')
                intro = intro_elem.get_text().strip() if intro_elem else 'Not found'
                
                # 获取详细信息
                participants, prize, start_date, end_date = get_details(link)
                
                # 只处理有效的比赛数据（进行中或即将开始的比赛）
                if (start_date is None or start_date <= datetime.datetime.now()) and (end_date is None or end_date >= datetime.datetime.now()):
                    print(f"{LOG_CONFIG['success_emoji']} 收集比赛: {name}")
                    
                    # 立即插入到飞书表格，传递介绍信息用于AI分析
                    if insert_to_feishu(name, link, start_date, end_date, "", "", "", intro):
                        success_count += 1
                        print(f"{LOG_CONFIG['processing_emoji']} 成功导入第 {success_count} 条数据")
                    else:
                        failed_count += 1
                        print(f"{LOG_CONFIG['error_emoji']} 导入失败: {name}")
                    
                    # 每次插入后稍作延迟，避免频率限制
                    time.sleep(1)
                else:
                    print(f"{LOG_CONFIG['skip_emoji']} 跳过过期比赛: {name}")
                    
            except Exception as e:
                print(f"{LOG_CONFIG['warning_emoji']} 处理文章时出错: {e}")
                continue
        
        driver.quit()
                
    except ImportError:
        print(f"{LOG_CONFIG['error_emoji']} 缺少selenium依赖，请安装: pip install selenium")
        return
    except Exception as e:
        print(f"{LOG_CONFIG['error_emoji']} 爬取腾讯博客时出错: {e}")
        return
    
    # 输出统计信息
    print(f"\n{LOG_CONFIG['stats_emoji']} 腾讯CSDN博客爬取完成: 成功导入 {success_count} 条，失败 {failed_count} 条")
    return success_count, failed_count