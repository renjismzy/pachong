# -*- coding: utf-8 -*-
"""
阿里云天池爬虫模块
"""

import requests
import datetime
import time
from feishu_api import insert_to_feishu, get_feishu_token
from config import FEISHU_APP_ID, FEISHU_APP_SECRET, REQUEST_CONFIG, LOG_CONFIG
from utils import get_details
from duplicate_checker import DuplicateChecker

def crawl_aliyun():
    """爬取阿里天池比赛信息"""
    print(f"{LOG_CONFIG['start_emoji']} 开始爬取阿里天池比赛信息...")
    base_url = "https://tianchi.aliyun.com/v3/proxy/competition/api/race/page?visualTab=&raceName=&isActive="
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
        url = f"{base_url}&pageNum={page}"
        headers = {'User-Agent': REQUEST_CONFIG['user_agent']}
        
        try:
            response = requests.get(url, headers=headers, timeout=REQUEST_CONFIG['timeout'])
            response.raise_for_status()
            data = response.json()
            
            if not data.get('success', False):
                print(f"{LOG_CONFIG['error_emoji']} API返回失败: {data.get('message', '未知错误')}")
                break
                
            items = data.get('data', {}).get('list', [])
            if not items:
                break
                
            print(f"{LOG_CONFIG['page_emoji']} 处理第 {page} 页，找到 {len(items)} 个比赛")
            
            for item in items:
                name = item.get('name', 'Unknown')
                intro = item.get('introduction', 'Not available')
                link = f"https://tianchi.aliyun.com/competition/entrance/{item.get('raceId', '')}/introduction"
                
                # 尝试从API数据中获取日期信息
                api_start_date = None
                api_end_date = None
                
                if 'gmtStart' in item and item['gmtStart']:
                    try:
                        api_start_date = datetime.datetime.fromtimestamp(item['gmtStart'] / 1000)
                    except:
                        pass
                        
                if 'gmtEnd' in item and item['gmtEnd']:
                    try:
                        api_end_date = datetime.datetime.fromtimestamp(item['gmtEnd'] / 1000)
                    except:
                        pass
                
                # 从页面获取详细信息
                participants, prize, page_start_date, page_end_date = get_details(link)
                
                # 优先使用API中的日期，如果没有则使用页面提取的日期
                start_date = api_start_date or page_start_date
                end_date = api_end_date or page_end_date
                
                # 只处理有效的比赛数据（进行中或即将开始的比赛）
                if (start_date is None or start_date <= datetime.datetime.now()) and (end_date is None or end_date >= datetime.datetime.now()):
                    print(f"{LOG_CONFIG['success_emoji']} 收集比赛: {name}")
                    
                    # 检查是否重复
                    duplicate_result = duplicate_checker.check_duplicate(name, "阿里云", link)
                    
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
    print(f"\n{LOG_CONFIG['stats_emoji']} 阿里天池爬取完成: 成功导入 {success_count} 条，跳过重复 {duplicate_count} 条，失败 {failed_count} 条")
    return success_count, failed_count, duplicate_count