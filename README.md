# ISSCC论文追踪系统

自动获取ISSCC等电路设计顶级会议论文，并通过邮件推送。

## 功能特性

- 🤖 AI相关性筛选 (使用OpenAI GPT模型)
- 📝 自动生成中文摘要
- 📧 邮件推送
- ⏰ 每日自动运行 (GitHub Actions)
- 🔄 支持扩展到其他会议 (VLSI, DAC, ICCAD等)

## 快速开始

### 1. 克隆仓库

```bash
git clone https://github.com/yourusername/isscc-paper-tracker.git
cd isscc-paper-tracker
```

### 2. 配置环境变量

```bash
cp .env.example .env
# 编辑 .env 文件，填入你的API密钥
```

### 3. 本地测试

```bash
pip install -r requirements.txt
cd src && python main.py
```

### 4. 部署到GitHub

1. 创建GitHub仓库
2. 添加Secrets配置:
   - `OPENAI_API_KEY` - OpenAI API密钥
   - `SMTP_HOST` - SMTP服务器
   - `SMTP_USERNAME` - 发送邮箱
   - `SMTP_PASSWORD` - 邮箱密码(App密码)
   - `TO_EMAILS` - 接收邮箱

## 配置说明

编辑 `config/config.yaml` 修改:

- 关注的会议列表
- 筛选关键词
- 推送数量限制
- 邮件主题等

## 扩展

在配置文件中添加更多会议:

```yaml
conferences:
  - name: "VLSI"
    year: 2026
    keywords: ["VLSI", "circuit", "SoC"]
  - name: "DAC"
    year: 2026
    keywords: ["EDA", "design automation"]
```

## 许可证

MIT
