#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试比赛封面上传功能
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from feishu_api import upload_cover_image_from_url, insert_to_feishu
from config import *

def test_cover_upload():
    """测试封面上传功能"""
    print("=" * 60)
    print("🧪 测试比赛封面上传功能")
    print("=" * 60)
    
    # 使用GitHub的一个公开图片进行测试
    test_image_url = "https://github.com/microsoft/vscode/raw/main/resources/linux/code.png"
    
    print(f"📸 测试图片URL: {test_image_url}")
    
    # 测试单独的上传功能
    print("\n1. 测试单独上传功能...")
    file_token = upload_cover_image_from_url(test_image_url)
    
    if file_token:
        print(f"✅ 上传成功，获得file_token: {file_token[:20]}...")
        
        # 测试完整的插入功能
        print("\n2. 测试完整插入功能...")
        success = insert_to_feishu(
            name="测试比赛封面上传",
            link="https://example.com/test-competition",
            cover_image=test_image_url,
            competition_type="其它",
            difficulty_level="L1",
            description="这是一个测试比赛，用于验证封面上传功能"
        )
        
        if success:
            print("✅ 完整插入测试成功！")
        else:
            print("❌ 完整插入测试失败")
    else:
        print("❌ 上传失败")
    
    print("\n" + "=" * 60)
    print("🏁 测试完成")
    print("=" * 60)

if __name__ == "__main__":
    test_cover_upload()