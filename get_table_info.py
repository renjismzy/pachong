#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
获取飞书表格信息脚本
用于查看表格中已有的比赛信息，避免重复添加
"""

import argparse
from feishu_api import get_all_records, get_feishu_token
from config import FEISHU_APP_TOKEN, FEISHU_TABLE_ID
import json
from datetime import datetime

def get_table_info(show_details=False, filter_platform=None, export_json=False):
    """
    获取飞书表格中的所有比赛信息
    
    Args:
        show_details: 是否显示详细信息
        filter_platform: 过滤特定平台
        export_json: 是否导出为JSON文件
    """
    print("🔍 正在获取飞书表格信息...")
    
    # 获取飞书访问令牌
    token = get_feishu_token()
    if not token:
        print("❌ 无法获取飞书访问令牌")
        return
    
    # 获取所有记录
    records = get_all_records()
    if not records:
        print("❌ 无法获取表格记录")
        return
    
    print(f"📊 表格中共有 {len(records)} 条记录")
    
    # 统计信息
    platform_stats = {}
    status_stats = {}
    unique_titles = set()
    duplicate_titles = []
    
    filtered_records = []
    
    for record in records:
        fields = record.get('fields', {})
        title = fields.get('标题', '未知标题')
        platform = fields.get('平台', '未知平台')
        status = fields.get('状态', '未知状态')
        
        # 平台过滤
        if filter_platform and platform != filter_platform:
            continue
            
        filtered_records.append(record)
        
        # 统计平台分布
        platform_stats[platform] = platform_stats.get(platform, 0) + 1
        
        # 统计状态分布
        status_stats[status] = status_stats.get(status, 0) + 1
        
        # 检查重复标题
        if title in unique_titles:
            duplicate_titles.append(title)
        else:
            unique_titles.add(title)
    
    print("\n📈 统计信息:")
    print(f"   总记录数: {len(filtered_records)}")
    print(f"   唯一标题数: {len(unique_titles)}")
    print(f"   重复标题数: {len(duplicate_titles)}")
    
    print("\n🏢 平台分布:")
    for platform, count in sorted(platform_stats.items()):
        print(f"   {platform}: {count} 条")
    
    print("\n📊 状态分布:")
    for status, count in sorted(status_stats.items()):
        print(f"   {status}: {count} 条")
    
    if duplicate_titles:
        print("\n⚠️ 发现重复标题:")
        for title in set(duplicate_titles):
            print(f"   - {title}")
    
    if show_details:
        print("\n📋 详细记录信息:")
        for i, record in enumerate(filtered_records, 1):
            fields = record.get('fields', {})
            print(f"\n{i}. 标题: {fields.get('标题', 'N/A')}")
            print(f"   平台: {fields.get('平台', 'N/A')}")
            print(f"   状态: {fields.get('状态', 'N/A')}")
            print(f"   类型: {fields.get('类型', 'N/A')}")
            print(f"   难度: {fields.get('难度', 'N/A')}")
            print(f"   开始时间: {fields.get('开始时间', 'N/A')}")
            print(f"   结束时间: {fields.get('结束时间', 'N/A')}")
            print(f"   链接: {fields.get('链接', 'N/A')}")
    
    if export_json:
        # 导出为JSON文件
        export_data = {
            'export_time': datetime.now().isoformat(),
            'total_records': len(filtered_records),
            'unique_titles': len(unique_titles),
            'duplicate_count': len(duplicate_titles),
            'platform_stats': platform_stats,
            'status_stats': status_stats,
            'duplicate_titles': list(set(duplicate_titles)),
            'records': []
        }
        
        for record in filtered_records:
            fields = record.get('fields', {})
            export_data['records'].append({
                'title': fields.get('标题', ''),
                'platform': fields.get('平台', ''),
                'status': fields.get('状态', ''),
                'type': fields.get('类型', ''),
                'difficulty': fields.get('难度', ''),
                'start_time': fields.get('开始时间', ''),
                'end_time': fields.get('结束时间', ''),
                'link': fields.get('链接', ''),
                'participants': fields.get('参与人数', ''),
                'prize': fields.get('奖金', ''),
                'create_time': fields.get('创建时间', '')
            })
        
        filename = f"table_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(export_data, f, ensure_ascii=False, indent=2)
        print(f"\n💾 数据已导出到: {filename}")
    
    print(f"\n🔗 飞书表格链接: https://feishu.cn/base/{FEISHU_APP_TOKEN}")

def check_duplicate_title(title):
    """
    检查指定标题是否已存在于表格中
    
    Args:
        title: 要检查的比赛标题
    
    Returns:
        bool: 如果标题已存在返回True，否则返回False
    """
    print(f"🔍 检查标题是否重复: {title}")
    
    records = get_all_records()
    if not records:
        print("❌ 无法获取表格记录")
        return False
    
    for record in records:
        fields = record.get('fields', {})
        existing_title = fields.get('标题', '')
        if existing_title == title:
            print(f"⚠️ 发现重复标题: {title}")
            print(f"   平台: {fields.get('平台', 'N/A')}")
            print(f"   状态: {fields.get('状态', 'N/A')}")
            print(f"   创建时间: {fields.get('创建时间', 'N/A')}")
            return True
    
    print(f"✅ 标题不重复: {title}")
    return False

def main():
    parser = argparse.ArgumentParser(
        description="获取飞书表格信息，检查重复比赛",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例用法:
  python get_table_info.py                          # 获取基本统计信息
  python get_table_info.py --details               # 显示详细记录信息
  python get_table_info.py --platform baidu        # 只显示百度平台的记录
  python get_table_info.py --export                # 导出数据为JSON文件
  python get_table_info.py --check-title "比赛名称"  # 检查指定标题是否重复
        """
    )
    
    parser.add_argument("--details", action="store_true", help="显示详细记录信息")
    parser.add_argument("--platform", choices=['baidu', 'aliyun', 'wechat', 'tencent'], help="过滤特定平台")
    parser.add_argument("--export", action="store_true", help="导出数据为JSON文件")
    parser.add_argument("--check-title", help="检查指定标题是否已存在")
    
    args = parser.parse_args()
    
    try:
        if args.check_title:
            check_duplicate_title(args.check_title)
        else:
            get_table_info(
                show_details=args.details,
                filter_platform=args.platform,
                export_json=args.export
            )
    except KeyboardInterrupt:
        print("\n❌ 用户中断程序")
    except Exception as e:
        print(f"\n❌ 程序运行出错: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()