"""AI论文相关性筛选模块 - 使用OpenAI API"""
import openai
import os
import json
import re
from typing import List, Dict


class PaperFilter:
    """使用LLM进行论文相关性筛选"""
    
    def __init__(self, keywords: List[str], min_score: float = 0.7, model: str = "gpt-4o-mini"):
        openai.api_key = os.getenv("OPENAI_API_KEY")
        self.keywords = keywords
        self.min_score = min_score
        self.model = model
    
    def filter_papers(self, papers: List[Dict]) -> List[Dict]:
        """批量筛选论文"""
        if not papers:
            return []
        
        if not os.getenv("OPENAI_API_KEY"):
            print("No OpenAI API key, skipping AI filter")
            return papers[:20]  # 返回前20篇
        
        # 构建提示词
        keyword_str = ", ".join(self.keywords)
        
        # 准备论文信息（限制数量以避免超出token限制）
        paper_list = papers[:30]  # 最多处理30篇
        
        paper_texts = []
        for i, paper in enumerate(paper_list):
            text = f"论文{i}:\n标题: {paper.get('title', '')}"
            if paper.get('abstract'):
                text += f"\n摘要: {paper.get('abstract', '')[:300]}"
            paper_texts.append(text)
        
        prompt = f"""你是一个电路设计领域的专家。请分析以下论文列表，找出与以下研究方向高度相关的论文。

研究方向关键词: {keyword_str}

请对每篇论文进行相关性评分（0-1分），只返回与电路设计（analog, digital, VLSI, SoC, IC, memory, ADC, PLL, RF, power management, low power, AI chip等）相关的论文。

论文列表:
{chr(10).join(paper_texts)}

请返回JSON格式数组（只返回JSON，不要其他内容）:
[
  {{"index": 0, "score": 0.95, "reason": "简短原因"}},
  {{"index": 1, "score": 0.80, "reason": "简短原因"}}
]
只返回评分>=0.6的论文。
"""
        try:
            response = openai.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3
            )
            
            result_text = response.choices[0].message.content
            scores = self._parse_json_response(result_text)
            
            # 筛选高分论文
            filtered = []
            for score_info in scores:
                idx = score_info.get("index", 0)
                score = score_info.get("score", 0)
                if score >= self.min_score and idx < len(paper_list):
                    paper = paper_list[idx].copy()
                    paper["relevance_score"] = score
                    paper["reason"] = score_info.get("reason", "")
                    filtered.append(paper)
            
            # 按相关性排序
            filtered.sort(key=lambda x: x.get("relevance_score", 0), reverse=True)
            print(f"AI筛选后保留 {len(filtered)} 篇论文")
            return filtered
            
        except Exception as e:
            print(f"Filter error: {e}")
            # 出错时返回所有论文
            return papers[:20]
    
    def _parse_json_response(self, text: str) -> List[Dict]:
        """解析JSON响应"""
        # 尝试提取JSON数组
        match = re.search(r'\[[\s\S]*\]', text)
        if match:
            try:
                return json.loads(match.group())
            except json.JSONDecodeError as e:
                print(f"JSON parse error: {e}")
                print(f"Raw text: {text[:200]}")
        return []
