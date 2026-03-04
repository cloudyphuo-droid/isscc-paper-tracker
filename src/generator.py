"""论文摘要生成模块 - 支持OpenAI和智谱GLM API"""
import os
import json
import re
import requests
from typing import List, Dict


class SummaryGenerator:
    """生成论文中文摘要"""
    
    def __init__(self, model: str = "gpt-4o-mini"):
        self.model = model
        self.api_type = None
        self._detect_api()
    
    def _detect_api(self):
        """检测可用的API"""
        # 优先使用智谱GLM
        zhipu_key = os.getenv("ZHIPU_API_KEY")
        if zhipu_key:
            self.api_type = "zhipu"
            self.api_key = zhipu_key
            return
        
        # 其次使用OpenAI
        openai_key = os.getenv("OPENAI_API_KEY")
        if openai_key and openai_key.startswith("sk-"):
            self.api_type = "openai"
            self.api_key = openai_key
            return
        
        self.api_type = None
    
    def generate_summaries(self, papers: List[Dict]) -> List[Dict]:
        """为论文列表生成中文摘要"""
        if not papers:
            return papers
        
        if not self.api_type:
            print("No AI API key available, using original abstracts")
            for paper in papers:
                paper["summary_cn"] = paper.get("abstract", "")[:200] if paper.get("abstract") else "无摘要"
            return papers
        
        # 批量生成以节省API调用
        paper_texts = []
        for i, paper in enumerate(papers):
            text = f"论文{i}:\n标题: {paper.get('title', '')}\n"
            if paper.get('abstract'):
                text += f"原文摘要: {paper.get('abstract', '')[:400]}"
            paper_texts.append(text)
        
        prompt = f"""请为以下电路设计领域的学术论文生成详细的中文摘要（每篇80-150字）。

要求：
1. 用中文输出
2. 保留核心技术关键词（英文缩写）
3. 必须包含：创新点、技术指标、应用场景
4. 格式："[研究目标] 本文提出...[创新点]...实现了...[性能指标]...适用于..."

论文列表:
{chr(10).join(paper_texts)}

请返回JSON格式数组:
[
  {{"index": 0, "summary": "详细中文摘要"}},
  {{"index": 1, "summary": "详细中文摘要"}}
]
只返回JSON，不要其他内容。
"""
        
        try:
            if self.api_type == "zhipu":
                result_text = self._call_zhipu(prompt)
            else:
                result_text = self._call_openai(prompt)
            
            summaries = self._parse_json_response(result_text)
            
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
            for paper in papers:
                paper["summary_cn"] = paper.get("abstract", "")[:150] if paper.get("abstract") else "无摘要"
        
        return papers
    
    def _call_zhipu(self, prompt: str) -> str:
        """调用智谱GLM API"""
        url = "https://open.bigmodel.cn/api/paas/v4/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        data = {
            "model": "glm-4-flash",
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.5
        }
        
        response = requests.post(url, headers=headers, json=data, timeout=60)
        if response.status_code == 200:
            result = response.json()
            return result.get("choices", [{}])[0].get("message", {}).get("content", "")
        else:
            raise Exception(f"Zhipu API error: {response.status_code} - {response.text}")
    
    def _call_openai(self, prompt: str) -> str:
        """调用OpenAI API"""
        import openai
        openai.api_key = self.api_key
        
        response = openai.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.5
        )
        return response.choices[0].message.content
    
    def _parse_json_response(self, text: str) -> List[Dict]:
        """解析JSON响应"""
        match = re.search(r'\[[\s\S]*\]', text)
        if match:
            try:
                return json.loads(match.group())
            except json.JSONDecodeError as e:
                print(f"JSON parse error: {e}")
        return []
