#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
比赛信息爬虫Web管理界面
提供爬虫任务管理、定时调度、状态监控等功能
"""

import os
import json
import datetime
import threading
import subprocess
from pathlib import Path
from flask import Flask, render_template, request, jsonify, send_from_directory
from flask_cors import CORS
from flask_socketio import SocketIO, emit
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
import psutil

# 导入爬虫模块
try:
    from crawlers.baidu_crawler import crawl_baidu
    from crawlers.aliyun_crawler import crawl_aliyun
    from crawlers.tencent_crawler import crawl_tencent
    from crawlers.wechat_crawler import crawl_wechat
    from feishu_api import update_all_competition_status, get_all_records
except ImportError as e:
    print(f"导入爬虫模块失败: {e}")

# 初始化Flask应用
app = Flask(__name__)
app.config['SECRET_KEY'] = 'crawler_web_ui_secret_key'
CORS(app)
socketio = SocketIO(app, cors_allowed_origins="*")

# 初始化调度器
scheduler = BackgroundScheduler()
scheduler.start()

# 全局变量
task_status = {
    'baidu': {'status': 'idle', 'last_run': None, 'message': ''},
    'aliyun': {'status': 'idle', 'last_run': None, 'message': ''},
    'tencent': {'status': 'idle', 'last_run': None, 'message': ''},
    'wechat': {'status': 'idle', 'last_run': None, 'message': ''},
    'update_status': {'status': 'idle', 'last_run': None, 'message': ''}
}

running_tasks = {}
scheduled_jobs = {}

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

def filter_ongoing_competitions(competitions, current_date):
    """筛选未结束的比赛"""
    try:
        current_dt = datetime.datetime.strptime(current_date, '%Y-%m-%d')
        ongoing = []
        
        for comp in competitions:
            end_date_str = comp.get('end_date', '')
            if end_date_str:
                try:
                    # 尝试解析结束时间
                    if isinstance(end_date_str, str) and end_date_str.strip():
                        # 处理不同的日期格式
                        for fmt in ['%Y-%m-%d %H:%M:%S', '%Y-%m-%d', '%Y/%m/%d', '%m/%d/%Y']:
                            try:
                                end_dt = datetime.datetime.strptime(end_date_str.strip(), fmt)
                                if end_dt.date() >= current_dt.date():
                                    ongoing.append(comp)
                                break
                            except ValueError:
                                continue
                except:
                    # 如果无法解析日期，保留比赛
                    ongoing.append(comp)
            else:
                # 如果没有结束日期，保留比赛
                ongoing.append(comp)
        
        return ongoing
    except Exception as e:
        print(f"筛选比赛失败: {e}")
        return competitions

def run_crawler_task(platform, filter_date=None):
    """运行爬虫任务"""
    try:
        task_status[platform]['status'] = 'running'
        task_status[platform]['message'] = f'正在爬取{PLATFORM_NAMES[platform]}...'
        socketio.emit('task_status_update', task_status)
        
        # 执行爬虫函数
        if filter_date and platform != 'update_status':
            # 如果有筛选日期，需要修改爬虫函数支持日期筛选
            # 这里暂时还是调用原函数，后续会修改爬虫逻辑
            CRAWLER_FUNCTIONS[platform]()
        else:
            CRAWLER_FUNCTIONS[platform]()
        
        task_status[platform]['status'] = 'completed'
        task_status[platform]['last_run'] = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        task_status[platform]['message'] = f'{PLATFORM_NAMES[platform]}爬取完成'
        
        # 爬取完成后发送所有比赛数据
        competitions = get_all_competitions()
        socketio.emit('competitions_updated', competitions)
        
    except Exception as e:
        task_status[platform]['status'] = 'error'
        task_status[platform]['message'] = f'{PLATFORM_NAMES[platform]}爬取失败: {str(e)}'
    
    finally:
        if platform in running_tasks:
            del running_tasks[platform]
        socketio.emit('task_status_update', task_status)

@app.route('/')
def index():
    """主页面"""
    return render_template('index.html')

@app.route('/api/status')
def get_status():
    """获取所有任务状态"""
    return jsonify({
        'task_status': task_status,
        'scheduled_jobs': list(scheduled_jobs.keys()),
        'system_info': {
            'cpu_percent': psutil.cpu_percent(),
            'memory_percent': psutil.virtual_memory().percent,
            'disk_percent': psutil.disk_usage('/').percent if os.name != 'nt' else psutil.disk_usage('C:').percent
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

@app.route('/api/run/all', methods=['POST'])
def run_all_tasks():
    """运行所有爬虫任务"""
    if any(platform in running_tasks for platform in CRAWLER_FUNCTIONS.keys()):
        return jsonify({'success': False, 'message': '有任务正在运行中'}), 400
    
    def run_all():
        platforms = ['baidu', 'aliyun', 'tencent', 'wechat', 'update_status']
        for platform in platforms:
            if platform not in running_tasks:
                run_crawler_task(platform)
                # 等待间隔，避免请求过于频繁
                if platform != 'update_status':
                    import time
                    time.sleep(5)
    
    thread = threading.Thread(target=run_all)
    thread.daemon = True
    thread.start()
    
    return jsonify({'success': True, 'message': '开始执行全平台爬取任务'})

def run_all_crawlers():
    """供定时任务调用的全平台爬取函数"""
    platforms = ['baidu', 'aliyun', 'tencent', 'wechat', 'update_status']
    for platform in platforms:
        try:
            run_crawler_task(platform)
            # 等待间隔，避免请求过于频繁
            if platform != 'update_status':
                import time
                time.sleep(5)
        except Exception as e:
            print(f"定时任务执行{platform}失败: {e}")

@app.route('/api/schedule', methods=['POST'])
def add_schedule():
    """添加定时任务"""
    data = request.get_json()
    
    task_name = data.get('taskName')
    frequency = data.get('frequency')
    execute_time = data.get('executeTime')
    weekday = data.get('weekday')
    monthday = data.get('monthday')
    
    if not all([task_name, frequency, execute_time]):
        return jsonify({'success': False, 'message': '参数不完整'}), 400
    
    if frequency not in ['daily', 'weekly', 'monthly']:
        return jsonify({'success': False, 'message': '不支持的频率类型'}), 400
    
    try:
        # 解析执行时间
        time_parts = execute_time.split(':')
        if len(time_parts) != 2:
            return jsonify({'success': False, 'message': '时间格式错误，应为HH:MM'}), 400
        
        hour, minute = time_parts
        hour = int(hour)
        minute = int(minute)
        
        if not (0 <= hour <= 23 and 0 <= minute <= 59):
            return jsonify({'success': False, 'message': '时间范围错误'}), 400
        
        # 生成唯一的job_id
        job_id = f"{task_name}_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        # 根据频率设置触发器参数
        trigger_kwargs = {
            'hour': hour,
            'minute': minute
        }
        
        if frequency == 'weekly':
            if not weekday:
                return jsonify({'success': False, 'message': '周任务需要指定星期几'}), 400
            trigger_kwargs['day_of_week'] = int(weekday)
        elif frequency == 'monthly':
            if not monthday:
                return jsonify({'success': False, 'message': '月任务需要指定日期'}), 400
            trigger_kwargs['day'] = int(monthday)
        
        # 添加定时任务 - 默认运行所有爬虫
        scheduler.add_job(
            func=run_all_crawlers,
            trigger=CronTrigger(**trigger_kwargs),
            id=job_id,
            replace_existing=True
        )
        
        scheduled_jobs[job_id] = {
            'task_name': task_name,
            'frequency': frequency,
            'execute_time': execute_time,
            'weekday': weekday if frequency == 'weekly' else None,
            'monthday': monthday if frequency == 'monthly' else None,
            'created_at': datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        
        return jsonify({'success': True, 'message': f'定时任务 {task_name} 添加成功'})
        
    except Exception as e:
        return jsonify({'success': False, 'message': f'添加定时任务失败: {str(e)}'}), 500

@app.route('/api/schedule/<job_id>', methods=['DELETE'])
def remove_schedule(job_id):
    """删除定时任务"""
    try:
        scheduler.remove_job(job_id)
        if job_id in scheduled_jobs:
            del scheduled_jobs[job_id]
        return jsonify({'success': True, 'message': f'定时任务 {job_id} 删除成功'})
    except Exception as e:
        return jsonify({'success': False, 'message': f'删除定时任务失败: {str(e)}'}), 500

@app.route('/api/logs')
def get_logs():
    """获取日志文件列表"""
    logs_dir = Path('logs')
    if not logs_dir.exists():
        return jsonify({'logs': []})
    
    log_files = []
    for log_file in logs_dir.glob('*.log'):
        stat = log_file.stat()
        log_files.append({
            'name': log_file.name,
            'size': stat.st_size,
            'modified': datetime.datetime.fromtimestamp(stat.st_mtime).strftime('%Y-%m-%d %H:%M:%S')
        })
    
    return jsonify({'logs': sorted(log_files, key=lambda x: x['modified'], reverse=True)})

@app.route('/api/logs/<filename>')
def get_log_content(filename):
    """获取日志文件内容"""
    logs_dir = Path('logs')
    log_file = logs_dir / filename
    
    if not log_file.exists():
        return jsonify({'success': False, 'message': '日志文件不存在'}), 404
    
    try:
        with open(log_file, 'r', encoding='utf-8') as f:
            lines = f.readlines()
            # 只返回最后1000行
            content = ''.join(lines[-1000:])
        
        return jsonify({'success': True, 'content': content})
    except Exception as e:
        return jsonify({'success': False, 'message': f'读取日志文件失败: {str(e)}'}), 500

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
            'message': f'获取比赛数据失败: {str(e)}'
        }), 500

@app.route('/api/competitions/ongoing', methods=['POST'])
def get_ongoing_competitions():
    """获取未结束的比赛数据"""
    try:
        data = request.get_json()
        current_date = data.get('date', datetime.datetime.now().strftime('%Y-%m-%d'))
        
        all_competitions = get_all_competitions()
        ongoing_competitions = filter_ongoing_competitions(all_competitions, current_date)
        
        return jsonify({
            'success': True,
            'data': ongoing_competitions,
            'total': len(ongoing_competitions),
            'filter_date': current_date
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'获取未结束比赛数据失败: {str(e)}'
        }), 500

@app.route('/api/run/filtered', methods=['POST'])
def run_filtered_crawl():
    """运行筛选爬取任务"""
    try:
        data = request.get_json()
        platforms = data.get('platforms', [])
        filter_date = data.get('date')
        
        if not platforms:
            return jsonify({
                'success': False,
                'message': '请选择要爬取的平台'
            }), 400
        
        if not filter_date:
            return jsonify({
                'success': False,
                'message': '请提供筛选日期'
            }), 400
        
        # 启动爬取任务
        for platform in platforms:
            if platform in CRAWLER_FUNCTIONS and platform not in running_tasks:
                running_tasks[platform] = True
                thread = threading.Thread(target=run_crawler_task, args=(platform, filter_date))
                thread.daemon = True
                thread.start()
        
        return jsonify({
            'success': True,
            'message': f'已启动 {len(platforms)} 个平台的筛选爬取任务',
            'platforms': platforms,
            'filter_date': filter_date
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'启动筛选爬取失败: {str(e)}'
        }), 500

@socketio.on('connect')
def handle_connect():
    """WebSocket连接处理"""
    emit('task_status_update', task_status)

if __name__ == '__main__':
    # 创建templates目录
    templates_dir = Path('templates')
    templates_dir.mkdir(exist_ok=True)
    
    # 创建static目录
    static_dir = Path('static')
    static_dir.mkdir(exist_ok=True)
    
    print("🚀 爬虫Web管理界面启动")
    print("📱 访问地址: http://localhost:5000")
    
    socketio.run(app, host='0.0.0.0', port=5000, debug=True)