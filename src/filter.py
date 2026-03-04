"""AI论文相关性筛选模块 - 支持OpenAI和智谱GLM API"""
import os
import json
import re
import requests
from typing import List, Dict


class PaperFilter:
    """使用LLM进行论文相关性筛选"""
    
    def __init__(self, keywords: List[str], min_score: float = 0.7, model: str = "gpt-4o-mini"):
        self.keywords = keywords
        self.min_score = min_score
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
    
    def filter_papers(self, papers: List[Dict]) -> List[Dict]:
        """批量筛选论文"""
        if not papers:
            return []
        
        if not self.api_type:
            print("No AI API key available, skipping AI filter")
            return papers[:20]
        
        # 构建提示词
        keyword_str = ", ".join(self.keywords)
        
        # 准备论文信息（限制数量以避免超出token限制）
        paper_list = papers[:30]
        
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
            if self.api_type == "zhipu":
                result_text = self._call_zhipu(prompt)
            else:
                result_text = self._call_openai(prompt)
            
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
            
            filtered.sort(key=lambda x: x.get("relevance_score", 0), reverse=True)
            print(f"AI筛选后保留 {len(filtered)} 篇论文")
            return filtered
            
        except Exception as e:
            print(f"Filter error: {e}")
            return papers[:20]
    
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
            "temperature": 0.3
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
            temperature=0.3
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
