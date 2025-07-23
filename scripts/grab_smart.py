import requests, re, json, datetime, os, time, random, feedparser
from bs4 import BeautifulSoup
from openai import OpenAI

# 初始化 Ark 客户端
client = OpenAI(
    base_url="https://ark.cn-beijing.volces.com/api/v3",
    api_key=os.getenv("ARK_API_KEY")
)

today = datetime.date.today().strftime("%Y-%m-%d")
items = []

# 各平台源配置
SOURCES = {
    "头条": {
        "type": "md",
        "url": f"https://raw.githubusercontent.com/SnailDev/toutiao-hot-hub/main/archives/{today}.md"
    },
    "澎湃新闻": {
        "type": "rss",
        "url": "https://rsshub.app/thepaper/featured"
    },
    "腾讯新闻": {
        "type": "rss",
        "url": "https://news.qq.com/world_index.xml"
    }
}

# 抓取正文
def fetch_article_text(url):
    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        res = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(res.text, "html.parser")
        for tag in soup(["script", "style"]): tag.decompose()
        text = soup.get_text(separator="\n", strip=True)
        return text[:1500] if len(text) > 200 else None
    except Exception:
        return None

# 生成摘要
def gen_summary(title, content):
    prompt = f"""请根据以下新闻标题和正文片段，用一句话新闻简讯风格描述事件发生，需包含时间、地点、人物、行为及结果，禁止评论性词语。\n格式：高/中/低: 时间 地点 人物 做了什么（结果）\n标题：{title}\n正文：{content[:500]}"""
    for _ in range(3):
        try:
            rsp = client.chat.completions.create(
                model="ep-20250721132115-4hpdj",
                messages=[{"role":"user","content":prompt}],
                temperature=0.5,
                max_tokens=150
            )
            out = rsp.choices[0].message.content.strip().replace("：", ":")
            m = re.match(r"(高|中|低)\s*[:：]\s*(.+)", out)
            rel, summ = ("high","中",)[0] if False else (None,None)
            if m:
                zh, text = m.groups()
                rel = {"高":"high","中":"medium","低":"low"}.get(zh, "medium")
                return text.strip(), rel
        except Exception:
            time.sleep(1)
    return None, None

# 处理各平台
for name, cfg in SOURCES.items():
    try:
        if cfg["type"] == "md":
            pat = re.compile(r"\d+\.\s*\[(.+?)\]\((https?://[^)]+)\)")
            text = requests.get(cfg["url"], timeout=20).text
            for title, link in pat.findall(text)[:5]:
                content = fetch_article_text(link)
                if not content: continue
                summary, rel = gen_summary(title, content)
                if not summary: continue
                items.append({"source":name,"title":title,"link":link,
                              "summary":summary,"date":today,
                              "relevance":rel,
                              "priority":1 if rel=="high" else 2 if rel=="medium" else 3})
        else:
            feed = feedparser.parse(cfg["url"])
            for entry in feed.entries[:5]:
                title, link = entry.title, entry.link
                content = fetch_article_text(link)
                if not content: continue
                summary, rel = gen_summary(title, content)
                if not summary: continue
                items.append({"source":name,"title":title,"link":link,
                              "summary":summary,"date":entry.get("published",today)[:10],
                              "relevance":rel,
                              "priority":1 if rel=="high" else 2 if rel=="medium" else 3})
    except Exception as e:
        print(f"[WARN] {name} 处理失败: {e}")

# 排序与保存
items.sort(key=lambda x: x["priority"])
outf = f"hotnews_smart_{today}.json"
with open(outf, "w", encoding="utf-8") as f:
    json.dump(items, f, ensure_ascii=False, indent=2)
print(f"✅ 完成，共 {len(items)} 条 → {outf}")
