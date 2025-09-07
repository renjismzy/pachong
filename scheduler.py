#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
定时任务调度器
每天早上9点自动爬取所有平台的比赛信息
"""

import schedule
import time
import datetime
import logging
import sys
import os
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# 导入爬虫模块
try:
    from crawlers.baidu_crawler import crawl_baidu
    from crawlers.aliyun_crawler import crawl_aliyun
    from crawlers.tencent_crawler import crawl_tencent
    from crawlers.wechat_crawler import crawl_wechat
    from feishu_api import update_all_competition_status
except ImportError as e:
    print(f"导入模块失败: {e}")
    sys.exit(1)

# 配置日志
def setup_logging():
    """配置日志系统"""
    log_dir = project_root / "logs"
    log_dir.mkdir(exist_ok=True)
    
    log_file = log_dir / f"scheduler_{datetime.datetime.now().strftime('%Y%m')}.log"
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file, encoding='utf-8'),
            logging.StreamHandler(sys.stdout)
        ]
    )
    return logging.getLogger(__name__)

logger = setup_logging()

def run_daily_crawl():
    """执行每日爬虫任务"""
    start_time = datetime.datetime.now()
    logger.info("="*60)
    logger.info(f"🚀 开始执行每日爬虫任务 - {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info("="*60)
    
    success_count = 0
    total_platforms = 4
    
    # 爬取百度AI Studio
    try:
        logger.info("📍 开始爬取百度AI Studio...")
        crawl_baidu()
        success_count += 1
        logger.info("✅ 百度AI Studio爬取完成")
    except Exception as e:
        logger.error(f"❌ 百度AI Studio爬取失败: {str(e)}")
    
    # 等待间隔，避免请求过于频繁
    time.sleep(5)
    
    # 爬取阿里天池
    try:
        logger.info("📍 开始爬取阿里天池...")
        crawl_aliyun()
        success_count += 1
        logger.info("✅ 阿里天池爬取完成")
    except Exception as e:
        logger.error(f"❌ 阿里天池爬取失败: {str(e)}")
    
    # 等待间隔
    time.sleep(5)
    
    # 爬取腾讯CSDN
    try:
        logger.info("📍 开始爬取腾讯CSDN...")
        crawl_tencent()
        success_count += 1
        logger.info("✅ 腾讯CSDN爬取完成")
    except Exception as e:
        logger.error(f"❌ 腾讯CSDN爬取失败: {str(e)}")
    
    # 等待间隔
    time.sleep(5)
    
    # 爬取微信公众号
    try:
        logger.info("📍 开始爬取微信公众号...")
        crawl_wechat()
        success_count += 1
        logger.info("✅ 微信公众号爬取完成")
    except Exception as e:
        logger.error(f"❌ 微信公众号爬取失败: {str(e)}")
    
    # 等待间隔
    time.sleep(5)
    
    # 更新比赛状态
    try:
        logger.info("📍 开始更新比赛状态...")
        update_all_competition_status()
        logger.info("✅ 比赛状态更新完成")
    except Exception as e:
        logger.error(f"❌ 比赛状态更新失败: {str(e)}")
    
    # 任务完成统计
    end_time = datetime.datetime.now()
    duration = end_time - start_time
    
    logger.info("="*60)
    logger.info(f"📊 任务执行完成 - {end_time.strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info(f"⏱️ 执行时长: {duration}")
    logger.info(f"📈 成功平台: {success_count}/{total_platforms}")
    if success_count == total_platforms:
        logger.info("🎉 所有平台爬取成功！")
    else:
        logger.warning(f"⚠️ 有 {total_platforms - success_count} 个平台爬取失败")
    logger.info("="*60)

def run_scheduler(frequency="daily", time_str="09:00", weekday=None):
    """运行定时调度器
    
    Args:
        frequency (str): 执行频率 - "daily", "weekly", "monthly"
        time_str (str): 执行时间，格式为 "HH:MM"
        weekday (str): 当frequency为"weekly"时指定星期几 (monday, tuesday, etc.)
    """
    logger.info("🕘 定时任务调度器启动")
    
    # 清除所有现有任务
    schedule.clear()
    
    # 根据频率设置定时任务
    if frequency == "daily":
        schedule.every().day.at(time_str).do(run_daily_crawl)
        logger.info(f"📅 计划任务: 每天 {time_str} 执行爬虫任务")
    elif frequency == "weekly":
        if weekday:
            getattr(schedule.every(), weekday.lower()).at(time_str).do(run_daily_crawl)
            logger.info(f"📅 计划任务: 每周{weekday} {time_str} 执行爬虫任务")
        else:
            schedule.every().monday.at(time_str).do(run_daily_crawl)
            logger.info(f"📅 计划任务: 每周一 {time_str} 执行爬虫任务")
    elif frequency == "monthly":
        # 每月1号执行
        def monthly_job():
            if datetime.datetime.now().day == 1:
                run_daily_crawl()
        
        schedule.every().day.at(time_str).do(monthly_job)
        logger.info(f"📅 计划任务: 每月1号 {time_str} 执行爬虫任务")
    else:
        logger.error(f"❌ 不支持的频率: {frequency}")
        return
    
    logger.info("⏰ 等待定时任务触发...")
    
    while True:
        try:
            schedule.run_pending()
            time.sleep(60)  # 每分钟检查一次
        except KeyboardInterrupt:
            logger.info("\n👋 收到中断信号，正在停止调度器...")
            break
        except Exception as e:
            logger.error(f"❌ 调度器运行出错: {str(e)}")
            time.sleep(60)

def run_once():
    """立即执行一次爬虫任务（用于测试）"""
    logger.info("🧪 立即执行爬虫任务（测试模式）")
    run_daily_crawl()

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="比赛信息爬虫定时调度器")
    parser.add_argument(
        "--mode", 
        choices=["schedule", "once"], 
        default="schedule",
        help="运行模式: schedule(定时调度) 或 once(立即执行)"
    )
    parser.add_argument(
        "--frequency",
        choices=["daily", "weekly", "monthly"],
        default="daily",
        help="定时频率: daily(每天), weekly(每周), monthly(每月)"
    )
    parser.add_argument(
        "--time",
        default="09:00",
        help="执行时间，格式为 HH:MM (默认: 09:00)"
    )
    parser.add_argument(
        "--weekday",
        choices=["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"],
        help="当frequency为weekly时指定星期几"
    )
    
    args = parser.parse_args()
    
    try:
        if args.mode == "once":
            run_once()
        else:
            run_scheduler(args.frequency, args.time, args.weekday)
    except Exception as e:
        logger.error(f"❌ 程序运行失败: {str(e)}")
        sys.exit(1)