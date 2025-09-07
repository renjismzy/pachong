# 比赛信息爬虫

一个自动爬取各平台比赛信息并同步到飞书表格的Python爬虫程序。

## 项目结构

```
pachong/
├── main.py                 # 主程序入口
├── config.py              # 配置文件
├── feishu_api.py          # 飞书API相关功能
├── utils.py               # 通用工具函数
├── crawlers/              # 爬虫模块目录
│   ├── __init__.py        # 包初始化文件
│   ├── baidu_crawler.py   # 百度AI Studio爬虫
│   ├── aliyun_crawler.py  # 阿里天池爬虫
│   ├── tencent_crawler.py # 腾讯CSDN爬虫
│   └── wechat_crawler.py  # 微信公众号爬虫
├── .env                   # 环境变量配置
├── requirements.txt       # 依赖包列表
└── README.md             # 项目说明文档
```

## 模块说明

### 核心模块

- **main.py**: 程序主入口，处理命令行参数和调度各个爬虫模块
- **config.py**: 集中管理所有配置信息，包括API密钥、URL、爬虫参数等
- **feishu_api.py**: 封装飞书API相关功能，包括数据插入、查询、状态更新等
- **utils.py**: 提供通用工具函数，如文本清理、日期解析、详情获取等

### 爬虫模块 (crawlers/)

- **baidu_crawler.py**: 百度AI Studio平台比赛信息爬取
- **aliyun_crawler.py**: 阿里天池平台比赛信息爬取
- **tencent_crawler.py**: 腾讯CSDN博客比赛信息爬取
- **wechat_crawler.py**: 微信公众号文章爬取

## 功能特性

- 🎯 **多平台支持**: 支持百度AI Studio、阿里天池、腾讯CSDN、微信公众号
- 📊 **飞书集成**: 自动同步数据到飞书表格
- 🔄 **状态更新**: 自动更新比赛状态（进行中/已结束）
- 🤖 **AI分析**: 集成DeepSeek API进行比赛类型和难度分析
  - 难度等级：L1(刚接触电脑) → L2(会用电脑) → L3(对电脑比较熟练) → L4(对电脑很熟悉)
- 🚫 **去重机制**: 自动检测并避免重复数据插入
- ⚡ **批量处理**: 支持批量数据插入和处理
- 🛡️ **错误处理**: 完善的错误处理和重试机制

## 使用方法

### 基本用法

```bash
# 爬取百度AI Studio
python main.py --platform baidu

# 爬取阿里天池
python main.py --platform aliyun

# 爬取腾讯CSDN
python main.py --platform tencent

# 爬取所有平台
python main.py --platform all

# 更新比赛状态
python main.py --platform update-status
```

### 微信公众号爬取

```bash
python main.py --platform wechat --biz <BIZ_ID> --token <TOKEN> --cookie <COOKIE>
```

## 更新日志

### v2.0.0 (当前版本)
- 🔧 重构代码结构，模块化设计
- 📁 分离不同功能到独立文件
- 🎯 改进错误处理和日志输出
- 📊 优化飞书API集成
- 🤖 集成AI分析功能