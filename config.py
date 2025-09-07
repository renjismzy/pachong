# -*- coding: utf-8 -*-
"""
配置文件 - 存放所有应用配置信息
"""

import os
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

# 飞书配置
FEISHU_APP_ID = os.getenv('FEISHU_APP_ID')
FEISHU_APP_SECRET = os.getenv('FEISHU_APP_SECRET')
FEISHU_APP_TOKEN = 'XgmKbtiiUa8mLhsHDsQcNQKBnVg'
FEISHU_TABLE_ID = 'tblgA8hErJNkgZGm'

# DeepSeek AI配置
DEEPSEEK_API_KEY = os.getenv('DEEPSEEK_API_KEY')

# 飞书API URLs
FEISHU_TOKEN_URL = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal/"
FEISHU_RECORDS_URL = f"https://open.feishu.cn/open-apis/bitable/v1/apps/{FEISHU_APP_TOKEN}/tables/{FEISHU_TABLE_ID}/records"
FEISHU_BASE_URL = f"https://feishu.cn/base/{FEISHU_APP_TOKEN}"
FEISHU_UPLOAD_IMAGE_URL = "https://open.feishu.cn/open-apis/im/v1/images"
FEISHU_UPLOAD_FILE_URL = "https://open.feishu.cn/open-apis/drive/v1/medias/upload_all"

# 爬虫配置
CRAWLER_CONFIG = {
    'baidu': {
        'base_url': 'https://aistudio.baidu.com/studio/match/search?pageSize=10&matchType=0&matchStatus=1&keyword=&orderBy=0',
        'detail_url_template': 'https://aistudio.baidu.com/studio/match/detail/{}'
    },
    'aliyun': {
        'base_url': 'https://tianchi.aliyun.com/v3/proxy/competition/api/race/page?visualTab=&raceName=&isActive=',
        'headers': {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3'
        }
    },
    'tencent': {
        'base_url': 'https://blog.csdn.net/QcloudCommunity/article/list'
    },
    'wechat': {
        'cookie': 'eas_sid=71J71522R3C0l7U4H6t8H3o7N1; pgv_pvid=9076977620; fqm_pvqid=6bb4cd3e-64a1-4529-8367-4217583cc204; yyb_muid=0AE4C70849E8675C0B31D12248E96696; ua_id=5BeKo7IQVO1T5BaJAAAAAIkX3r1FtBxdrNHZue3Okdc=; wxuin=55224558893414; mm_lang=zh_CN; pac_uid=0_ayJ80MYSxCm8H; omgid=0_ayJ80MYSxCm8H; _qimei_uuid42=1981a1325071003caeea7654a13ca032734a3b747c; _qimei_fingerprint=e41e25a8ca3ac1cbe408485703dfc3c9; _qimei_q32=60055ceb6566fe81cd3d551e1ab4b5a9; _qimei_h38=8f956f0faeea7654a13ca03202000009a1981a; _qimei_q36=08025af0dd99f88c30c56a8f30001d018810; _clck=3964405222|1|fyu|0; uuid=0325d33916d08ad5f1912836b4ec03fc; rand_info=CAESIPm0EJkPO7FY6sDPmrzPwlRQm46JoGNBoNYIvb8VC6vz; slave_bizuin=3964405222; data_bizuin=3964405222; bizuin=3964405222; data_ticket=1DmnJqsx5VA1hgGRruWjWrhUG7vCx4tTO6V/VCMtM1tBZy7kBLiiZRhUO9hLUskX; slave_sid=STNxUG9LaENoeEdtYXQ3d2d6RlF3a0RNS0NPS09mc3NtaEticjhWeEoyR0VTSFh2M1NIcnUwNHd3clpPck9nOTd2dU1vR2VFdGI3Y3pDbm1wUWdJSTV4am51U0p2RUtVemtrRW5NVkk1ajBvRmw1QlJ2Z21naWdnQng5TlhFRFl3bEk1amZWdjlyaVZpR3hn; slave_user=gh_90157a032df9; xid=c127dc93ac2e661d38d8a7811a9e690f; cert=PilrngRthSgqUlsJxGwEnAdhVndy83zL; _clsk=17zfhga|1756372450675|7|1|mp.weixin.qq.com/weheat-agent/payload/record',
        'token': '1029959952',
        'fakeid': 'Mzk0MzY0MTMwNA=='
    }
}

# 请求配置
REQUEST_CONFIG = {
    'timeout': 30,
    'max_retries': 3,
    'retry_delay': 1,  # 秒
    'page_delay': 2,   # 页面间延迟
    'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'rate_limit_delay': 0.5  # 状态更新时的延迟
}

# Selenium配置
SELENIUM_CONFIG = {
    'headless': True,
    'options': [
        '--no-sandbox',
        '--disable-dev-shm-usage',
        '--disable-gpu'
    ],
    'wait_timeout': 10
}

# 数据字段配置
FIELD_LIMITS = {
    'name_max_length': 500,
    'link_max_length': 500,
    'link_text_max_length': 100,
    'cover_image_max_length': 500
}

# 有效的难度等级和比赛类型
# 难度等级说明：
# L1: 刚接触电脑，适合完全没有编程基础的初学者
# L2: 会用电脑，有基本的计算机操作能力
# L3: 对电脑比较熟练，有一定的编程和开发经验
# L4: 对电脑很熟悉，专业开发者或高级技术人员
VALID_DIFFICULTY_LEVELS = ['L1', 'L2', 'L3', 'L4']
DEFAULT_DIFFICULTY_LEVEL = 'L2'
DEFAULT_COMPETITION_TYPE = '其它'

# 比赛状态
COMPETITION_STATUS = {
    'ONGOING': '进行中',
    'ENDED': '已结束'
}

# 日期解析配置
DATE_FORMATS = [
    '%Y年%m月%d日 %H:%M',
    '%Y年%m月%d日',
    '%Y-%m-%d %H:%M:%S',
    '%Y-%m-%d %H:%M',
    '%Y-%m-%d',
    '%Y/%m/%d %H:%M:%S',
    '%Y/%m/%d %H:%M',
    '%Y/%m/%d',
    '%m月%d日 %H:%M',
    '%m月%d日',
    '%m-%d %H:%M',
    '%m-%d',
    '%m/%d %H:%M',
    '%m/%d'
]

# 日期正则表达式模式
DATE_PATTERNS = {
    'start_date': r'(开始时间|报名时间|开赛时间|比赛开始)[:：]?\s*([^\n\r，,。.]+)',
    'end_date': r'(结束时间|截止时间|比赛结束|报名截止)[:：]?\s*([^\n\r，,。.]+)',
    'general_date': r'(\d{4}[年.-/]?\d{1,2}[月.-/]?\d{1,2}[日]?(?:\s*\d{1,2}[点:]\d{2}(?::\d{2})?)?|即日起|\d{1,2}[月.-/]?\d{1,2}[日]?(?:\s*\d{1,2}[点:]\d{2}(?::\d{2})?)?)',
    'immediate_start': r'即日起'
}

# 批量处理配置
BATCH_CONFIG = {
    'default_batch_size': 10,
    'records_per_page': 500  # 飞书API每页记录数
}

# 日志配置
LOG_CONFIG = {
    'start_emoji': '🚀',
    'success_emoji': '✅',
    'error_emoji': '❌',
    'warning_emoji': '⚠️',
    'info_emoji': '💡',
    'processing_emoji': '📦',
    'skip_emoji': '⏭️',
    'update_emoji': '🔄',
    'page_emoji': '📄',
    'stats_emoji': '📊'
}