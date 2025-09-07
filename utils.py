import re
import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.options import Options
import time
from config import FEISHU_APP_TOKEN

def clean_text(text):
    """清理文本，去除多余的空白字符和特殊字符"""
    if not text:
        return ""
    # 去除多余的空白字符
    text = re.sub(r'\s+', ' ', text.strip())
    # 去除特殊字符但保留中文、英文、数字和基本标点
    text = re.sub(r'[^\u4e00-\u9fa5a-zA-Z0-9\s.,!?()\[\]{}"\'-]', '', text)
    return text

def get_details(link):
    """从给定链接获取比赛详细信息"""
    options = Options()
    options.headless = True
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)
    
    try:
        driver.get(link)
        time.sleep(2)  # 添加延迟确保页面加载
        page_text = driver.find_element(By.TAG_NAME, 'body').text
        print("完整页面文本:", page_text)
        
        participants = 'Not found'
        prize = 'Not found'
        start_date = None
        end_date = None
        
        # 提取参与人数
        participants_match = re.search(r"报名人数[:：]?\s*(\d+)", page_text)
        if participants_match:
            participants = participants_match.group(1)
        
        # 提取奖金信息
        prize_match = re.search(r"(奖池|奖金)[:：]?\s*([\w\d¥,]+)", page_text)
        if prize_match:
            prize = prize_match.group(2)
        
        # 改进的日期正则表达式，支持更多格式
        date_pattern = (
            r'(\d{4}[年.-/]?\d{1,2}[月.-/]?\d{1,2}[日]?'
            r'(?:\s*\d{1,2}[点:]\d{2}(?::\d{2})?)?|'
            r'即日起|'
            r'\d{1,2}[月.-/]?\d{1,2}[日]?'
            r'(?:\s*\d{1,2}[点:]\d{2}(?::\d{2})?)?)'
        )
        all_dates = re.findall(date_pattern, page_text)
        print("页面中所有潜在日期字符串:", all_dates)
        
        # 提取开始日期
        start_date_match = re.search(r"(开始日期|起始日期|开始时间|比赛时间|活动时间|报名时间)[:：]?\s*" + date_pattern, page_text)
        if start_date_match:
            print("匹配到的开始日期字符串:", start_date_match.group(0))
            date_str = start_date_match.group(1).strip()
            if date_str == '即日起':
                start_date = datetime.datetime.now()
            else:
                start_date = parse_date_string(date_str)
        
        # 提取结束日期
        end_date_match = re.search(r"(结束日期|截止日期|截止时间|比赛时间|活动时间|报名时间)[:：]?\s*" + date_pattern, page_text)
        if end_date_match:
            print("匹配到的结束日期字符串:", end_date_match.group(0))
            date_str = end_date_match.group(1).strip()
            end_date = parse_date_string(date_str)
        
        # 处理日期范围，如 '即日起-9月23日23点59分59秒'
        range_match = re.search(r"(开始日期|起始日期|比赛时间|活动时间|报名时间)[:：]?\s*(即日起|\d{4}[年.-/]?\d{1,2}[月.-/]?\d{1,2}[日]?)\s*(?:-|至|到)\s*(\d{4}[年.-/]?\d{1,2}[月.-/]?\d{1,2}[日]?(?:\s*\d{1,2}[点:]\d{2}(?::\d{2})?)?)", page_text)
        if range_match:
            print("匹配到的日期范围字符串:", range_match.group(0))
            start_str = range_match.group(2).strip()
            end_str = range_match.group(3).strip()
            
            if start_str == '即日起':
                start_date = datetime.datetime.now()
            else:
                start_date = parse_date_string(start_str)
            
            end_date = parse_date_string(end_str)
        
        return participants, prize, start_date, end_date
    
    finally:
        driver.quit()

def parse_date_string(date_str):
    """解析日期字符串为datetime对象"""
    if not date_str:
        return None
    
    # 标准化日期字符串
    date_str = date_str.replace('年', '-').replace('月', '-').replace('日', '').replace('.', '-').replace('/', '-').replace('点', ':')
    
    # 尝试多种日期格式
    formats = [
        '%Y-%m-%d %H:%M:%S',
        '%Y-%m-%d %H:%M',
        '%Y-%m-%d',
        '%m-%d %H:%M:%S',
        '%m-%d %H:%M',
        '%m-%d'
    ]
    
    for fmt in formats:
        try:
            # 如果格式中没有年份，添加当前年份
            if '%Y' not in fmt:
                date_str = f"{datetime.datetime.now().year}-{date_str}"
            return datetime.datetime.strptime(date_str, fmt)
        except ValueError:
            continue
    
    return None

def print_summary_stats():
    """打印爬虫运行统计信息"""
    print("\n" + "="*60)
    print("🎯 比赛信息爬虫运行完成")
    print("="*60)
    print(f"⏰ 运行时间: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"🔗 飞书表格: https://feishu.cn/base/{FEISHU_APP_TOKEN}")
    print("\n💡 操作提示:")
    print("   • 可以在飞书表格中查看和编辑爬取的数据")
    print("   • 支持多种平台: baidu, aliyun, wechat, tencent")
    print("   • 使用 --platform 参数指定爬取平台")
    print("   • 使用 update-status 更新比赛状态")
    print("="*60)