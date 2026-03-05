"""主程序入口 - ISSCC论文追踪系统"""
import yaml
import os
import sys
import json
from datetime import datetime
from dotenv import load_dotenv

# 添加src目录到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from fetcher import PaperFetcher
from filter import PaperFilter
from generator import SummaryGenerator
from mailer import Mailer

# 缓存文件路径
CACHE_FILE = os.path.join(os.path.dirname(__file__), '..', '.cache', 'sent_papers.json')


def load_config(config_path: str = None) -> dict:
    """加载配置文件"""
    if config_path is None:
        config_path = os.path.join(
            os.path.dirname(__file__), 
            'config', 
            'config.yaml'
        )
    
    if os.path.exists(config_path):
        with open(config_path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f)
    return {}


def load_sent_papers() -> set:
    """加载已推送的论文URL"""
    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return set(data.get('sent_urls', []))
        except:
            return set()
    return set()


def save_sent_papers(urls: set):
    """保存已推送的论文URL"""
    cache_dir = os.path.dirname(CACHE_FILE)
    if not os.path.exists(cache_dir):
        os.makedirs(cache_dir)
    with open(CACHE_FILE, 'w', encoding='utf-8') as f:
        json.dump({'sent_urls': list(urls)}, f)


def collect_keywords(conferences: list) -> set:
    """收集所有会议的关注关键词"""
    keywords = set()
    for conf in conferences:
        keywords.update(conf.get("keywords", []))
    return keywords


def main():
    """主函数"""
    print("=" * 60)
    print("ISSCC论文追踪系统启动")
    print(f"时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    
    # 加载环境变量
    load_dotenv()
    
    # 检查测试模式
    test_mode = os.getenv("TEST_MODE", "").lower() == "true"
    if test_mode:
        print("测试模式：邮件功能已禁用")
    
    # 加载配置
    config = load_config()
    tracker_config = config.get("tracker", {})
    
    if not tracker_config:
        # 使用默认配置
        tracker_config = {
            "conferences": [
                {
                    "name": "ISSCC",
                    "year": 2026,
                    "keywords": ["circuit", "analog", "digital", "VLSI", "SoC", "memory", "ADC", "PLL", "RF", "power"]
                },
                {
                    "name": "ISSCC",
                    "year": 2025,
                    "keywords": ["circuit", "analog", "digital", "VLSI", "SoC", "memory", "ADC", "PLL", "RF", "power"]
                }
            ],
            "filter": {"min_relevance_score": 0.6},
            "limits": {"max_papers_per_run": 15}
        }
    
    conferences = tracker_config.get("conferences", [])
    keywords = collect_keywords(conferences)
    
    print(f"\n关注的会议: {[c['name'] + str(c['year']) for c in conferences]}")
    print(f"关键词: {', '.join(keywords)}")
    
    # 1. 获取论文
    print("\n[1/4] 正在获取论文...")
    fetcher = PaperFetcher(ieee_api_key=os.getenv("IEEE_API_KEY"))
    
    all_papers = []
    for conf in conferences:
        conf_name = conf["name"]
        conf_year = conf["year"]
        print(f"  获取 {conf_name} {conf_year}...")
        
        papers = fetcher.fetch_from_ieee(conf_name, conf_year, max_results=30)
        print(f"    获取到 {len(papers)} 篇")
        all_papers.extend(papers)
    
    # 去重
    seen_titles = set()
    unique_papers = []
    for paper in all_papers:
        title_lower = paper.get("title", "").lower()
        if title_lower and title_lower not in seen_titles:
            seen_titles.add(title_lower)
            unique_papers.append(paper)
    
    # 过滤已推送的论文（避免重复）
    sent_urls = load_sent_papers()
    new_papers = []
    new_urls = []
    for paper in unique_papers:
        url = paper.get('url', '')
        if url and url not in sent_urls:
            new_papers.append(paper)
            new_urls.append(url)
        elif not url:
            # 如果没有URL，用标题作为唯一标识
            new_papers.append(paper)
    
    print(f"  去重后共 {len(unique_papers)} 篇论文")
    print(f"  新论文: {len(new_papers)} 篇 (已过滤 {len(sent_urls)} 篇历史论文)")
    
    if not new_papers:
        print("\n没有新论文，已全部推送过")
        return
    
    # 保存新论文URL到缓存
    if new_urls:
        sent_urls.update(new_urls)
        save_sent_papers(sent_urls)
    
    if not new_papers:
        print("\n没有新论文，已全部推送过")
        return
    
    # 保存新论文URL到缓存
    if new_urls:
        sent_urls.update(new_urls)
        save_sent_papers(sent_urls)
    
    if not new_papers:
        print("\n没有获取到论文，尝试获取arXiv论文...")
        arxiv_papers = fetcher.fetch_from_arxiv(
            categories=["eess.AS", "cs.AR", "cs.LG"],
            max_results=20
        )
        new_papers = arxiv_papers
        print(f"  获取到 {len(new_papers)} 篇arXiv论文")
    
    if not new_papers:
        print("\n没有获取到任何论文，程序退出")
        return
    
    # 2. AI筛选
    print("\n[2/4] 正在进行AI相关性筛选...")
    paper_filter = PaperFilter(
        keywords=list(keywords),
        min_score=tracker_config.get("filter", {}).get("min_relevance_score", 0.6),
        model=config.get("openai", {}).get("model", "gpt-4o-mini")
    )
    filtered_papers = paper_filter.filter_papers(new_papers)
    
    # 限制数量
    max_papers = tracker_config.get("limits", {}).get("max_papers_per_run", 15)
    filtered_papers = filtered_papers[:max_papers]
    
    print(f"  筛选后保留 {len(filtered_papers)} 篇论文")
    
    if not filtered_papers:
        print("\n没有符合筛选条件的论文")
        return
    
    # 3. 生成摘要
    print("\n[3/4] 正在生成中文摘要...")
    summary_gen = SummaryGenerator(
        model=config.get("openai", {}).get("model", "gpt-4o-mini")
    )
    final_papers = summary_gen.generate_summaries(filtered_papers)
    
    # 4. 发送邮件
    print("\n[4/4] 正在发送邮件...")
    mail_enabled = config.get("mail", {}).get("enabled", True)
    
    # 测试模式下禁用邮件
    if test_mode:
        mail_enabled = False
    
    if mail_enabled:
        mailer = Mailer()
        to_emails_str = os.getenv("TO_EMAILS", "")
        to_emails = [e.strip() for e in to_emails_str.split(",") if e.strip()]
        
        if to_emails:
            subject_prefix = config.get("mail", {}).get("subject_prefix", "[ISSCC论文]")
            success = mailer.send_digest(
                papers=final_papers,
                to_emails=to_emails,
                subject_prefix=subject_prefix
            )
            if success:
                print("  邮件发送成功!")
            else:
                print("  邮件发送失败")
        else:
            print("  未配置接收邮箱，仅输出到控制台")
            _print_papers_console(final_papers)
    else:
        print("  邮件功能已禁用，仅输出到控制台")
        _print_papers_console(final_papers)
    
    print("\n" + "=" * 60)
    print("处理完成!")
    print("=" * 60)


def _print_papers_console(papers: list):
    """在控制台打印论文列表"""
    print("\n论文列表:")
    for i, paper in enumerate(papers, 1):
        print(f"\n{i}. {paper.get('title', '')}")
        print(f"   作者: {paper.get('authors', 'N/A')}")
        print(f"   相关性: {paper.get('relevance_score', 0):.2f}")
        print(f"   摘要: {paper.get('summary_cn', paper.get('abstract', '无')[:100])}...")
        if paper.get('url'):
            print(f"   链接: {paper['url']}")


if __name__ == "__main__":
    main()
