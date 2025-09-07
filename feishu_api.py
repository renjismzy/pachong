# -*- coding: utf-8 -*-
"""
飞书API模块 - 处理所有飞书相关的API操作
"""

import requests
import json
import time
import datetime
import io
import mimetypes
from urllib.parse import urlparse
from config import (
    FEISHU_APP_ID, FEISHU_APP_SECRET, FEISHU_APP_TOKEN, FEISHU_TABLE_ID,
    FEISHU_TOKEN_URL, FEISHU_RECORDS_URL, FEISHU_UPLOAD_IMAGE_URL, FEISHU_UPLOAD_FILE_URL,
    DEEPSEEK_API_KEY, REQUEST_CONFIG, FIELD_LIMITS, VALID_DIFFICULTY_LEVELS, 
    DEFAULT_DIFFICULTY_LEVEL, DEFAULT_COMPETITION_TYPE, COMPETITION_STATUS,
    BATCH_CONFIG, LOG_CONFIG
)
from utils import clean_text

def get_feishu_token():
    """获取飞书访问令牌
    
    Returns:
        str: 访问令牌，失败时返回None
    """
    # 检查配置是否存在
    if not FEISHU_APP_ID or not FEISHU_APP_SECRET:
        print(f"{LOG_CONFIG['error_emoji']} 飞书配置缺失！请检查.env文件中的FEISHU_APP_ID和FEISHU_APP_SECRET")
        print(f"{LOG_CONFIG['info_emoji']} 请访问 https://open.feishu.cn/app 创建应用并获取配置信息")
        return None
        
    payload = {"app_id": FEISHU_APP_ID, "app_secret": FEISHU_APP_SECRET}
    
    try:
        response = requests.post(FEISHU_TOKEN_URL, json=payload, timeout=REQUEST_CONFIG['timeout'])
        if response.status_code != 200:
            print(f"{LOG_CONFIG['error_emoji']} 获取飞书token失败: {response.status_code} - {response.text}")
            return None
        
        data = response.json()
        if data.get('code') != 0:
            print(f"{LOG_CONFIG['error_emoji']} 飞书API返回错误: {data.get('msg', '未知错误')}")
            return None
            
        return data["tenant_access_token"]
    except requests.exceptions.RequestException as e:
        print(f"{LOG_CONFIG['error_emoji']} 网络请求失败: {e}")
        return None
    except Exception as e:
        print(f"{LOG_CONFIG['error_emoji']} 解析响应失败: {e}")
        return None

def format_difficulty_level(level):
    """将难度等级转换为多选格式
    
    Args:
        level: 难度等级字符串
    
    Returns:
        list: 格式化后的难度等级列表
    """
    if not level:
        return [DEFAULT_DIFFICULTY_LEVEL]
    
    level_str = str(level).upper()
    # 尝试匹配已知的难度等级
    for valid_level in VALID_DIFFICULTY_LEVELS:
        if valid_level in level_str:
            return [valid_level]
    # 如果没有匹配到，默认返回L2
    return [DEFAULT_DIFFICULTY_LEVEL]

def format_competition_type(comp_type):
    """将比赛类型转换为多选格式
    
    Args:
        comp_type: 比赛类型字符串或列表
    
    Returns:
        list: 格式化后的比赛类型列表
    """
    if not comp_type:
        return [DEFAULT_COMPETITION_TYPE]
    
    if isinstance(comp_type, list):
        return comp_type if comp_type else [DEFAULT_COMPETITION_TYPE]
    
    # 如果是字符串，尝试解析
    comp_type_str = str(comp_type)
    if comp_type_str in ['wibe coding', 'MCP', 'AI智能体', 'AI视频', '其它']:
        return [comp_type_str]
    
    return [DEFAULT_COMPETITION_TYPE]

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
        return COMPETITION_STATUS['ENDED']
    
    # 如果有开始时间且还未开始，则为进行中（即将开始）
    # 如果正在进行中或时间不明确，默认为进行中
    return COMPETITION_STATUS['ONGOING']

def insert_to_feishu(name, link, start_date=None, end_date=None, cover_image="", 
                    difficulty_level="", competition_type="", description="", max_retries=None):
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
        max_retries: 最大重试次数
    
    Returns:
        bool: 插入是否成功
    """
    if max_retries is None:
        max_retries = REQUEST_CONFIG['max_retries']
    
    # 数据验证
    if not name or not link:
        print(f"错误：比赛名称或链接为空 - 名称: {name}, 链接: {link}")
        return False
    
    # 检查记录是否已存在
    exists, record_id = check_record_exists(name, link)
    if exists:
        # 如果记录已存在，检查并更新状态
        competition_status = determine_competition_status(start_date, end_date)
        if competition_status == COMPETITION_STATUS['ENDED']:
            if update_record_status(record_id, COMPETITION_STATUS['ENDED']):
                print(f"{LOG_CONFIG['success_emoji']} 已更新比赛状态为已结束: {name}")
            else:
                print(f"{LOG_CONFIG['error_emoji']} 更新比赛状态失败: {name}")
        print(f"{LOG_CONFIG['skip_emoji']} 跳过重复记录: {name}")
        return True
    
    # 使用DeepSeek AI分析比赛类型和难度等级（如果未提供或为空）
    if not difficulty_level or not competition_type:
        print(f"🤖 使用AI分析比赛: {name}")
        ai_types, ai_difficulty = analyze_competition_with_deepseek(name, description)
        
        # 如果原参数为空，使用AI分析结果
        if not competition_type:
            competition_type = ai_types[0] if ai_types else DEFAULT_COMPETITION_TYPE
        if not difficulty_level:
            difficulty_level = ai_difficulty[0] if ai_difficulty else DEFAULT_DIFFICULTY_LEVEL
    
    # 确定比赛状态
    competition_status = determine_competition_status(start_date, end_date)
    
    # 获取访问令牌
    token = get_feishu_token()
    if not token:
        print("错误：无法获取飞书访问令牌")
        return False
    
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    
    # 构建请求数据
    payload = {
        "fields": {
            "比赛名称": clean_text(name)[:FIELD_LIMITS['name_max_length']],
            "比赛链接": {
                "text": clean_text(name)[:FIELD_LIMITS['link_text_max_length']],
                "link": clean_text(link)[:FIELD_LIMITS['link_max_length']]
            },
            "比赛状态": competition_status,
            "难度等级": format_difficulty_level(difficulty_level),
            "比赛类型": format_competition_type(competition_type)
        }
    }
    
    # 如果有封面图片URL，上传到飞书并获取file_token
    if cover_image and cover_image.strip():
        print(f"{LOG_CONFIG['processing_emoji']} 正在上传比赛封面: {name}")
        file_token = upload_cover_image_from_url(cover_image)
        if file_token:
            payload["fields"]["比赛封面"] = [{
                "file_token": file_token,
                "name": "比赛封面",
                "url": clean_text(cover_image)[:FIELD_LIMITS['cover_image_max_length']]
            }]
            print(f"{LOG_CONFIG['success_emoji']} 封面上传成功: {name}")
        else:
            print(f"{LOG_CONFIG['warning_emoji']} 封面上传失败，将跳过封面字段: {name}")
            # 上传失败时不添加封面字段，避免插入错误
    
    # 重试机制
    for attempt in range(max_retries):
        try:
            response = requests.post(FEISHU_RECORDS_URL, headers=headers, json=payload, 
                                   timeout=REQUEST_CONFIG['timeout'])
            
            if response.status_code == 200:
                result = response.json()
                if result.get('code') == 0:
                    print(f"{LOG_CONFIG['success_emoji']} 成功插入数据: {name}")
                    return True
                else:
                    print(f"{LOG_CONFIG['error_emoji']} 飞书API返回错误: {result.get('msg', '未知错误')}")
                    print(f"详细错误信息: {result}")
            elif response.status_code == 401:
                print(f"{LOG_CONFIG['error_emoji']} 认证失败，请检查飞书应用配置")
                return False
            elif response.status_code == 429:
                wait_time = 2 ** attempt
                print(f"{LOG_CONFIG['warning_emoji']} 请求频率限制，等待 {wait_time} 秒后重试...")
                time.sleep(wait_time)
                continue
            else:
                print(f"{LOG_CONFIG['error_emoji']} HTTP错误 {response.status_code}: {response.text}")
                
        except requests.exceptions.RequestException as e:
            print(f"{LOG_CONFIG['error_emoji']} 网络请求失败 (尝试 {attempt + 1}/{max_retries}): {e}")
            if attempt < max_retries - 1:
                time.sleep(REQUEST_CONFIG['retry_delay'])
        except Exception as e:
            print(f"{LOG_CONFIG['error_emoji']} 插入数据时出错: {e}")
            break
    
    return False

def get_all_records():
    """获取表格中的所有记录
    
    Returns:
        list: 所有记录的列表，每个记录包含record_id和fields
    """
    token = get_feishu_token()
    if not token:
        return []
    
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    
    all_records = []
    page_token = None
    
    try:
        while True:
            params = {"page_size": BATCH_CONFIG['records_per_page']}
            if page_token:
                params["page_token"] = page_token
            
            response = requests.get(FEISHU_RECORDS_URL, headers=headers, params=params, 
                                  timeout=REQUEST_CONFIG['timeout'])
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
                    print(f"{LOG_CONFIG['error_emoji']} 获取记录失败: {result.get('msg', '未知错误')}")
                    break
            else:
                print(f"{LOG_CONFIG['error_emoji']} HTTP错误 {response.status_code}: {response.text}")
                break
                
    except Exception as e:
        print(f"{LOG_CONFIG['warning_emoji']} 获取所有记录时出错: {e}")
    
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
    
    url = f"https://open.feishu.cn/open-apis/bitable/v1/apps/{FEISHU_APP_TOKEN}/tables/{FEISHU_TABLE_ID}/records/search"
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
        response = requests.post(url, headers=headers, json=payload, timeout=REQUEST_CONFIG['timeout'])
        if response.status_code == 200:
            result = response.json()
            if result.get('code') == 0:
                records = result.get('data', {}).get('items', [])
                if len(records) > 0:
                    return True, records[0].get('record_id')
                return False, None
    except Exception as e:
        print(f"{LOG_CONFIG['warning_emoji']} 检查记录存在性时出错: {e}")
    
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
    
    url = f"https://open.feishu.cn/open-apis/bitable/v1/apps/{FEISHU_APP_TOKEN}/tables/{FEISHU_TABLE_ID}/records/{record_id}"
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    
    payload = {
        "fields": {
            "比赛状态": status
        }
    }
    
    try:
        response = requests.put(url, headers=headers, json=payload, timeout=REQUEST_CONFIG['timeout'])
        if response.status_code == 200:
            result = response.json()
            if result.get('code') == 0:
                return True
            else:
                print(f"{LOG_CONFIG['error_emoji']} 更新记录状态失败: {result.get('msg', '未知错误')}")
        else:
            print(f"{LOG_CONFIG['error_emoji']} HTTP错误 {response.status_code}: {response.text}")
    except Exception as e:
        print(f"{LOG_CONFIG['warning_emoji']} 更新记录状态时出错: {e}")
    
    return False

def update_all_competition_status():
    """更新所有比赛的状态，将已结束的比赛标记为已结束
    
    Returns:
        tuple: (更新成功数量, 更新失败数量)
    """
    print(f"{LOG_CONFIG['update_emoji']} 开始更新所有比赛状态...")
    
    # 获取所有记录
    all_records = get_all_records()
    if not all_records:
        print(f"{LOG_CONFIG['error_emoji']} 无法获取表格记录")
        return 0, 0
    
    success_count = 0
    failed_count = 0
    
    # 需要导入get_details函数来获取比赛详情
    from utils import get_details
    
    for record in all_records:
        try:
            record_id = record.get('record_id')
            fields = record.get('fields', {})
            
            # 获取比赛名称用于日志
            name = fields.get('比赛名称', 'Unknown')
            
            # 获取当前状态
            current_status = fields.get('比赛状态', COMPETITION_STATUS['ONGOING'])
            
            # 如果已经是已结束状态，跳过
            if current_status == COMPETITION_STATUS['ENDED']:
                continue
            
            # 从比赛链接获取详细信息来判断是否已结束
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
                if new_status == COMPETITION_STATUS['ENDED'] and current_status != COMPETITION_STATUS['ENDED']:
                    if update_record_status(record_id, COMPETITION_STATUS['ENDED']):
                        print(f"{LOG_CONFIG['success_emoji']} 已更新比赛状态: {name} -> 已结束")
                        success_count += 1
                    else:
                        print(f"{LOG_CONFIG['error_emoji']} 更新失败: {name}")
                        failed_count += 1
                    
                    # 添加延迟避免频率限制
                    time.sleep(REQUEST_CONFIG['rate_limit_delay'])
            
        except Exception as e:
            print(f"{LOG_CONFIG['warning_emoji']} 处理记录时出错: {e}")
            failed_count += 1
    
    print(f"📊 状态更新完成: 成功 {success_count} 条，失败 {failed_count} 条")
    return success_count, failed_count

def analyze_competition_with_deepseek(name, description=""):
    """使用DeepSeek AI分析比赛类型和难度等级
    
    Args:
        name: 比赛名称
        description: 比赛描述
    
    Returns:
        tuple: (比赛类型列表, 难度等级列表)
    """
    if not DEEPSEEK_API_KEY:
        print(f"{LOG_CONFIG['warning_emoji']} DeepSeek API密钥未配置，使用默认分类")
        return [DEFAULT_COMPETITION_TYPE], [DEFAULT_DIFFICULTY_LEVEL]
    
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
            'Authorization': f'Bearer {DEEPSEEK_API_KEY}',
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
            timeout=REQUEST_CONFIG['timeout']
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
                comp_types = analysis.get('competition_types', [DEFAULT_COMPETITION_TYPE])
                difficulty = analysis.get('difficulty_level', DEFAULT_DIFFICULTY_LEVEL)
                
                print(f"🤖 AI分析结果: 类型={comp_types}, 难度={difficulty}")
                return comp_types, [difficulty]
            except json.JSONDecodeError:
                print(f"{LOG_CONFIG['warning_emoji']} AI响应解析失败: {content}")
                return [DEFAULT_COMPETITION_TYPE], [DEFAULT_DIFFICULTY_LEVEL]
        else:
            print(f"{LOG_CONFIG['error_emoji']} DeepSeek API调用失败: {response.status_code}")
            return [DEFAULT_COMPETITION_TYPE], [DEFAULT_DIFFICULTY_LEVEL]
            
    except Exception as e:
        print(f"{LOG_CONFIG['error_emoji']} DeepSeek分析出错: {str(e)}")
        return [DEFAULT_COMPETITION_TYPE], [DEFAULT_DIFFICULTY_LEVEL]

def batch_insert_to_feishu(records_data, batch_size=None):
    """批量插入数据到飞书表格
    
    Args:
        records_data: 记录数据列表，每条记录包含(name, link, competition_time, cover_image, difficulty_level, competition_type)
        batch_size: 批量大小
    
    Returns:
        tuple: (成功数量, 失败数量)
    """
    if batch_size is None:
        batch_size = BATCH_CONFIG['default_batch_size']
    
    # 首先检查飞书配置
    if not FEISHU_APP_ID or not FEISHU_APP_SECRET:
        print(f"{LOG_CONFIG['error_emoji']} 无法插入数据：飞书配置缺失")
        print(f"{LOG_CONFIG['info_emoji']} 请在.env文件中配置FEISHU_APP_ID和FEISHU_APP_SECRET")
        print("📝 数据已收集完成，配置好飞书后可重新运行程序插入数据")
        return 0, len(records_data)
    
    success_count = 0
    failed_count = 0
    
    # 测试飞书连接
    test_token = get_feishu_token()
    if not test_token:
        print(f"{LOG_CONFIG['error_emoji']} 无法连接到飞书，跳过数据插入")
        return 0, len(records_data)
    
    print(f"{LOG_CONFIG['success_emoji']} 飞书连接正常，开始批量插入 {len(records_data)} 条数据...")
    
    for i in range(0, len(records_data), batch_size):
        batch = records_data[i:i + batch_size]
        print(f"\n{LOG_CONFIG['processing_emoji']} 处理批次 {i//batch_size + 1}: {len(batch)} 条记录")
        
        for record in batch:
            name, link, competition_time, cover_image, difficulty_level, competition_type = record
            
            # 插入记录
            if insert_to_feishu(name, link, None, None, cover_image, difficulty_level, competition_type):
                success_count += 1
            else:
                failed_count += 1
            
            # 批次间延迟，避免频率限制
            time.sleep(REQUEST_CONFIG['retry_delay'])
        
        # 批次间稍长延迟
        if i + batch_size < len(records_data):
            time.sleep(REQUEST_CONFIG['page_delay'])
    
    print(f"\n📊 批量插入完成: 成功 {success_count} 条，失败 {failed_count} 条")
    return success_count, failed_count

def print_summary_stats():
    """打印爬虫运行统计信息"""
    print("\n" + "="*60)
    print("🎯 比赛信息爬虫运行完成")
    print("="*60)
    print(f"⏰ 运行时间: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"🔗 飞书表格: https://feishu.cn/base/{FEISHU_APP_TOKEN}")
    print(f"📊 表格ID: {FEISHU_TABLE_ID}")
    print("\n💡 提示:")
    print("  - 数据已自动去重，避免重复插入")
    print("  - 只收集当前有效的比赛信息")
    print("  - 现已改为逐个导入模式，每条数据收集后立即插入飞书表格")
    print("  - 如需查看详细日志，请检查控制台输出")
    print("="*60)

def download_image_from_url(image_url, max_size_mb=10):
    """从URL下载图片
    
    Args:
        image_url: 图片URL
        max_size_mb: 最大文件大小（MB）
    
    Returns:
        tuple: (图片数据, 文件名, 内容类型) 或 (None, None, None)
    """
    try:
        # 解析URL获取文件名
        parsed_url = urlparse(image_url)
        filename = parsed_url.path.split('/')[-1]
        if not filename or '.' not in filename:
            filename = 'cover_image.jpg'
        
        # 下载图片
        headers = {'User-Agent': REQUEST_CONFIG['user_agent']}
        response = requests.get(image_url, headers=headers, timeout=REQUEST_CONFIG['timeout'], stream=True)
        response.raise_for_status()
        
        # 检查文件大小
        content_length = response.headers.get('content-length')
        if content_length and int(content_length) > max_size_mb * 1024 * 1024:
            print(f"{LOG_CONFIG['warning_emoji']} 图片文件过大: {int(content_length) / 1024 / 1024:.1f}MB > {max_size_mb}MB")
            return None, None, None
        
        # 读取图片数据
        image_data = io.BytesIO()
        total_size = 0
        for chunk in response.iter_content(chunk_size=8192):
            total_size += len(chunk)
            if total_size > max_size_mb * 1024 * 1024:
                print(f"{LOG_CONFIG['warning_emoji']} 图片文件过大: {total_size / 1024 / 1024:.1f}MB > {max_size_mb}MB")
                return None, None, None
            image_data.write(chunk)
        
        image_data.seek(0)
        
        # 获取内容类型
        content_type = response.headers.get('content-type')
        if not content_type:
            content_type, _ = mimetypes.guess_type(filename)
            if not content_type:
                content_type = 'image/jpeg'
        
        print(f"{LOG_CONFIG['success_emoji']} 成功下载图片: {filename} ({total_size / 1024:.1f}KB)")
        return image_data.getvalue(), filename, content_type
        
    except requests.exceptions.RequestException as e:
        print(f"{LOG_CONFIG['error_emoji']} 下载图片失败: {e}")
        return None, None, None
    except Exception as e:
        print(f"{LOG_CONFIG['error_emoji']} 处理图片时出错: {e}")
        return None, None, None

def upload_image_to_feishu(image_data, filename, content_type):
    """上传图片到飞书并获取file_token
    
    Args:
        image_data: 图片二进制数据
        filename: 文件名
        content_type: 内容类型
    
    Returns:
        str: file_token，失败时返回None
    """
    # 获取访问令牌
    token = get_feishu_token()
    if not token:
        print(f"{LOG_CONFIG['error_emoji']} 无法获取飞书访问令牌")
        return None
    
    try:
        # 准备上传数据
        files = {
            'image': (filename, image_data, content_type)
        }
        data = {
            'image_type': 'message'
        }
        headers = {
            'Authorization': f'Bearer {token}'
        }
        
        # 上传图片
        response = requests.post(FEISHU_UPLOAD_IMAGE_URL, headers=headers, files=files, data=data, timeout=REQUEST_CONFIG['timeout'])
        response.raise_for_status()
        
        result = response.json()
        if result.get('code') == 0:
            image_key = result.get('data', {}).get('image_key')
            if image_key:
                print(f"{LOG_CONFIG['success_emoji']} 成功上传图片到飞书: {filename}")
                return image_key
            else:
                print(f"{LOG_CONFIG['error_emoji']} 飞书返回数据中缺少image_key")
                return None
        else:
            print(f"{LOG_CONFIG['error_emoji']} 飞书API返回错误: {result.get('msg', '未知错误')}")
            return None
            
    except requests.exceptions.RequestException as e:
        print(f"{LOG_CONFIG['error_emoji']} 上传图片到飞书失败: {e}")
        return None
    except Exception as e:
        print(f"{LOG_CONFIG['error_emoji']} 处理上传请求时出错: {e}")
        return None

def upload_file_to_feishu(file_data, filename, content_type):
    """上传文件到飞书云盘并获取file_token
    
    Args:
        file_data: 文件二进制数据
        filename: 文件名
        content_type: 内容类型
    
    Returns:
        str: file_token，失败时返回None
    """
    # 获取访问令牌
    token = get_feishu_token()
    if not token:
        print(f"{LOG_CONFIG['error_emoji']} 无法获取飞书访问令牌")
        return None
    
    try:
        # 准备上传数据
        files = {
            'file': (filename, file_data, content_type)
        }
        data = {
            'file_name': filename,
            'parent_type': 'bitable_image',
            'parent_node': FEISHU_APP_TOKEN,
            'size': str(len(file_data))
        }
        headers = {
            'Authorization': f'Bearer {token}'
        }
        
        # 上传文件
        response = requests.post(FEISHU_UPLOAD_FILE_URL, headers=headers, files=files, data=data, timeout=REQUEST_CONFIG['timeout'])
        response.raise_for_status()
        
        result = response.json()
        if result.get('code') == 0:
            file_token = result.get('data', {}).get('file_token')
            if file_token:
                print(f"{LOG_CONFIG['success_emoji']} 成功上传文件到飞书云盘: {filename}")
                return file_token
            else:
                print(f"{LOG_CONFIG['error_emoji']} 飞书返回数据中缺少file_token")
                return None
        else:
            print(f"{LOG_CONFIG['error_emoji']} 飞书API返回错误: {result.get('msg', '未知错误')}")
            return None
            
    except requests.exceptions.RequestException as e:
        print(f"{LOG_CONFIG['error_emoji']} 上传文件到飞书失败: {e}")
        return None
    except Exception as e:
        print(f"{LOG_CONFIG['error_emoji']} 处理上传请求时出错: {e}")
        return None

def upload_cover_image_from_url(image_url):
    """从URL上传比赛封面图片到飞书
    
    Args:
        image_url: 图片URL
    
    Returns:
        str: file_token，失败时返回None
    """
    if not image_url or not image_url.strip():
        return None
    
    print(f"{LOG_CONFIG['processing_emoji']} 正在处理封面图片: {image_url}")
    
    # 下载图片
    image_data, filename, content_type = download_image_from_url(image_url)
    if not image_data:
        return None
    
    # 上传到飞书云盘（用于多维表格附件）
    file_token = upload_file_to_feishu(image_data, filename, content_type)
    return file_token