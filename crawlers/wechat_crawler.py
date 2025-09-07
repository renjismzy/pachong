# -*- coding: utf-8 -*-
"""
微信公众号爬虫模块
"""

import requests
import datetime
from config import REQUEST_CONFIG, LOG_CONFIG, CRAWLER_CONFIG
from utils import get_details

def get_biz_banner():
    """获取公众号banner信息"""
    wechat_config = CRAWLER_CONFIG['wechat']
    headers = {
        'User-Agent': REQUEST_CONFIG['user_agent'],
        'Cookie': wechat_config['cookie']
    }
    
    url = f'https://mp.weixin.qq.com/cgi-bin/appmsg?action=list_ex&begin=0&count=1&fakeid={wechat_config["fakeid"]}&type=9&query=&token={wechat_config["token"]}&lang=zh_CN&f=json&ajax=1'
    
    try:
        response = requests.get(url, headers=headers, timeout=REQUEST_CONFIG['timeout'])
        data = response.json()
        return data.get('app_msg_list', [])
    except Exception as e:
        print(f"{LOG_CONFIG['warning_emoji']} 获取banner信息失败: {e}")
        return []

def get_video_snaps(link):
    """获取视频快照信息"""
    try:
        response = requests.get(link, timeout=REQUEST_CONFIG['timeout'])
        # 这里可以添加视频快照提取逻辑
        return "Video snap extraction not implemented"
    except Exception as e:
        print(f"{LOG_CONFIG['warning_emoji']} 获取视频快照失败: {e}")
        return "Not available"

def get_comments(link):
    """获取文章评论信息"""
    try:
        response = requests.get(link, timeout=REQUEST_CONFIG['timeout'])
        # 这里可以添加评论提取逻辑
        return "Comment extraction not implemented"
    except Exception as e:
        print(f"{LOG_CONFIG['warning_emoji']} 获取评论失败: {e}")
        return "Not available"

def crawl_wechat():
    """爬取微信公众号文章信息"""
    print(f"{LOG_CONFIG['start_emoji']} 开始爬取微信公众号文章信息...")
    
    wechat_config = CRAWLER_CONFIG['wechat']
    headers = {
        'User-Agent': REQUEST_CONFIG['user_agent'],
        'Cookie': wechat_config['cookie']
    }
    
    # 获取公众号banner信息
    print(f"{LOG_CONFIG['processing_emoji']} 获取公众号banner信息...")
    banner = get_biz_banner()
    print(f"{LOG_CONFIG['info_emoji']} 公众号Banner: {banner}")
    
    base_url = 'https://mp.weixin.qq.com/cgi-bin/appmsg'
    begin = 0
    success_count = 0
    failed_count = 0
    
    while True:
        params = {
            'action': 'list_ex',
            'begin': str(begin),
            'count': '5',
            'fakeid': wechat_config['fakeid'],
            'type': '9',
            'query': '',
            'token': wechat_config['token'],
            'lang': 'zh_CN',
            'f': 'json',
            'ajax': '1'
        }
        
        try:
            response = requests.get(base_url, headers=headers, params=params, timeout=REQUEST_CONFIG['timeout'])
            data = response.json()
            
            if 'app_msg_list' not in data or not data['app_msg_list']:
                break
            
            print(f"{LOG_CONFIG['page_emoji']} 处理从 {begin} 开始的 {len(data['app_msg_list'])} 篇文章")
            
            for item in data['app_msg_list']:
                # 只处理标题包含"赛"的文章
                if '赛' in item['title']:
                    link = item['link']
                    name = item['title']
                    create_time = item.get('create_time', 'Unknown')
                    
                    print(f"{LOG_CONFIG['processing_emoji']} 处理文章: {name}")
                    
                    # 获取详细信息
                    participants, prize, start_date, end_date = get_details(link)
                    
                    # 只处理有效的比赛数据（进行中或即将开始的比赛）
                    if (start_date is None or start_date <= datetime.datetime.now()) and (end_date is None or end_date >= datetime.datetime.now()):
                        print(f"{LOG_CONFIG['success_emoji']} 收集比赛: {name}")
                        print(f"{LOG_CONFIG['info_emoji']} 链接: {link}")
                        print(f"{LOG_CONFIG['info_emoji']} 创建时间: {create_time}")
                        
                        # 获取额外信息
                        comments = get_comments(link)
                        video_snaps = get_video_snaps(link)
                        
                        print(f"{LOG_CONFIG['info_emoji']} 评论: {comments}")
                        print(f"{LOG_CONFIG['info_emoji']} 视频快照: {video_snaps}")
                        
                        success_count += 1
                    else:
                        print(f"{LOG_CONFIG['skip_emoji']} 跳过过期比赛: {name}")
                        failed_count += 1
            
            begin += len(data['app_msg_list'])
            
            # 如果返回的文章数量少于请求数量，说明已经到最后一页
            if len(data['app_msg_list']) < 5:
                break
                
        except requests.exceptions.RequestException as e:
            print(f"{LOG_CONFIG['error_emoji']} 请求失败: {e}")
            break
        except Exception as e:
            print(f"{LOG_CONFIG['error_emoji']} 处理数据时出错: {e}")
            break
    
    # 输出统计信息
    print(f"\n{LOG_CONFIG['stats_emoji']} 微信公众号爬取完成: 成功处理 {success_count} 条，跳过 {failed_count} 条")
    return success_count, failed_count