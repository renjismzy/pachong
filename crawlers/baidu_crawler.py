# -*- coding: utf-8 -*-
"""
百度AI Studio爬虫模块
"""

import requests
import datetime
import time
from feishu_api import insert_to_feishu, get_feishu_token
from config import FEISHU_APP_ID, FEISHU_APP_SECRET, REQUEST_CONFIG, LOG_CONFIG
from utils import get_details
from duplicate_checker import DuplicateChecker

def crawl_baidu():
    """爬取百度AI Studio比赛信息"""
    print(f"{LOG_CONFIG['start_emoji']} 开始爬取百度AI Studio比赛信息...")
    base_url = "https://aistudio.baidu.com/studio/match/search?pageSize=10&matchType=0&matchStatus=1&keyword=&orderBy=0"
    page = 1
    success_count = 0
    failed_count = 0
    duplicate_count = 0
    
    # 初始化重复检查器
    duplicate_checker = DuplicateChecker()
    
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
    
    while True:
        url = f"{base_url}&p={page}"
        try:
            response = requests.get(url, timeout=REQUEST_CONFIG['timeout'])
            response.raise_for_status()
            data = response.json()
            items = data['result']['data']
            
            if not items:
                break
                
            print(f"{LOG_CONFIG['page_emoji']} 处理第 {page} 页，找到 {len(items)} 个比赛")
            
            for item in items:
                name = item['matchName']
                intro = item['matchAbs']
                link = f"https://aistudio.baidu.com/studio/match/detail/{item['id']}"
                
                participants, prize, start_date, end_date = get_details(link)

                # 只处理有效的比赛数据（进行中或即将开始的比赛）
                if (start_date is None or start_date <= datetime.datetime.now()) and (end_date is None or end_date >= datetime.datetime.now()):
                    print(f"{LOG_CONFIG['success_emoji']} 收集比赛: {name}")
                    
                    # 检查是否重复
                    duplicate_result = duplicate_checker.check_duplicate(name, "百度", link)
                    
                    if duplicate_result['is_duplicate'] and duplicate_result['recommendation'] == 'skip':
                        duplicate_count += 1
                        print(f"{LOG_CONFIG['skip_emoji']} 跳过重复比赛: {name}")
                        if duplicate_result['duplicate_type'] == 'exact':
                            print(f"   完全匹配现有记录: {duplicate_result['exact_match']['existing_title']}")
                        elif duplicate_result['duplicate_type'] == 'link':
                            print(f"   链接重复: {duplicate_result['exact_match']['existing_title']}")
                    else:
                        # 立即插入到飞书表格，传递介绍信息用于AI分析
                        if insert_to_feishu(name, link, start_date, end_date, "", "", "", intro):
                            success_count += 1
                            print(f"{LOG_CONFIG['processing_emoji']} 成功导入第 {success_count} 条数据")
                            
                            # 如果有相似匹配，给出提示
                            if duplicate_result['similar_matches']:
                                print(f"   ⚠️ 发现相似比赛 ({len(duplicate_result['similar_matches'])} 条)，请注意检查")
                        else:
                            failed_count += 1
                            print(f"{LOG_CONFIG['error_emoji']} 导入失败: {name}")
                    
                    # 每次处理后稍作延迟，避免频率限制
                    time.sleep(REQUEST_CONFIG['retry_delay'])
                else:
                    print(f"{LOG_CONFIG['skip_emoji']} 跳过过期比赛: {name}")
                    
            page += 1
            time.sleep(REQUEST_CONFIG['page_delay'])  # 页面间延迟
            
        except requests.exceptions.RequestException as e:
            print(f"{LOG_CONFIG['error_emoji']} 请求第 {page} 页时出错: {e}")
            break
        except Exception as e:
            print(f"{LOG_CONFIG['error_emoji']} 处理第 {page} 页时出错: {e}")
            break
    
    # 输出统计信息
    print(f"\n{LOG_CONFIG['stats_emoji']} 百度AI Studio爬取完成: 成功导入 {success_count} 条，跳过重复 {duplicate_count} 条，失败 {failed_count} 条")
    return success_count, failed_count, duplicate_count