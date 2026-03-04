"""论文摘要生成模块 - 使用LLM生成中文摘要"""
import openai
import os
import json
import re
from typing import List, Dict


class SummaryGenerator:
    """生成论文中文摘要"""
    
    def __init__(self, model: str = "gpt-4o-mini"):
        openai.api_key = os.getenv("OPENAI_API_KEY")
        self.model = model
    
    def generate_summaries(self, papers: List[Dict]) -> List[Dict]:
        """为论文列表生成中文摘要"""
        if not papers:
            return papers
        
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            print("No OpenAI API key, using original abstracts")
            for paper in papers:
                paper["summary_cn"] = paper.get("abstract", "")[:200] if paper.get("abstract") else "无摘要"
            return papers
        
        # 检查是否是无效的key（配额不足等）
        if not api_key.startswith("sk-"):
            print("Invalid OpenAI API key, using original abstracts")
            for paper in papers:
                paper["summary_cn"] = paper.get("abstract", "")[:200] if paper.get("abstract") else "无摘要"
            return papers
        
        openai.api_key = api_key
        
        # 批量生成以节省API调用
        paper_texts = []
        for i, paper in enumerate(papers):
            text = f"论文{i}:\n标题: {paper.get('title', '')}\n"
            if paper.get('abstract'):
                text += f"原文摘要: {paper.get('abstract', '')[:400]}"
            paper_texts.append(text)
        
        prompt = f"""请为以下电路设计领域的学术论文生成简洁的中文摘要（每篇30-80字）。

要求：
1. 用中文输出
2. 保留核心技术关键词（英文）
3. 突出创新点和应用场景

论文列表:
{chr(10).join(paper_texts)}

请返回JSON格式数组:
[
  {{"index": 0, "summary": "中文摘要"}},
  {{"index": 1, "summary": "中文摘要"}}
]
只返回JSON，不要其他内容。
"""
        
        try:
            response = openai.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.5
            )
            
            summaries = self._parse_json_response(response.choices[0].message.content)
            
            # 合并摘要到论文
            for s in summaries:
                idx = s.get("index", 0)
                if idx < len(papers):
                    papers[idx]["summary_cn"] = s.get("summary", "")
            
            # 处理没有生成摘要的论文
            for paper in papers:
                if "summary_cn" not in paper:
                    paper["summary_cn"] = paper.get("abstract", "")[:150] if paper.get("abstract") else "无摘要"
                    
            print(f"生成摘要完成，共 {len(papers)} 篇")
            
        except Exception as e:
            print(f"Summary generation error: {e}")
            # 出错时使用原文摘要
            for paper in papers:
                paper["summary_cn"] = paper.get("abstract", "")[:150] if paper.get("abstract") else "无摘要"
        
        return papers
    
    def _parse_json_response(self, text: str) -> List[Dict]:
        """解析JSON响应"""
        match = re.search(r'\[[\s\S]*\]', text)
        if match:
            try:
                return json.loads(match.group())
            except json.JSONDecodeError as e:
                print(f"JSON parse error: {e}")
        return []
