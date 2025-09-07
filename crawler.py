import requests
import json
from bs4 import BeautifulSoup
import argparse
import re
import time
import sys
import os
import datetime
from dotenv import load_dotenv
load_dotenv()
app_id = os.getenv('FEISHU_APP_ID')
app_secret = os.getenv('FEISHU_APP_SECRET')
deepseek_api_key = os.getenv('DEEPSEEK_API_KEY')
app_token = 'XgmKbtiiUa8mLhsHDsQcNQKBnVg'
table_id = 'tblgA8hErJNkgZGm'
def update_all_competition_status():
    """更新所有比赛的状态，将已结束的比赛标记为已结束
    
    Returns:
        tuple: (更新成功数量, 更新失败数量)
    """
    print("🔄 开始更新所有比赛状态...")
    
    # 获取所有记录
    all_records = get_all_records()
    if not all_records:
        print("❌ 无法获取表格记录")
        return 0, 0
    
    success_count = 0
    failed_count = 0
    
    for record in all_records:
        try:
            record_id = record.get('record_id')
            fields = record.get('fields', {})
            
            # 获取比赛名称用于日志
            name = fields.get('比赛名称', 'Unknown')
            
            # 获取当前状态
            current_status = fields.get('比赛状态', '进行中')
            
            # 如果已经是已结束状态，跳过
            if current_status == '已结束':
                continue
            
            # 这里需要从比赛链接获取详细信息来判断是否已结束
            # 由于我们移除了比赛时间字段，需要重新获取比赛详情
            link_field = fields.get('比赛链接', {})
            if isinstance(link_field, dict):
                link = link_field.get('link', '')
            else:
                link = str(link_field) if link_field else ''
            
            if link:
                # 获取比赛详情
                participants, prize, start_date, end_date = get_details(link)
                
                # 判断比赛状态
                new_status = determine_competition_status(start_date, end_date)
                
                # 如果状态需要更新为已结束
                if new_status == '已结束' and current_status != '已结束':
                    if update_record_status(record_id, '已结束'):
                        print(f"✅ 已更新比赛状态: {name} -> 已结束")
                        success_count += 1
                    else:
                        print(f"❌ 更新失败: {name}")
                        failed_count += 1
                    
                    # 添加延迟避免频率限制
                    time.sleep(0.5)
            
        except Exception as e:
            print(f"⚠️ 处理记录时出错: {e}")
            failed_count += 1
    
    print(f"📊 状态更新完成: 成功 {success_count} 条，失败 {failed_count} 条")
    return success_count, failed_count

def analyze_competition_with_deepseek(name, description=""):
    """使用DeepSeek AI分析比赛类型和难度等级"""
    if not deepseek_api_key:
        print("⚠️ DeepSeek API密钥未配置，使用默认分类")
        return ['其它'], ['L2']
    
    try:
        # 构建分析提示
        prompt = f"""
请分析以下比赛信息，并返回JSON格式的分类结果：

比赛名称：{name}
比赛描述：{description}

请根据以下标准进行分类：

比赛类型（可多选）：
- wibe coding: 编程、算法、代码相关比赛
- MCP: 多模态、跨平台、综合性技术比赛
- AI智能体: AI、机器学习、深度学习相关比赛
- AI视频: 视频处理、计算机视觉、多媒体相关比赛
- 其它: 不属于以上类别的比赛

难度等级（单选）：
- L1: 刚接触电脑，适合完全没有编程基础的初学者
- L2: 会用电脑，有基本的计算机操作能力
- L3: 对电脑比较熟练，有一定的编程和开发经验
- L4: 对电脑很熟悉，专业开发者或高级技术人员

请返回JSON格式：
{{
  "competition_types": ["类型1", "类型2"],
  "difficulty_level": "L2"
}}
"""
        
        headers = {
            'Authorization': f'Bearer {deepseek_api_key}',
            'Content-Type': 'application/json'
        }
        
        data = {
            'model': 'deepseek-chat',
            'messages': [
                {
                    'role': 'user',
                    'content': prompt
                }
            ],
            'temperature': 0.1,
            'max_tokens': 500
        }
        
        response = requests.post(
            'https://api.deepseek.com/chat/completions',
            headers=headers,
            json=data,
            timeout=30
        )
        
        if response.status_code == 200:
            result = response.json()
            content = result['choices'][0]['message']['content']
            
            # 尝试解析JSON响应
            try:
                # 清理可能的markdown代码块标记
                clean_content = content.strip()
                if clean_content.startswith('```json'):
                    clean_content = clean_content[7:]
                if clean_content.endswith('```'):
                    clean_content = clean_content[:-3]
                clean_content = clean_content.strip()
                
                analysis = json.loads(clean_content)
                comp_types = analysis.get('competition_types', ['其它'])
                difficulty = analysis.get('difficulty_level', 'L2')
                
                print(f"🤖 AI分析结果: 类型={comp_types}, 难度={difficulty}")
                return comp_types, [difficulty]
            except json.JSONDecodeError:
                print(f"⚠️ AI响应解析失败: {content}")
                return ['其它'], ['L2']
        else:
            print(f"❌ DeepSeek API调用失败: {response.status_code}")
            return ['其它'], ['L2']
            
    except Exception as e:
        print(f"❌ DeepSeek分析出错: {str(e)}")
        return ['其它'], ['L2']

def get_feishu_token():
    # 检查配置是否存在
    if not app_id or not app_secret:
        print("❌ 飞书配置缺失！请检查.env文件中的FEISHU_APP_ID和FEISHU_APP_SECRET")
        print("💡 请访问 https://open.feishu.cn/app 创建应用并获取配置信息")
        return None
        
    url = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal/"
    payload = {"app_id": app_id, "app_secret": app_secret}
    
    try:
        response = requests.post(url, json=payload, timeout=30)
        if response.status_code != 200:
            print(f"❌ 获取飞书token失败: {response.status_code} - {response.text}")
            return None
        
        data = response.json()
        if data.get('code') != 0:
            print(f"❌ 飞书API返回错误: {data.get('msg', '未知错误')}")
            return None
            
        return data["tenant_access_token"]
    except requests.exceptions.RequestException as e:
        print(f"❌ 网络请求失败: {e}")
        return None
    except Exception as e:
        print(f"❌ 解析响应失败: {e}")
        return None
def insert_to_feishu(name, link, start_date=None, end_date=None, cover_image="", difficulty_level="", competition_type="", description="", max_retries=3):
    """将比赛数据插入到飞书表格中
    
    Args:
        name: 比赛名称
        link: 比赛链接
        start_date: 比赛开始时间
        end_date: 比赛结束时间
        cover_image: 比赛封面
        difficulty_level: 难度等级
        competition_type: 比赛类型
        description: 比赛描述（用于AI分析）
    
    Returns:
        bool: 插入是否成功
    """
    # 数据验证
    if not name or not link:
        print(f"错误：比赛名称或链接为空 - 名称: {name}, 链接: {link}")
        return False
    
    # 检查记录是否已存在
    exists, record_id = check_record_exists(name, link)
    if exists:
        # 如果记录已存在，检查并更新状态
        competition_status = determine_competition_status(start_date, end_date)
        if competition_status == "已结束":
            if update_record_status(record_id, "已结束"):
                print(f"✅ 已更新比赛状态为已结束: {name}")
            else:
                print(f"❌ 更新比赛状态失败: {name}")
        print(f"⏭️ 跳过重复记录: {name}")
        return True
    
    # 使用DeepSeek AI分析比赛类型和难度等级（如果未提供或为空）
    if not difficulty_level or not competition_type:
        print(f"🤖 使用AI分析比赛: {name}")
        ai_types, ai_difficulty = analyze_competition_with_deepseek(name, description)
        
        # 如果原参数为空，使用AI分析结果
        if not competition_type:
            competition_type = ai_types[0] if ai_types else "其它"
        if not difficulty_level:
            difficulty_level = ai_difficulty[0] if ai_difficulty else "L2"
    
    # 确定比赛状态
    competition_status = determine_competition_status(start_date, end_date)
    
    # 获取访问令牌
    token = get_feishu_token()
    if not token:
        print("错误：无法获取飞书访问令牌")
        return False
    
    url = f"https://open.feishu.cn/open-apis/bitable/v1/apps/{app_token}/tables/{table_id}/records"
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    
    # 构建请求数据 - 按照飞书要求的格式
    def clean_text(text):
        """清理文本，移除特殊字符和换行符"""
        if not text:
            return ""
        # 转换为字符串并移除换行符、制表符等特殊字符
        cleaned = str(text).replace('\n', ' ').replace('\r', ' ').replace('\t', ' ')
        # 移除多余的空格
        cleaned = ' '.join(cleaned.split())
        return cleaned
    
    # 根据飞书表格字段格式要求构建数据
    def format_difficulty_level(level):
        """将难度等级转换为多选格式"""
        if not level:
            return []
        level_str = str(level).upper()
        valid_levels = ['L1', 'L2', 'L3', 'L4']
        # 尝试匹配已知的难度等级
        for valid_level in valid_levels:
            if valid_level in level_str:
                return [valid_level]
        # 如果没有匹配到，默认返回L2
        return ['L2']
    
    def format_competition_type(comp_type):
        """将比赛类型转换为多选格式"""
        if not comp_type:
            return []
        type_str = str(comp_type).lower()
        valid_types = ['wibe coding', 'MCP', 'AI智能体', 'AI视频', '其它']
        result = []
        
        # 检查是否包含已知类型
        if 'coding' in type_str or '编程' in type_str:
            result.append('wibe coding')
        elif 'mcp' in type_str:
            result.append('MCP')
        elif 'ai' in type_str or '智能' in type_str:
            if '视频' in type_str or 'video' in type_str:
                result.append('AI视频')
            else:
                result.append('AI智能体')
        
        # 如果没有匹配到任何类型，返回其它
        return result if result else ['其它']
    
    payload = {
        "fields": {
            "比赛名称": clean_text(name)[:500],
            "比赛链接": {
                "text": clean_text(name)[:100],
                "link": clean_text(link)[:500]
            },
            "比赛状态": competition_status,
            "难度等级": format_difficulty_level(difficulty_level),
            "比赛类型": format_competition_type(competition_type)
        }
    }
    
    # 如果有封面图片URL，按照飞书附件格式添加
    if cover_image and cover_image.strip():
        payload["fields"]["比赛封面"] = [{
            "file_token": "",
            "name": "比赛封面",
            "url": clean_text(cover_image)[:500]
        }]
    
    # 重试机制
    for attempt in range(max_retries):
        try:
            response = requests.post(url, headers=headers, json=payload, timeout=30)
            
            if response.status_code == 200:
                result = response.json()
                if result.get('code') == 0:
                    print(f"✅ 成功插入数据: {name}")
                    return True
                else:
                    print(f"❌ 飞书API返回错误: {result.get('msg', '未知错误')}")
                    print(f"详细错误信息: {result}")
            elif response.status_code == 401:
                print("❌ 认证失败，请检查飞书应用配置")
                return False
            elif response.status_code == 429:
                print(f"⚠️ 请求频率过高，等待后重试 (尝试 {attempt + 1}/{max_retries})")
                time.sleep(2 ** attempt)  # 指数退避
                continue
            else:
                print(f"❌ HTTP错误 {response.status_code}: {response.text}")
                
        except requests.exceptions.Timeout:
            print(f"⚠️ 请求超时，重试中 (尝试 {attempt + 1}/{max_retries})")
        except requests.exceptions.RequestException as e:
            print(f"⚠️ 网络错误: {e} (尝试 {attempt + 1}/{max_retries})")
        except Exception as e:
            print(f"❌ 未知错误: {e}")
            return False
        
        if attempt < max_retries - 1:
            time.sleep(1)  # 重试前等待
    
    print(f"❌ 插入失败，已重试 {max_retries} 次: {name}")
    return False

def get_all_records():
    """获取表格中的所有记录
    
    Returns:
        list: 所有记录的列表，每个记录包含record_id和fields
    """
    token = get_feishu_token()
    if not token:
        return []
    
    url = f"https://open.feishu.cn/open-apis/bitable/v1/apps/{app_token}/tables/{table_id}/records"
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    
    all_records = []
    page_token = None
    
    try:
        while True:
            params = {"page_size": 500}
            if page_token:
                params["page_token"] = page_token
            
            response = requests.get(url, headers=headers, params=params, timeout=30)
            if response.status_code == 200:
                result = response.json()
                if result.get('code') == 0:
                    data = result.get('data', {})
                    records = data.get('items', [])
                    all_records.extend(records)
                    
                    # 检查是否还有更多页面
                    page_token = data.get('page_token')
                    if not page_token:
                        break
                else:
                    print(f"❌ 获取记录失败: {result.get('msg', '未知错误')}")
                    break
            else:
                print(f"❌ HTTP错误 {response.status_code}: {response.text}")
                break
                
    except Exception as e:
        print(f"⚠️ 获取所有记录时出错: {e}")
    
    return all_records

def check_record_exists(name, link):
    """检查记录是否已存在
    
    Args:
        name: 比赛名称
        link: 比赛链接
    
    Returns:
        tuple: (是否存在, 记录ID) - 如果存在返回(True, record_id)，否则返回(False, None)
    """
    token = get_feishu_token()
    if not token:
        return False, None
    
    url = f"https://open.feishu.cn/open-apis/bitable/v1/apps/{app_token}/tables/{table_id}/records/search"
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    
    # 使用比赛链接作为唯一标识符进行查询
    payload = {
        "filter": {
            "conditions": [
                {
                    "field_name": "比赛链接",
                    "operator": "is",
                    "value": [link]
                }
            ],
            "conjunction": "and"
        }
    }
    
    try:
        response = requests.post(url, headers=headers, json=payload, timeout=30)
        if response.status_code == 200:
            result = response.json()
            if result.get('code') == 0:
                records = result.get('data', {}).get('items', [])
                if len(records) > 0:
                    return True, records[0].get('record_id')
                return False, None
    except Exception as e:
        print(f"⚠️ 检查记录存在性时出错: {e}")
    
    return False, None

def update_record_status(record_id, status):
    """更新记录的比赛状态
    
    Args:
        record_id: 记录ID
        status: 比赛状态 ("进行中" 或 "已结束")
    
    Returns:
        bool: 更新是否成功
    """
    token = get_feishu_token()
    if not token:
        return False
    
    url = f"https://open.feishu.cn/open-apis/bitable/v1/apps/{app_token}/tables/{table_id}/records/{record_id}"
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    
    payload = {
        "fields": {
            "比赛状态": status
        }
    }
    
    try:
        response = requests.put(url, headers=headers, json=payload, timeout=30)
        if response.status_code == 200:
            result = response.json()
            if result.get('code') == 0:
                return True
            else:
                print(f"❌ 更新记录状态失败: {result.get('msg', '未知错误')}")
        else:
            print(f"❌ HTTP错误 {response.status_code}: {response.text}")
    except Exception as e:
        print(f"⚠️ 更新记录状态时出错: {e}")
    
    return False

def determine_competition_status(start_date, end_date):
    """根据比赛时间确定比赛状态
    
    Args:
        start_date: 开始时间
        end_date: 结束时间
    
    Returns:
        str: 比赛状态 ("进行中" 或 "已结束")
    """
    now = datetime.datetime.now()
    
    # 如果有结束时间且已过期，则为已结束
    if end_date and end_date < now:
        return "已结束"
    
    # 如果有开始时间且还未开始，则为进行中（即将开始）
    # 如果正在进行中或时间不明确，默认为进行中
    return "进行中"

def batch_insert_to_feishu(records_data, batch_size=10):
    """批量插入数据到飞书表格
    
    Args:
        records_data: 记录数据列表，每条记录包含(name, link, competition_time, cover_image, difficulty_level, competition_type)
        batch_size: 批量大小
    
    Returns:
        tuple: (成功数量, 失败数量)
    """
    # 首先检查飞书配置
    if not app_id or not app_secret:
        print("❌ 无法插入数据：飞书配置缺失")
        print("💡 请在.env文件中配置FEISHU_APP_ID和FEISHU_APP_SECRET")
        print("📝 数据已收集完成，配置好飞书后可重新运行程序插入数据")
        return 0, len(records_data)
    
    success_count = 0
    failed_count = 0
    
    # 测试飞书连接
    test_token = get_feishu_token()
    if not test_token:
        print("❌ 无法连接到飞书，跳过数据插入")
        return 0, len(records_data)
    
    print(f"✅ 飞书连接正常，开始批量插入 {len(records_data)} 条数据...")
    
    for i in range(0, len(records_data), batch_size):
        batch = records_data[i:i + batch_size]
        print(f"\n📦 处理批次 {i//batch_size + 1}: {len(batch)} 条记录")
        
        for record in batch:
            name, link, competition_time, cover_image, difficulty_level, competition_type = record
            
            # 检查是否已存在（这里的逻辑已经在insert_to_feishu中处理了）
            # 插入记录
            if insert_to_feishu(name, link, None, None, cover_image, difficulty_level, competition_type):
                success_count += 1
            else:
                failed_count += 1
            
            # 批次间延迟，避免频率限制
            time.sleep(0.5)
        
        # 批次间稍长延迟
        if i + batch_size < len(records_data):
            time.sleep(2)
    
    print(f"\n📊 批量插入完成: 成功 {success_count} 条，失败 {failed_count} 条")
    return success_count, failed_count

def crawl_wechat(biz, token, cookie):
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3',
        'Cookie': cookie
    }
    # Fetch biz banner first
    print("Fetching biz banner...")
    banner = get_biz_banner(biz, token, cookie)
    print("Biz Banner:", banner)
    base_url = 'https://mp.weixin.qq.com/cgi-bin/appmsg'
    begin = 0
    while True:
        params = {
            'action': 'list_ex',
            'begin': str(begin),
            'count': '5',
            'fakeid': biz,
            'type': '9',
            'query': '',
            'token': token,
            'lang': 'zh_CN',
            'f': 'json',
            'ajax': '1'
        }
        response = requests.get(base_url, headers=headers, params=params)
        data = response.json()
        if 'app_msg_list' not in data or not data['app_msg_list']:
            break
        for item in data['app_msg_list']:
            if '赛' in item['title']:
                link = item['link']
                participants, prize, start_date, end_date = get_details(link)  # Reuse get_details for article
                if (start_date is None or start_date <= datetime.datetime.now()) and (end_date is None or end_date >= datetime.datetime.now()):
                    print(f"Title: {item['title']}")
                    print(f"Link: {item['link']}")
                    print(f"Create Time: {item['create_time']}")
                    print(f"Participants: {participants}")
                    print(f"Prize: {prize}")
                    # Parse mid and idx from link
                    from urllib.parse import urlparse, parse_qs
                    parsed_url = urlparse(item['link'])
                    query_params = parse_qs(parsed_url.query)
                    mid = query_params.get('mid', [''])[0]
                    idx = query_params.get('idx', [''])[0]
                    sn = query_params.get('sn', [''])[0]
                    if mid and idx:
                        print("Fetching comments...")
                        comments = get_comments(biz, token, cookie, mid, idx)
                        for comment in comments:
                            print(f"Comment: {comment['content']}")
                            print(f"Author: {comment.get('nick_name', 'Anonymous')}")
                            print("---")
                        print("Fetching video snaps...")
                        video_snaps = get_video_snaps(biz, token, cookie)
                    print("---")
        begin += 5
        time.sleep(2)

def get_biz_banner(biz, token, cookie):
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3',
        'Cookie': cookie
    }
    base_url = 'https://mp.weixin.qq.com/mp/getbizbanner'
    params = {
        '__biz': biz,
        'uin': '',
        'key': '',
        'pass_ticket': '',
        'wxtoken': '777',
        'devicetype': '',
        'clientversion': 'false',
        'version': 'false',
        'appmsg_token': '',
        'x5': '0',
        'f': 'json',
        'user_article_role': '0'
    }
    response = requests.get(base_url, headers=headers, params=params)
    data = response.json()
    return data

def get_video_snaps(biz, appmsg_token, cookie):
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3',
        'Cookie': cookie
    }
    base_url = 'https://mp.weixin.qq.com/mp/appmsg_video_snap'
    params = {
        'action': 'batch_get_video_snap',
        'uin': '',
        'key': '',
        'pass_ticket': '',
        'wxtoken': '777',
        'devicetype': '',
        'clientversion': 'false',
        'version': 'false',
        '__biz': biz,
        'appmsg_token': appmsg_token,
        'x5': '0',
        'f': 'json',
        'user_article_role': '0'
    }
    response = requests.get(base_url, headers=headers, params=params)
    data = response.json()
    print("Video Snaps:", data)
    return data
def get_comments(biz, token, cookie, appmsgid, idx):
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3',
        'Cookie': cookie
    }
    base_url = 'https://mp.weixin.qq.com/mp/appmsg_comment'
    params = {
        'action': 'getcomment',
        'scene': '0',
        '__biz': biz,
        'appmsgid': appmsgid,
        'idx': idx,
        'comment_id': '',  # Can be set if needed for specific comment
        'offset': '0',
        'limit': '100',
        'send_time': '',
        'sessionid': '',
        'enterid': '',
        'top_content_id': '',
        'top_reply_id': '',
        'comment_scene': '0',
        'uin': '',
        'key': '',
        'pass_ticket': '',
        'wxtoken': '777',
        'devicetype': '',
        'clientversion': 'false',
        'version': 'false',
        'appmsg_token': '',
        'x5': '0',
        'f': 'json',
        'user_article_role': '0'
    }
    response = requests.get(base_url, headers=headers, params=params)
    data = response.json()
    if 'base_resp' in data and data['base_resp']['ret'] == 0:
        comments = data.get('elected_comment', [])
        for comment in comments:
            print(f"Comment ID: {comment['comment_id']}")
            print(f"Content: {comment['content']}")
            if 'reply_list' in comment:
                for reply in comment['reply_list']:
                    print(f"Reply: {reply['content']}")
        # Parse cookie to extract parameters
        cookie_dict = dict(item.split('=') for item in cookie.split('; ') if '=' in item)
        uin = cookie_dict.get('wxuin', '')
        key = cookie_dict.get('rand_info', '')  # Assuming rand_info might be key, adjust if needed
        pass_ticket = cookie_dict.get('data_ticket', '')  # Assuming data_ticket as pass_ticket, adjust if needed
        # Fetch identity list
        identity_params = {
            'action': 'getidentitylist',
            'scene': '0',
            'register': '0',
            'uin': uin,
            'key': key,
            'pass_ticket': pass_ticket,
            'wxtoken': '777',
            'devicetype': '',
            'clientversion': 'false',
            'version': 'false',
            '__biz': biz,
            'appmsg_token': token,  # Use provided token as appmsg_token
            'x5': '0',
            'f': 'json',
            'user_article_role': '0'
        }
        identity_response = requests.get(base_url, headers=headers, params=identity_params)
        identity_data = identity_response.json()
        print("Identity List:", identity_data)
        return comments
    else:
        print("Failed to fetch comments:", data)
        return []

def crawl_baidu():
    """爬取百度AI Studio比赛信息"""
    print("🚀 开始爬取百度AI Studio比赛信息...")
    base_url = "https://aistudio.baidu.com/studio/match/search?pageSize=10&matchType=0&matchStatus=1&keyword=&orderBy=0"
    page = 1
    success_count = 0
    failed_count = 0
    
    # 检查飞书配置
    if not app_id or not app_secret:
        print("❌ 飞书配置缺失！请检查.env文件中的FEISHU_APP_ID和FEISHU_APP_SECRET")
        print("💡 请访问 https://open.feishu.cn/app 创建应用并获取配置信息")
        return
    
    # 测试飞书连接
    test_token = get_feishu_token()
    if not test_token:
        print("❌ 无法连接到飞书，请检查配置")
        return
    
    print("✅ 飞书连接正常，开始逐个导入比赛数据...")
    
    while True:
        url = f"{base_url}&p={page}"
        try:
            response = requests.get(url, timeout=30)
            response.raise_for_status()
            data = response.json()
            items = data['result']['data']
            
            if not items:
                break
                
            print(f"📄 处理第 {page} 页，找到 {len(items)} 个比赛")
            
            for item in items:
                name = item['matchName']
                intro = item['matchAbs']
                link = f"https://aistudio.baidu.com/studio/match/detail/{item['id']}"
                
                participants, prize, start_date, end_date = get_details(link)

                # 只处理有效的比赛数据（进行中或即将开始的比赛）
                if (start_date is None or start_date <= datetime.datetime.now()) and (end_date is None or end_date >= datetime.datetime.now()):
                    print(f"✅ 收集比赛: {name}")
                    
                    # 立即插入到飞书表格，传递介绍信息用于AI分析
                    if insert_to_feishu(name, link, start_date, end_date, "", "", "", intro):
                        success_count += 1
                        print(f"📝 成功导入第 {success_count} 条数据")
                    else:
                        failed_count += 1
                        print(f"❌ 导入失败: {name}")
                    
                    # 每次插入后稍作延迟，避免频率限制
                    time.sleep(1)
                else:
                    print(f"⏭️ 跳过过期比赛: {name}")
                    
            page += 1
            time.sleep(2)  # 页面间延迟
            
        except requests.exceptions.RequestException as e:
            print(f"❌ 请求第 {page} 页时出错: {e}")
            break
        except Exception as e:
            print(f"❌ 处理第 {page} 页时出错: {e}")
            break
    
    # 输出统计信息
    print(f"\n📊 百度AI Studio爬取完成: 成功导入 {success_count} 条，失败 {failed_count} 条")

def crawl_aliyun():
    """爬取阿里天池比赛信息"""
    print("🚀 开始爬取阿里天池比赛信息...")
    base_url = "https://tianchi.aliyun.com/v3/proxy/competition/api/race/page?visualTab=&raceName=&isActive="
    page = 1
    success_count = 0
    failed_count = 0
    
    # 检查飞书配置
    if not app_id or not app_secret:
        print("❌ 飞书配置缺失！请检查.env文件中的FEISHU_APP_ID和FEISHU_APP_SECRET")
        print("💡 请访问 https://open.feishu.cn/app 创建应用并获取配置信息")
        return
    
    # 测试飞书连接
    test_token = get_feishu_token()
    if not test_token:
        print("❌ 无法连接到飞书，请检查配置")
        return
    
    print("✅ 飞书连接正常，开始逐个导入比赛数据...")
    
    while True:
        url = f"{base_url}&pageNum={page}"
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3'}
        
        try:
            response = requests.get(url, headers=headers, timeout=30)
            response.raise_for_status()
            data = response.json()
            
            if not data.get('success', False):
                print(f"❌ API返回失败: {data.get('message', '未知错误')}")
                break
                
            items = data.get('data', {}).get('list', [])
            if not items:
                break
                
            print(f"📄 处理第 {page} 页，找到 {len(items)} 个比赛")
            
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
                    print(f"✅ 收集比赛: {name}")
                    
                    # 立即插入到飞书表格，传递介绍信息用于AI分析
                    if insert_to_feishu(name, link, start_date, end_date, "", "", "", intro):
                        success_count += 1
                        print(f"📝 成功导入第 {success_count} 条数据")
                    else:
                        failed_count += 1
                        print(f"❌ 导入失败: {name}")
                    
                    # 每次插入后稍作延迟，避免频率限制
                    time.sleep(1)
                else:
                    print(f"⏭️ 跳过过期比赛: {name}")
                    
            page += 1
            time.sleep(2)  # 页面间延迟
            
        except requests.exceptions.RequestException as e:
            print(f"❌ 请求第 {page} 页时出错: {e}")
            break
        except Exception as e:
            print(f"❌ 处理第 {page} 页时出错: {e}")
            break
    
    # 输出统计信息
    print(f"\n📊 阿里天池爬取完成: 成功导入 {success_count} 条，失败 {failed_count} 条")

def crawl_tencent():
    """爬取腾讯CSDN博客比赛信息"""
    print("🚀 开始爬取腾讯CSDN博客比赛信息...")
    success_count = 0
    failed_count = 0
    
    # 检查飞书配置
    if not app_id or not app_secret:
        print("❌ 飞书配置缺失！请检查.env文件中的FEISHU_APP_ID和FEISHU_APP_SECRET")
        print("💡 请访问 https://open.feishu.cn/app 创建应用并获取配置信息")
        return
    
    # 测试飞书连接
    test_token = get_feishu_token()
    if not test_token:
        print("❌ 无法连接到飞书，请检查配置")
        return
    
    print("✅ 飞书连接正常，开始逐个导入比赛数据...")
    
    try:
        from selenium import webdriver
        from selenium.webdriver.chrome.options import Options
        from selenium.webdriver.common.by import By
        from selenium.webdriver.support.ui import WebDriverWait
        from selenium.webdriver.support import expected_conditions as EC
        
        options = Options()
        options.headless = True
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-gpu')
        
        driver = webdriver.Chrome(options=options)
        url = 'https://blog.csdn.net/QcloudCommunity/article/list'
        
        print(f"📄 正在访问: {url}")
        driver.get(url)
        
        # 等待页面加载
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.TAG_NAME, "body"))
        )
        
        soup = BeautifulSoup(driver.page_source, 'html.parser')
        driver.quit()
        
        # 查找文章
        articles = soup.find_all('div', class_='article-item-box')
        if not articles:
            # 尝试其他可能的选择器
            articles = soup.find_all('article') or soup.find_all('div', class_='article')
        
        print(f"📄 找到的文章数量: {len(articles)}")
        
        for article in articles:
            try:
                # 尝试多种标题选择器
                title_elem = (article.find('h4', class_='text-truncate') or 
                             article.find('h3') or 
                             article.find('h2') or 
                             article.find('a', class_='title'))
                
                if title_elem and '赛' in title_elem.get_text():
                    name = title_elem.get_text().strip()
                    
                    # 获取链接
                    link_elem = title_elem.find('a') if title_elem.name != 'a' else title_elem
                    if not link_elem:
                        continue
                        
                    link = link_elem.get('href', '')
                    if link and not link.startswith('http'):
                        link = f"https://blog.csdn.net{link}"
                    
                    # 获取介绍
                    intro_elem = article.find('p', class_='content') or article.find('div', class_='summary')
                    intro = intro_elem.get_text().strip() if intro_elem else 'Not found'
                    
                    # 获取详细信息
                    participants, prize, start_date, end_date = get_details(link)
                    
                    # 只处理有效的比赛数据（进行中或即将开始的比赛）
                    if (start_date is None or start_date <= datetime.datetime.now()) and (end_date is None or end_date >= datetime.datetime.now()):
                        print(f"✅ 收集比赛: {name}")
                        
                        # 立即插入到飞书表格，传递介绍信息用于AI分析
                        if insert_to_feishu(name, link, start_date, end_date, "", "", "", intro):
                            success_count += 1
                            print(f"📝 成功导入第 {success_count} 条数据")
                        else:
                            failed_count += 1
                            print(f"❌ 导入失败: {name}")
                        
                        # 每次插入后稍作延迟，避免频率限制
                        time.sleep(1)
                    else:
                        print(f"⏭️ 跳过过期比赛: {name}")
                        
            except Exception as e:
                print(f"⚠️ 处理文章时出错: {e}")
                continue
                
    except ImportError:
        print("❌ 缺少selenium依赖，请安装: pip install selenium")
        return
    except Exception as e:
        print(f"❌ 爬取腾讯博客时出错: {e}")
        return
    
    # 输出统计信息
    print(f"\n📊 腾讯CSDN博客爬取完成: 成功导入 {success_count} 条，失败 {failed_count} 条")

import datetime
def get_details(link):
    from selenium import webdriver
    from selenium.webdriver.common.by import By
    from selenium.webdriver.chrome.service import Service
    from webdriver_manager.chrome import ChromeDriverManager
    from selenium.webdriver.chrome.options import Options
    import time
    options = Options()
    options.headless = True
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)
    driver.get(link)
    time.sleep(2)  # 添加延迟确保页面加载
    page_text = driver.find_element(By.TAG_NAME, 'body').text
    print("完整页面文本:", page_text)
    participants = 'Not found'
    prize = 'Not found'
    start_date = None
    end_date = None
    participants_match = re.search(r"报名人数[:：]?\s*(\d+)", page_text)
    if participants_match:
        participants = participants_match.group(1)
    prize_match = re.search(r"(奖池|奖金)[:：]?\s*([\w\d¥,]+)", page_text)
    if prize_match:
        prize = prize_match.group(2)
    # Improved date regex to support more formats, including missing year and time
    date_pattern = r'(\d{4}[年.-/]?\d{1,2}[月.-/]?\d{1,2}[日]?(?:\s*\d{1,2}[点:]\d{2}(?::\d{2})?)?|即日起|\d{1,2}[月.-/]?\d{1,2}[日]?(?:\s*\d{1,2}[点:]\d{2}(?::\d{2})?)?)'
    all_dates = re.findall(date_pattern, page_text)
    print("页面中所有潜在日期字符串:", all_dates)
    start_date_match = re.search(r"(开始日期|起始日期|开始时间|比赛时间|活动时间|报名时间)[:：]?\s*" + date_pattern, page_text)
    if start_date_match:
        print("匹配到的开始日期字符串:", start_date_match.group(0))
        date_str = start_date_match.group(1).strip()
        if date_str == '即日起':
            start_date = datetime.datetime.now()
        else:
            date_str = date_str.replace('年', '-').replace('月', '-').replace('日', '').replace('.', '-').replace('/', '-').replace('点', ':')
            formats = ['%Y-%m-%d %H:%M:%S', '%Y-%m-%d %H:%M', '%Y-%m-%d', '%m-%d %H:%M:%S', '%m-%d %H:%M', '%m-%d']
            for fmt in formats:
                try:
                    if '%Y' not in fmt:
                        date_str = f"{datetime.datetime.now().year}-{date_str}"
                    start_date = datetime.datetime.strptime(date_str, fmt)
                    break
                except ValueError:
                    pass
    end_date_match = re.search(r"(结束日期|截止日期|截止时间|比赛时间|活动时间|报名时间)[:：]?\s*" + date_pattern, page_text)
    if end_date_match:
        print("匹配到的结束日期字符串:", end_date_match.group(0))
        date_str = end_date_match.group(1).strip()
        date_str = date_str.replace('年', '-').replace('月', '-').replace('日', '').replace('.', '-').replace('/', '-').replace('点', ':')
        formats = ['%Y-%m-%d %H:%M:%S', '%Y-%m-%d %H:%M', '%Y-%m-%d', '%m-%d %H:%M:%S', '%m-%d %H:%M', '%m-%d']
        for fmt in formats:
            try:
                if '%Y' not in fmt:
                    date_str = f"{datetime.datetime.now().year}-{date_str}"
                end_date = datetime.datetime.strptime(date_str, fmt)
                break
            except ValueError:
                pass
    # Handle range like '即日起-9月23日23点59分59秒'
    range_match = re.search(r"(开始日期|起始日期|比赛时间|活动时间|报名时间)[:：]?\s*(即日起|\d{4}[年.-/]?\d{1,2}[月.-/]?\d{1,2}[日]?)\s*(?:-|至|到)\s*(\d{4}[年.-/]?\d{1,2}[月.-/]?\d{1,2}[日]?(?:\s*\d{1,2}[点:]\d{2}(?::\d{2})?)?)", page_text)
    if range_match:
        print("匹配到的日期范围字符串:", range_match.group(0))
        start_str = range_match.group(2).strip()
        end_str = range_match.group(3).strip()
        if start_str == '即日起':
            start_date = datetime.datetime.now()
        else:
            start_str = start_str.replace('年', '-').replace('月', '-').replace('日', '').replace('.', '-').replace('/', '-')
            formats = ['%Y-%m-%d', '%m-%d']
            for fmt in formats:
                try:
                    if '%Y' not in fmt:
                        start_str = f"{datetime.datetime.now().year}-{start_str}"
                    start_date = datetime.datetime.strptime(start_str, fmt)
                    break
                except ValueError:
                    pass
        end_str = end_str.replace('年', '-').replace('月', '-').replace('日', '').replace('.', '-').replace('/', '-').replace('点', ':')
        formats = ['%Y-%m-%d %H:%M:%S', '%Y-%m-%d %H:%M', '%Y-%m-%d', '%m-%d %H:%M:%S', '%m-%d %H:%M', '%m-%d']
        for fmt in formats:
            try:
                if '%Y' not in fmt:
                    end_str = f"{datetime.datetime.now().year}-{end_str}"
                end_date = datetime.datetime.strptime(end_str, fmt)
                break
            except ValueError:
                pass
    return participants, prize, start_date, end_date

def print_summary_stats():
    """打印爬虫运行统计信息"""
    print("\n" + "="*60)
    print("🎯 比赛信息爬虫运行完成")
    print("="*60)
    print(f"⏰ 运行时间: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"🔗 飞书表格: https://feishu.cn/base/{app_token}")
    print(f"📊 表格ID: {table_id}")
    print("\n💡 提示:")
    print("  - 数据已自动去重，避免重复插入")
    print("  - 只收集当前有效的比赛信息")
    print("  - 现已改为逐个导入模式，每条数据收集后立即插入飞书表格")
    print("  - 如需查看详细日志，请检查控制台输出")
    print("="*60)

if __name__ == "__main__":
    start_time = datetime.datetime.now()
    print(f"🚀 比赛信息爬虫启动 - {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
    
    parser = argparse.ArgumentParser(
        description="比赛信息爬虫 - 自动爬取各平台比赛信息并插入飞书表格",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例用法:
  python crawler.py --platform baidu          # 只爬取百度AI Studio
  python crawler.py --platform all            # 爬取所有平台
  python crawler.py --platform wechat --biz <BIZ_ID> --token <TOKEN> --cookie <COOKIE>
        """
    )
    parser.add_argument("--platform", 
                       choices=['baidu', 'aliyun', 'wechat', 'tencent', 'all', 'update-status'], 
                       default='baidu', 
                       help="选择爬取平台: baidu(百度AI Studio), aliyun(阿里天池), wechat(微信公众号), tencent(腾讯CSDN), all(所有平台), update-status(更新比赛状态)")
    parser.add_argument("--biz", help="微信公众号 biz ID")
    parser.add_argument("--token", default="", help="微信公众号 token")
    parser.add_argument("--cookie", default="", help="微信公众号 cookie")
    parser.add_argument("--batch-size", type=int, default=10, help="批量插入大小 (默认: 10)")
    parser.add_argument("--max-retries", type=int, default=3, help="最大重试次数 (默认: 3)")
    
    args = parser.parse_args()
    
    try:
        if args.platform == 'baidu':
            crawl_baidu()
        elif args.platform == 'aliyun':
            crawl_aliyun()
        elif args.platform == 'wechat':
            if not args.biz:
                print("❌ 微信公众号爬取需要 --biz 参数")
                sys.exit(1)
            token = args.token or ""
            cookie = args.cookie or ""
            crawl_wechat(args.biz, token, cookie)
        elif args.platform == 'tencent':
            crawl_tencent()
        elif args.platform == 'update-status':
            print("\n" + "="*50)
            print("🔄 开始更新所有比赛状态")
            print("="*50)
            update_all_competition_status()
        elif args.platform == 'all':
            print("\n" + "="*50)
            print("🎯 开始全平台比赛信息爬取")
            print("="*50)
            
            print("\n=== 🔍 爬取百度AI Studio比赛信息 ===")
            crawl_baidu()
            
            print("\n=== 🔍 爬取阿里天池比赛信息 ===")
            crawl_aliyun()
            
            print("\n=== 🔍 爬取腾讯CSDN博客比赛信息 ===")
            crawl_tencent()
            
            if args.biz and args.token and args.cookie:
                print("\n=== 🔍 爬取微信公众号文章 ===")
                crawl_wechat(args.biz, args.token, args.cookie)
            else:
                print("\n⚠️ 跳过微信公众号: 缺少必要参数 (--biz, --token, --cookie)")
                
    except KeyboardInterrupt:
        print("\n❌ 用户中断程序")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ 程序运行出错: {e}")
        sys.exit(1)
    finally:
        end_time = datetime.datetime.now()
        duration = end_time - start_time
        print(f"\n⏱️ 总运行时间: {duration}")
        print_summary_stats()