"""邮件发送模块"""
import smtplib
import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.header import Header
from typing import List, Dict
from datetime import datetime


class Mailer:
    def __init__(self):
        self.smtp_host = os.getenv("SMTP_HOST", "smtp.gmail.com")
        smtp_port_str = os.getenv("SMTP_PORT", "587")
        self.smtp_port = int(smtp_port_str) if smtp_port_str and smtp_port_str.strip() else 587
        self.username = os.getenv("SMTP_USERNAME")
        self.password = os.getenv("SMTP_PASSWORD")
        self.from_name = os.getenv("FROM_NAME", "ISSCC论文追踪")
    
    def send_digest(self, papers: List[Dict], to_emails: List[str], 
                    subject_prefix: str = "[ISSCC论文]") -> bool:
        """发送论文摘要邮件"""
        if not papers:
            print("No papers to send")
            return False
        
        if not all([self.username, self.password, to_emails]):
            print("Missing email configuration")
            return False
        
        subject = f"{subject_prefix} 最新论文 {len(papers)} 篇"
        
        html_body = self._build_html(papers)
        text_body = self._build_text(papers)
        
        msg = MIMEMultipart('alternative')
        msg['Subject'] = Header(subject, 'utf-8')
        msg['From'] = Header(self.from_name, 'utf-8')
        msg['To'] = ", ".join(to_emails)
        
        msg.attach(MIMEText(text_body, 'plain', 'utf-8'))
        msg.attach(MIMEText(html_body, 'html', 'utf-8'))
        
        try:
            server = smtplib.SMTP(self.smtp_host, self.smtp_port)
            server.starttls()
            server.login(self.username, self.password)
            server.sendmail(self.username, to_emails, msg.as_string())
            server.quit()
            print(f"Email sent successfully to {len(to_emails)} recipients")
            return True
        except Exception as e:
            print(f"Email send error: {e}")
            return False
    
    def _build_html(self, papers: List[Dict]) -> str:
        """构建HTML邮件内容"""
        current_year = datetime.now().year
        
        html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; line-height: 1.6; }}
        .container {{ max-width: 800px; margin: 0 auto; padding: 20px; }}
        h2 {{ color: #1a73e8; border-bottom: 2px solid #1a73e8; padding-bottom: 10px; }}
        .paper {{ margin-bottom: 25px; padding: 15px; border: 1px solid #e0e0e0; border-radius: 8px; }}
        .title {{ font-size: 16px; font-weight: bold; color: #333; margin-bottom: 8px; }}
        .score {{ color: #2196F3; font-weight: bold; }}
        .summary {{ margin-top: 10px; color: #555; font-size: 14px; }}
        .meta {{ font-size: 12px; color: #888; margin-top: 8px; }}
        .link {{ margin-top: 10px; }}
        .link a {{ color: #1a73e8; text-decoration: none; }}
        .link a:hover {{ text-decoration: underline; }}
        .footer {{ margin-top: 30px; padding-top: 20px; border-top: 1px solid #e0e0e0; font-size: 12px; color: #888; text-align: center; }}
    </style>
</head>
<body>
    <div class="container">
        <h2>🔬 ISSCC 电路设计论文追踪</h2>
        <p>共找到 <b>{len(papers)}</b> 篇相关论文</p>
"""
        
        for i, paper in enumerate(papers, 1):
            score = paper.get('relevance_score', 0)
            score_display = f"{score:.2f}" if score else "N/A"
            
            html += f"""
        <div class="paper">
            <div class="title">{i}. {self._escape_html(paper.get('title', ''))}</div>
            <div class="meta">
                <strong>作者:</strong> {self._escape_html(paper.get('authors', 'N/A'))} | 
                <strong>来源:</strong> {paper.get('source', 'N/A')} |
                <strong>相关性:</strong> <span class="score">{score_display}</span>
            </div>
            <div class="summary">{self._escape_html(paper.get('summary_cn', paper.get('abstract', '无摘要')[:200]))}</div>
"""
            
            if paper.get('url'):
                html += f'            <div class="link"><a href="{paper["url"]}" target="_blank">查看论文 →</a></div>\n'
            
            html += "        </div>\n"
        
        html += f"""
        <div class="footer">
            <p>本邮件由ISSCC论文追踪系统自动发送</p>
            <p>生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
        </div>
    </div>
</body>
</html>
"""
        return html
    
    def _build_text(self, papers: List[Dict]) -> str:
        """构建纯文本邮件内容"""
        text = "ISSCC 电路设计论文追踪\n"
        text += "=" * 50 + "\n\n"
        text += f"共找到 {len(papers)} 篇相关论文\n\n"
        
        for i, paper in enumerate(papers, 1):
            score = paper.get('relevance_score', 0)
            score_display = f"{score:.2f}" if score else "N/A"
            
            text += f"{i}. {paper.get('title', '')}\n"
            text += f"   作者: {paper.get('authors', 'N/A')}\n"
            text += f"   来源: {paper.get('source', 'N/A')} | 相关性: {score_display}\n"
            text += f"   摘要: {paper.get('summary_cn', paper.get('abstract', '无摘要')[:150])}...\n"
            if paper.get('url'):
                text += f"   链接: {paper['url']}\n"
            text += "\n" + "-" * 50 + "\n\n"
        
        text += f"\n生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
        return text
    
    def _escape_html(self, text: str) -> str:
        """转义HTML特殊字符"""
        if not text:
            return ""
        return (text
                .replace('&', '&amp;')
                .replace('<', '&lt;')
                .replace('>', '&gt;')
                .replace('"', '&quot;')
                .replace("'", '&#39;'))
