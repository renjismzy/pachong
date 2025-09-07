#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
重复检查模块
用于在添加新比赛前检查是否已存在相同或相似的比赛
"""

import re
import json
import requests
from difflib import SequenceMatcher
from feishu_api import get_all_records
from config import DEEPSEEK_API_KEY, REQUEST_CONFIG
from typing import List, Dict, Tuple, Optional

class DuplicateChecker:
    """重复检查器类"""
    
    def __init__(self, similarity_threshold: float = 0.8):
        """
        初始化重复检查器
        
        Args:
            similarity_threshold: 相似度阈值，超过此值认为是重复
        """
        self.similarity_threshold = similarity_threshold
        self.existing_records = []
        self.load_existing_records()
    
    def load_existing_records(self):
        """加载现有记录"""
        print("🔄 加载现有记录...")
        records = get_all_records()
        if records:
            self.existing_records = records
            print(f"✅ 已加载 {len(records)} 条现有记录")
        else:
            print("⚠️ 未能加载现有记录")
    
    def normalize_title(self, title: str) -> str:
        """标准化标题，用于比较"""
        if not title:
            return ""
        
        # 转换为小写
        title = title.lower()
        
        # 移除常见的标点符号和空白字符
        title = re.sub(r'[\s\-_—–]+', '', title)
        
        # 移除常见的后缀词汇
        suffixes = ['比赛', '竞赛', '大赛', 'competition', 'contest', 'challenge', 'hackathon']
        for suffix in suffixes:
            title = title.replace(suffix.lower(), '')
        
        return title.strip()
    
    def calculate_similarity(self, title1: str, title2: str) -> float:
        """计算两个标题的相似度"""
        norm_title1 = self.normalize_title(title1)
        norm_title2 = self.normalize_title(title2)
        
        if not norm_title1 or not norm_title2:
            return 0.0
        
        return SequenceMatcher(None, norm_title1, norm_title2).ratio()
    
    def analyze_duplicate_with_deepseek(self, new_title: str, new_description: str, existing_records: List[Dict]) -> Dict:
        """使用DeepSeek AI分析比赛重复性
        
        Args:
            new_title: 新比赛标题
            new_description: 新比赛描述
            existing_records: 现有记录列表
        
        Returns:
            dict: AI分析结果
        """
        if not DEEPSEEK_API_KEY:
            print("⚠️ DeepSeek API密钥未配置，跳过AI重复分析")
            return {'is_duplicate': False, 'confidence': 0.0, 'reason': 'API未配置'}
        
        try:
            # 构建现有比赛信息摘要
            existing_summaries = []
            for record in existing_records[:10]:  # 限制数量避免token过多
                fields = record.get('fields', {})
                title = fields.get('比赛名称', '')
                desc = fields.get('比赛描述', '')
                if title:
                    existing_summaries.append(f"标题: {title}\n描述: {desc[:100]}...")
            
            existing_text = "\n\n".join(existing_summaries)
            
            prompt = f"""
请分析以下新比赛是否与现有比赛重复。请考虑比赛的主题、内容、组织方等因素。

新比赛信息：
标题: {new_title}
描述: {new_description}

现有比赛信息：
{existing_text}

请返回JSON格式的分析结果：
{{
  "is_duplicate": true/false,
  "confidence": 0.0-1.0,
  "most_similar_title": "最相似的比赛标题",
  "reason": "判断理由"
}}

判断标准：
- 如果比赛主题、内容、时间完全相同，则为重复
- 如果只是名称相似但内容不同，则不重复
- 考虑比赛的具体领域和要求
"""
            
            headers = {
                'Authorization': f'Bearer {DEEPSEEK_API_KEY}',
                'Content-Type': 'application/json'
            }
            
            data = {
                'model': 'deepseek-chat',
                'messages': [
                    {
                        'role': 'user',
                        'content': prompt
                    }
                ],
                'temperature': 0.1,
                'max_tokens': 800
            }
            
            response = requests.post(
                'https://api.deepseek.com/chat/completions',
                headers=headers,
                json=data,
                timeout=REQUEST_CONFIG['timeout']
            )
            
            if response.status_code == 200:
                result = response.json()
                content = result['choices'][0]['message']['content']
                
                try:
                    analysis = json.loads(content)
                    print(f"🤖 AI重复分析: {analysis.get('reason', '无理由')}")
                    return analysis
                except json.JSONDecodeError:
                    print(f"⚠️ AI响应解析失败: {content}")
                    return {'is_duplicate': False, 'confidence': 0.0, 'reason': '解析失败'}
            else:
                print(f"❌ DeepSeek API调用失败: {response.status_code}")
                return {'is_duplicate': False, 'confidence': 0.0, 'reason': 'API调用失败'}
                
        except Exception as e:
            print(f"❌ DeepSeek重复分析出错: {str(e)}")
            return {'is_duplicate': False, 'confidence': 0.0, 'reason': f'分析出错: {str(e)}'}
    
    def check_exact_duplicate(self, title: str, platform: str = None) -> Optional[Dict]:
        """检查完全重复的记录"""
        for record in self.existing_records:
            fields = record.get('fields', {})
            existing_title = fields.get('标题', '')
            existing_platform = fields.get('平台', '')
            
            # 完全匹配标题
            if existing_title == title:
                # 如果指定了平台，也要匹配平台
                if platform is None or existing_platform == platform:
                    return {
                        'type': 'exact',
                        'record': record,
                        'similarity': 1.0,
                        'existing_title': existing_title,
                        'existing_platform': existing_platform
                    }
        
        return None
    
    def check_similar_duplicate(self, title: str, platform: str = None) -> List[Dict]:
        """检查相似的重复记录"""
        similar_records = []
        
        for record in self.existing_records:
            fields = record.get('fields', {})
            existing_title = fields.get('标题', '')
            existing_platform = fields.get('平台', '')
            
            if not existing_title:
                continue
            
            similarity = self.calculate_similarity(title, existing_title)
            
            if similarity >= self.similarity_threshold:
                # 如果指定了平台，优先考虑同平台的记录
                platform_match = platform is None or existing_platform == platform
                
                similar_records.append({
                    'type': 'similar',
                    'record': record,
                    'similarity': similarity,
                    'existing_title': existing_title,
                    'existing_platform': existing_platform,
                    'platform_match': platform_match
                })
        
        # 按相似度和平台匹配排序
        similar_records.sort(key=lambda x: (x['platform_match'], x['similarity']), reverse=True)
        
        return similar_records
    
    def check_duplicate(self, title: str, platform: str = None, link: str = None, description: str = "", use_ai: bool = True) -> Dict:
        """综合检查重复记录"""
        result = {
            'is_duplicate': False,
            'duplicate_type': None,
            'exact_match': None,
            'similar_matches': [],
            'ai_analysis': None,
            'recommendation': 'add'  # add, skip, review
        }
        
        # 检查完全重复
        exact_match = self.check_exact_duplicate(title, platform)
        if exact_match:
            result['is_duplicate'] = True
            result['duplicate_type'] = 'exact'
            result['exact_match'] = exact_match
            result['recommendation'] = 'skip'
            return result
        
        # 检查链接重复（如果提供了链接）
        if link:
            for record in self.existing_records:
                fields = record.get('fields', {})
                existing_link = fields.get('比赛链接', {}).get('link', '') or fields.get('链接', '')
                if existing_link == link:
                    result['is_duplicate'] = True
                    result['duplicate_type'] = 'link'
                    result['exact_match'] = {
                        'type': 'link',
                        'record': record,
                        'similarity': 1.0,
                        'existing_title': fields.get('比赛名称', '') or fields.get('标题', ''),
                        'existing_platform': fields.get('平台', '')
                    }
                    result['recommendation'] = 'skip'
                    return result
        
        # 检查相似重复
        similar_matches = self.check_similar_duplicate(title, platform)
        if similar_matches:
            result['similar_matches'] = similar_matches
            
            # 如果有高相似度的匹配，建议审查
            if similar_matches[0]['similarity'] >= 0.9:
                result['is_duplicate'] = True
                result['duplicate_type'] = 'similar'
                result['recommendation'] = 'review'
        
        # 使用DeepSeek AI进行智能重复分析
        if use_ai and description and DEEPSEEK_API_KEY:
            print(f"🤖 使用AI分析比赛重复性: {title}")
            ai_analysis = self.analyze_duplicate_with_deepseek(title, description, self.existing_records)
            result['ai_analysis'] = ai_analysis
            
            # 如果AI判断为重复且置信度高，更新结果
            if ai_analysis.get('is_duplicate') and ai_analysis.get('confidence', 0) >= 0.8:
                result['is_duplicate'] = True
                result['duplicate_type'] = 'ai_detected'
                result['recommendation'] = 'skip' if ai_analysis.get('confidence', 0) >= 0.9 else 'review'
                print(f"🚫 AI检测到重复: {ai_analysis.get('reason', '未知原因')}")
            elif ai_analysis.get('confidence', 0) >= 0.6:
                result['recommendation'] = 'review'
                print(f"⚠️ AI建议人工审查: {ai_analysis.get('reason', '未知原因')}")
        
        return result
    
    def print_duplicate_report(self, title: str, platform: str, check_result: Dict):
        """打印重复检查报告"""
        if not check_result['is_duplicate']:
            ai_analysis = check_result.get('ai_analysis')
            if ai_analysis and ai_analysis.get('confidence', 0) > 0.3:
                print(f"✅ 无重复: {title} (AI置信度: {ai_analysis.get('confidence', 0):.2f})")
            else:
                print(f"✅ 无重复: {title}")
            return
        
        print(f"⚠️ 发现重复: {title}")
        print(f"   平台: {platform}")
        print(f"   重复类型: {check_result['duplicate_type']}")
        
        if check_result['exact_match']:
            match = check_result['exact_match']
            print(f"   完全匹配: {match['existing_title']}")
            print(f"   现有平台: {match['existing_platform']}")
        
        if check_result['similar_matches']:
            print(f"   相似匹配 ({len(check_result['similar_matches'])} 条):")
            for i, match in enumerate(check_result['similar_matches'][:3], 1):
                print(f"     {i}. {match['existing_title']} (相似度: {match['similarity']:.2f})")
                print(f"        平台: {match['existing_platform']}")
        
        # 显示AI分析结果
        ai_analysis = check_result.get('ai_analysis')
        if ai_analysis:
            print(f"   🤖 AI分析:")
            print(f"      重复判断: {'是' if ai_analysis.get('is_duplicate') else '否'}")
            print(f"      置信度: {ai_analysis.get('confidence', 0):.2f}")
            print(f"      理由: {ai_analysis.get('reason', '无')}")
            if ai_analysis.get('most_similar_title'):
                print(f"      最相似: {ai_analysis.get('most_similar_title')}")
        
        print(f"   建议: {check_result['recommendation']}")

def check_competition_duplicate(title: str, platform: str = None, link: str = None, 
                              description: str = "", similarity_threshold: float = 0.8, 
                              use_ai: bool = True) -> Dict:
    """检查比赛是否重复的便捷函数"""
    checker = DuplicateChecker(similarity_threshold)
    return checker.check_duplicate(title, platform, link, description, use_ai)

def batch_check_duplicates(competitions: List[Dict], similarity_threshold: float = 0.8, use_ai: bool = True) -> List[Dict]:
    """批量检查比赛重复"""
    checker = DuplicateChecker(similarity_threshold)
    results = []
    
    for comp in competitions:
        title = comp.get('title', '')
        platform = comp.get('platform', '')
        link = comp.get('link', '')
        description = comp.get('description', '')
        
        check_result = checker.check_duplicate(title, platform, link, description, use_ai)
        results.append({
            'competition': comp,
            'check_result': check_result
        })
    
    return results

if __name__ == "__main__":
    # 测试功能
    import argparse
    
    parser = argparse.ArgumentParser(description="重复检查工具")
    parser.add_argument("--title", required=True, help="要检查的比赛标题")
    parser.add_argument("--platform", help="比赛平台")
    parser.add_argument("--link", help="比赛链接")
    parser.add_argument("--threshold", type=float, default=0.8, help="相似度阈值")
    
    args = parser.parse_args()
    
    checker = DuplicateChecker(args.threshold)
    result = checker.check_duplicate(args.title, args.platform, args.link)
    checker.print_duplicate_report(args.title, args.platform or "未知", result)