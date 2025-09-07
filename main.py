#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
比赛信息爬虫主程序
支持多平台比赛信息爬取和状态更新
"""

import argparse
import datetime
import sys
from crawlers import crawl_baidu, crawl_aliyun, crawl_wechat, crawl_tencent
from feishu_api import update_all_competition_status
from utils import print_summary_stats

def main():
    """主函数"""
    start_time = datetime.datetime.now()
    print(f"🚀 比赛信息爬虫启动 - {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
    
    parser = argparse.ArgumentParser(
        description="比赛信息爬虫 - 自动爬取各平台比赛信息并插入飞书表格",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例用法:
  python main.py --platform baidu          # 只爬取百度AI Studio
  python main.py --platform all            # 爬取所有平台
  python main.py --platform wechat         # 爬取微信公众号
  python main.py --platform update-status  # 更新比赛状态
        """
    )
    
    parser.add_argument("--platform", 
                       choices=['baidu', 'aliyun', 'wechat', 'tencent', 'all', 'update-status'], 
                       default='baidu', 
                       help="选择爬取平台: baidu(百度AI Studio), aliyun(阿里天池), wechat(微信公众号), tencent(腾讯CSDN), all(所有平台), update-status(更新比赛状态)")
    
    parser.add_argument("--batch-size", type=int, default=10, help="批量插入大小 (默认: 10)")
    parser.add_argument("--max-retries", type=int, default=3, help="最大重试次数 (默认: 3)")
    
    args = parser.parse_args()
    
    try:
        if args.platform == 'baidu':
            print("\n=== 🔍 爬取百度AI Studio比赛信息 ===")
            crawl_baidu()
            
        elif args.platform == 'aliyun':
            print("\n=== 🔍 爬取阿里天池比赛信息 ===")
            crawl_aliyun()
            
        elif args.platform == 'wechat':
            print("\n=== 🔍 爬取微信公众号文章 ===")
            crawl_wechat()
            
        elif args.platform == 'tencent':
            print("\n=== 🔍 爬取腾讯CSDN博客比赛信息 ===")
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
            
            print("\n=== 🔍 爬取微信公众号文章 ===")
            crawl_wechat()
                
    except KeyboardInterrupt:
        print("\n❌ 用户中断程序")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ 程序运行出错: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        end_time = datetime.datetime.now()
        duration = end_time - start_time
        print(f"\n⏱️ 总运行时间: {duration}")
        print_summary_stats()

if __name__ == "__main__":
    main()