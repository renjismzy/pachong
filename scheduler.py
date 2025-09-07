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

def run_scheduler():
    """运行定时调度器"""
    logger.info("🕘 定时任务调度器启动")
    logger.info("📅 计划任务: 每天早上9:00执行爬虫任务")
    
    # 设置定时任务：每天早上9点执行
    schedule.every().day.at("09:00").do(run_daily_crawl)
    
    # 可选：添加测试任务（每分钟执行一次，用于测试）
    # schedule.every().minute.do(run_daily_crawl)
    
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
    
    args = parser.parse_args()
    
    try:
        if args.mode == "once":
            run_once()
        else:
            run_scheduler()
    except Exception as e:
        logger.error(f"❌ 程序运行失败: {str(e)}")
        sys.exit(1)