import re
import requests, json, datetime, os, time, random, feedparser
from bs4 import BeautifulSoup
from openai import OpenAI

client = OpenAI(
    base_url="https://ark.cn-beijing.volces.com/api/v3",
    api_key=os.getenv("ARK_API_KEY")
)

today = datetime.date.today().strftime("%Y-%m-%d")

NEWS_SOURCES = {
    "头条": f"https://raw.githubusercontent.com/SnailDev/toutiao-hot-hub/main/archives/{today}.md",
    "腾讯新闻": "https://rsshub.app/tencent/news/index",             # RSS
    "澎湃新闻": "https://rsshub.app/thepaper/featured"              # RSS
}

items = []

def fetch_article_text(url):
    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        res = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(res.text, "html.parser")
        for tag in soup(["script", "style"]):
            tag.decompose()
        text = soup.get_text(separator="\n", strip=True)
        return text[:1500]
    except Exception as e:
        print(f"[跳过] 正文抓取失败: {url}, 错误: {e}")
        return None

def gen_summary(title, content):
    if not content:
        return None, None
    prompt = f"""请根据以下新闻标题和正文片段，用一句话描述事件的主要内容，包含“何时、何地、谁、做了什么”，不要加任何评论或总结性词语。返回格式为：高/中/低: 事件描述。
标题：{title}
正文：{content[:500]}
"""
    for attempt in range(3):
        try:
            rsp = client.chat.completions.create(
                model="ep-20250721132115-4hpdj",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.6,
                max_tokens=150
            )
            text = rsp.choices[0].message.content.strip().replace("：", ":")
            m = re.match(r"(高|中|低)\s*[:：]\s*(.+)", text)
            rel_zh, summ = m.groups() if m else ("中", text)
            rel_map = {"高": "high", "中": "medium", "低": "low"}
            return summ.strip()[:150], rel_map.get(rel_zh, "medium")
        except Exception as e:
            print(f"[{attempt+1}/3] Ark 调用失败: {e}")
            time.sleep(2 + random.uniform(0, 2))
    return None, None

def fetch_from_toutiao():
    url = NEWS_SOURCES["头条"]
    try:
        res = requests.get(url, timeout=20).text
        import re
        pat = re.compile(r'\d+\.\s*\[(.+?)\]\((https?://[^)]+)\)')
        for title, link in pat.findall(res)[:5]:
            content = fetch_article_text(link)
            if not content:
                continue
            summary, rel = gen_summary(title, content)
            if not summary:
                continue
            items.append({
                "title": title.strip(),
                "link": link.strip(),
                "summary": summary,
                "date": today,
                "relevance": rel,
                "priority": 1 if rel == "high" else 2 if rel == "medium" else 3,
                "source": "头条"
            })
    except Exception as e:
        print(f"[WARN] 头条抓取失败: {e}")

def fetch_from_paper():
    try:
        feed = feedparser.parse(NEWS_SOURCES["澎湃新闻"])
        for entry in feed.entries[:5]:
            title, link = entry.title, entry.link
            content = fetch_article_text(link)
            if not content:
                continue
            summary, rel = gen_summary(title, content)
            if not summary:
                continue
            items.append({
                "title": title.strip(),
                "link": link.strip(),
                "summary": summary,
                "date": today,
                "relevance": rel,
                "priority": 1 if rel == "high" else 2 if rel == "medium" else 3,
                "source": "澎湃新闻"
            })
    except Exception as e:
        print(f"[WARN] 澎湃抓取失败: {e}")

def fetch_from_tencent():
    try:
        res = requests.get(NEWS_SOURCES["腾讯新闻"], timeout=20).text
        soup = BeautifulSoup(res, "html.parser")
        cards = soup.select("a")[:20]
        for a in cards:
            title = a.get_text(strip=True)
            href = a.get("href")
            if not title or not href or not href.startswith("http"):
                continue
            content = fetch_article_text(href)
            if not content or len(content) < 200:
                continue
            summary, rel = gen_summary(title, content)
            if not summary:
                continue
            items.append({
                "title": title.strip(),
                "link": href.strip(),
                "summary": summary,
                "date": today,
                "relevance": rel,
                "priority": 1 if rel == "high" else 2 if rel == "medium" else 3,
                "source": "腾讯新闻"
            })
            if len(items) >= 15:
                break
    except Exception as e:
        print(f"[WARN] 腾讯新闻抓取失败: {e}")

# 调用函数
fetch_from_toutiao()
fetch_from_paper()
fetch_from_tencent()

# 排序并保存
items.sort(key=lambda x: x["priority"])
out = f"hotnews_smart_{today}.json"
with open(out, "w", encoding="utf-8") as f:
    json.dump(items, f, ensure_ascii=False, indent=2)

print(f"✅ 生成完成，共 {len(items)} 条 → {out}")