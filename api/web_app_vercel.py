#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
比赛信息爬虫Web管理界面 - Vercel版本
提供爬虫任务管理、状态监控等功能
"""

import os
import json
import datetime
import threading
from pathlib import Path
from flask import Flask, render_template, request, jsonify
from flask_cors import CORS

# 导入爬虫模块
try:
    import sys
    project_root = Path(__file__).parent.parent
    sys.path.insert(0, str(project_root))
    
    from crawlers.baidu_crawler import crawl_baidu
    from crawlers.aliyun_crawler import crawl_aliyun
    from crawlers.tencent_crawler import crawl_tencent
    from crawlers.wechat_crawler import crawl_wechat
    from feishu_api import update_all_competition_status, get_all_records
except ImportError as e:
    print(f"导入爬虫模块失败: {e}")
    # 为了防止部署失败，提供空函数
    def crawl_baidu(): pass
    def crawl_aliyun(): pass
    def crawl_tencent(): pass
    def crawl_wechat(): pass
    def update_all_competition_status(): pass
    def get_all_records(): return []

# 初始化Flask应用
try:
    # 尝试使用相对路径
    template_dir = Path(__file__).parent.parent / 'templates'
    static_dir = Path(__file__).parent.parent / 'static'
    
    if template_dir.exists() and static_dir.exists():
        app = Flask(__name__, template_folder=str(template_dir), static_folder=str(static_dir))
    else:
        # 如果路径不存在，使用默认配置
        app = Flask(__name__)
except Exception as e:
    print(f"Flask初始化警告: {e}")
    app = Flask(__name__)

app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'crawler_web_ui_secret_key')
CORS(app)

# 全局变量
task_status = {
    'baidu': {'status': 'idle', 'last_run': None, 'message': ''},
    'aliyun': {'status': 'idle', 'last_run': None, 'message': ''},
    'tencent': {'status': 'idle', 'last_run': None, 'message': ''},
    'wechat': {'status': 'idle', 'last_run': None, 'message': ''},
    'update_status': {'status': 'idle', 'last_run': None, 'message': ''}
}

running_tasks = {}

# 爬虫函数映射
CRAWLER_FUNCTIONS = {
    'baidu': crawl_baidu,
    'aliyun': crawl_aliyun,
    'tencent': crawl_tencent,
    'wechat': crawl_wechat,
    'update_status': update_all_competition_status
}

PLATFORM_NAMES = {
    'baidu': '百度AI Studio',
    'aliyun': '阿里天池',
    'tencent': '腾讯CSDN',
    'wechat': '微信公众号',
    'update_status': '状态更新'
}

def get_all_competitions():
    """获取所有比赛数据"""
    try:
        records = get_all_records()
        competitions = []
        
        for record in records:
            fields = record.get('fields', {})
            competition = {
                'id': record.get('record_id', ''),
                'name': fields.get('比赛名称', ''),
                'link': fields.get('比赛链接', {}).get('link', '') if isinstance(fields.get('比赛链接'), dict) else str(fields.get('比赛链接', '')),
                'status': fields.get('比赛状态', ''),
                'start_date': fields.get('比赛开始时间', ''),
                'end_date': fields.get('比赛结束时间', ''),
                'platform': fields.get('平台', ''),
                'difficulty': fields.get('难度等级', []),
                'type': fields.get('比赛类型', []),
                'prize': fields.get('奖金', ''),
                'participants': fields.get('参与人数', '')
            }
            competitions.append(competition)
        
        return competitions
    except Exception as e:
        print(f"获取比赛数据失败: {e}")
        return []

def run_crawler_task(platform, filter_date=None):
    """运行爬虫任务"""
    try:
        task_status[platform]['status'] = 'running'
        task_status[platform]['message'] = f'正在爬取{PLATFORM_NAMES[platform]}...'
        
        # 执行爬虫函数
        CRAWLER_FUNCTIONS[platform]()
        
        task_status[platform]['status'] = 'completed'
        task_status[platform]['last_run'] = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        task_status[platform]['message'] = f'{PLATFORM_NAMES[platform]}爬取完成'
        
    except Exception as e:
        task_status[platform]['status'] = 'error'
        task_status[platform]['message'] = f'{PLATFORM_NAMES[platform]}爬取失败: {str(e)}'
    
    finally:
        if platform in running_tasks:
            del running_tasks[platform]

@app.route('/')
def index():
    """主页面"""
    try:
        return render_template('index.html')
    except Exception as e:
        # 如果模板不存在，返回简单的HTML页面
        return f'''
        <!DOCTYPE html>
        <html>
        <head>
            <title>爬虫管理系统</title>
            <meta charset="utf-8">
        </head>
        <body>
            <h1>爬虫管理系统</h1>
            <p>系统正在运行中...</p>
            <p>API端点:</p>
            <ul>
                <li><a href="/api/status">/api/status</a> - 获取系统状态</li>
                <li><a href="/api/competitions">/api/competitions</a> - 获取比赛数据</li>
            </ul>
            <p>错误信息: {str(e)}</p>
        </body>
        </html>
        '''

@app.route('/health')
def health_check():
    """健康检查端点"""
    return {'status': 'ok', 'message': 'Service is running'}

@app.route('/api/status')
def get_status():
    """获取所有任务状态"""
    return jsonify({
        'task_status': task_status,
        'scheduled_jobs': [],  # Vercel不支持后台调度器
        'system_info': {
            'cpu_percent': 0,
            'memory_percent': 0,
            'disk_percent': 0
        }
    })

@app.route('/api/run/<platform>', methods=['POST'])
def run_task(platform):
    """手动运行爬虫任务"""
    if platform not in CRAWLER_FUNCTIONS:
        return jsonify({'success': False, 'message': '不支持的平台'}), 400
    
    if platform in running_tasks:
        return jsonify({'success': False, 'message': '任务正在运行中'}), 400
    
    # 在后台线程中运行任务
    thread = threading.Thread(target=run_crawler_task, args=(platform,))
    thread.daemon = True
    thread.start()
    
    running_tasks[platform] = thread
    
    return jsonify({'success': True, 'message': f'开始执行{PLATFORM_NAMES[platform]}爬取任务'})

@app.route('/api/competitions')
def get_competitions():
    """获取所有比赛数据"""
    try:
        competitions = get_all_competitions()
        return jsonify({
            'success': True,
            'data': competitions,
            'total': len(competitions)
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'获取比赛数据失败: {str(e)}',
            'data': [],
            'total': 0
        }), 500

# Vercel不支持定时任务，移除相关路由
@app.route('/api/schedule', methods=['POST'])
def add_schedule():
    """Vercel环境不支持定时任务"""
    return jsonify({'success': False, 'message': 'Vercel环境不支持后台定时任务'}), 400

@app.route('/api/logs')
def get_logs():
    """Vercel环境不支持日志查看"""
    return jsonify({'success': False, 'message': 'Vercel环境不支持日志文件访问'}), 400

# 导出app供Vercel使用
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)