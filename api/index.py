#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Vercel部署入口文件
"""

import sys
import os
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# 导入Flask应用
from web_app_vercel import app

# 如果直接运行此文件，启动开发服务器
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)