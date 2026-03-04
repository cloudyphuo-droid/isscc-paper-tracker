"""论文数据获取模块 - 支持IEEE Xplore和DBLP"""
import requests
import json
from typing import List, Dict, Optional
from datetime import datetime


class PaperFetcher:
    """从不同数据源获取论文"""
    
    def __init__(self, ieee_api_key: str = None):
        self.ieee_api_key = ieee_api_key
        self.ieee_base_url = "https://ieeexplore.ieee.org/api/v1/search/articles"
        self.dblp_base_url = "https://dblp.org/search/publ/api"  # 修正为正确的API端点
    
    def fetch_from_ieee(self, conference: str, year: int, max_results: int = 50) -> List[Dict]:
        """从IEEE Xplore获取会议论文"""
        if not self.ieee_api_key:
            print("No IEEE API key, using DBLP fallback")
            return self._fetch_from_dblp(conference, year, max_results)
        
        headers = {
            "x-api-key": self.ieee_api_key,
            "Accept": "application/json"
        }
        
        params = {
            "queryText": f"publication_year:{year}",
            "max_records": max_results,
            "sort_by": "date-published",
            "sort_order": "desc"
        }
        
        try:
            response = requests.get(
                self.ieee_base_url,
                headers=headers,
                params=params,
                timeout=30
            )
            if response.status_code == 200:
                data = response.json()
                articles = data.get("articles", [])
                # 过滤出目标会议的论文
                filtered = [a for a in articles if conference.lower() in a.get("conference", "").lower()]
                return self._parse_ieee_response(filtered)
            else:
                print(f"IEEE API error: {response.status_code}")
                return self._fetch_from_dblp(conference, year, max_results)
        except Exception as e:
            print(f"IEEE API exception: {e}")
            return self._fetch_from_dblp(conference, year, max_results)
    
    def _parse_ieee_response(self, articles: List[Dict]) -> List[Dict]:
        """解析IEEE API响应"""
        papers = []
        for article in articles:
            paper = {
                "title": article.get("article_title", ""),
                "authors": ", ".join([a.get("full_name", "") for a in article.get("authors", [])]),
                "abstract": article.get("abstract", ""),
                "doi": article.get("doi", ""),
                "publication_date": article.get("publication_date", ""),
                "conference": article.get("conference", ""),
                "keywords": article.get("keywords", []),
                "url": f"https://ieeexplore.ieee.org/document/{article.get('id', '')}",
                "source": "IEEE"
            }
            papers.append(paper)
        return papers
    
    def _fetch_from_dblp(self, conference: str, year: int, max_results: int = 50) -> List[Dict]:
        """从DBLP获取论文（免费备用方案）"""
        # DBLP会议论文的venue缩写映射
        conf_mapping = {
            "isscc": "isscc",
            "vlsisymposium": "vlsisymp",
            "dac": "dac",
            "iccad": "iccad",
            "date": "date",
            "islped": "islped",
            "isvlsi": "isvlsi",
            "glsvlsi": "glsvlsi"
        }
        
        conf_key = conf_mapping.get(conference.lower(), conference.lower())
        
        # 使用正确的DBLP查询格式
        params = {
            "q": f"{conf_key} {year}",
            "h": max_results,
            "format": "json",
            "f": 0
        }
        
        try:
            response = requests.get(self.dblp_base_url, params=params, timeout=30)
            if response.status_code == 200:
                data = response.json()
                return self._parse_dblp_response(data)
            else:
                print(f"DBLP API error: {response.status_code}")
                return []
        except Exception as e:
            print(f"DBLP fetch error: {e}")
            return []
    
    def _parse_dblp_response(self, data: Dict) -> List[Dict]:
        """解析DBLP响应"""
        papers = []
        hits = data.get("result", {}).get("hits", {}).get("hit", [])
        
        # 需要过滤掉的内容类型
        exclude_keywords = [
            "editorial", "introduction", "guest editorial", 
            "special section", "foreword", "preface",
            "acknowledgment", "acknowledgements", "call for",
            "conference", "workshop", "symposium"
        ]
        
        for hit in hits:
            info = hit.get("info", {})
            title = info.get("title", "").lower()
            
            # 过滤掉非技术论文
            if any(kw in title for kw in exclude_keywords):
                continue
            
            authors = info.get("authors", {}).get("author", [])
            if isinstance(authors, dict):
                authors = [authors]
            authors_str = ", ".join([a.get("text", a.get("name", "")) for a in authors])
            
            paper = {
                "title": info.get("title", ""),
                "authors": authors_str,
                "venue": info.get("venue", ""),
                "year": info.get("year", ""),
                "doi": info.get("doi", ""),
                "url": info.get("url", ""),
                "abstract": "",  # DBLP不提供摘要
                "source": "DBLP"
            }
            papers.append(paper)
        return papers
    
    def fetch_from_arxiv(self, categories: List[str] = ["eess.AS", "cs.LG", "cs.AR"], 
                         max_results: int = 30) -> List[Dict]:
        """从arXiv获取论文"""
        papers = []
        
        for cat in categories:
            url = "http://export.arxiv.org/api/query"
            params = {
                "search_query": f"cat:{cat}",
                "sortBy": "submittedDate",
                "sortOrder": "descending",
                "max_results": max_results
            }
            
            try:
                response = requests.get(url, params=params, timeout=30)
                if response.status_code == 200:
                    papers.extend(self._parse_arxiv_response(response.text))
            except Exception as e:
                print(f"arXiv fetch error: {e}")
        
        return papers
    
    def _parse_arxiv_response(self, xml_text: str) -> List[Dict]:
        """解析arXiv ATOM响应"""
        import xml.etree.ElementTree as ET
        
        papers = []
        try:
            root = ET.fromstring(xml_text)
            ns = {'atom': 'http://www.w3.org/2005/Atom'}
            
            for entry in root.findall('atom:entry', ns):
                title = entry.find('atom:title', ns).text.strip()
                summary = entry.find('atom:summary', ns).text.strip()
                authors = ", ".join([a.find('atom:name', ns).text for a in entry.findall('atom:author', ns)])
                
                # 获取PDF链接
                links = entry.findall('atom:link', ns)
                pdf_url = ""
                for link in links:
                    if link.get('title') == 'pdf':
                        pdf_url = link.get('href')
                        break
                
                # 获取发布日期
                published = entry.find('atom:published', ns).text[:10] if entry.find('atom:published', ns) is not None else ""
                
                papers.append({
                    "title": title,
                    "authors": authors,
                    "abstract": summary,
                    "url": pdf_url,
                    "publication_date": published,
                    "source": "arXiv",
                    "conference": "arXiv"
                })
        except Exception as e:
            print(f"arXiv XML parse error: {e}")
        
        return papers
