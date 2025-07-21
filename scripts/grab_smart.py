import requests, re, json, datetime, os, time, random
from bs4 import BeautifulSoup
from openai import OpenAI

client = OpenAI(
    base_url="https://ark.cn-beijing.volces.com/api/v3",
    api_key=os.getenv("ARK_API_KEY")
)

today = datetime.date.today().strftime("%Y-%m-%d")
URLS = {
    "微博":  f"https://raw.githubusercontent.com/SnailDev/weibo-hot-hub/main/archives/{today}.md",
    "知乎":  f"https://raw.githubusercontent.com/SnailDev/zhihu-hot-hub/main/archives/{today}.md",
    "微信":  f"https://raw.githubusercontent.com/SnailDev/wechat-hot-hub/main/archives/{today}.md",
    "头条":  f"https://raw.githubusercontent.com/SnailDev/toutiao-hot-hub/main/archives/{today}.md",
    "抖音":  f"https://raw.githubusercontent.com/SnailDev/douyin-hot-hub/main/archives/{today}.md"
}
pat = re.compile(r'\d+\.\s*\[(.+?)\]\((https?://[^)]+)\)')
items = []

def basic_summary(title: str):
    return (title[:38] + '…') if len(title) > 40 else title

def fetch_article_text(url):
    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        res = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(res.text, "html.parser")
        for tag in soup(["script", "style"]):
            tag.decompose()
        text = soup.get_text(separator="\n", strip=True)
        return text[:1000]
    except Exception as e:
        print(f"[跳过] 内容抓取失败: {url}, 错误: {e}")
        return None

def gen_summary(title, content):
    if not content:
        return None, None
    prompt = f"""请根据以下新闻标题和正文片段，提取事件的主要内容，用一句话简洁明确地描述清楚“何时、何地、谁、做了什么”。不要进行价值判断或总结性质，不要说“引发争议”“引发讨论”“反映问题”等字眼。
格式：高/中/低: 事件具体描述
标题：{title}
正文：{content[:500]}
"""
    for attempt in range(3):
        try:
            rsp = client.chat.completions.create(
                model="ep-20250721132115-4hpdj",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.6,
                max_tokens=120
            )
            text = rsp.choices[0].message.content.strip()
            text = text.replace("：", ":")
            m = re.match(r"(高|中|低)\s*[:：]\s*(.+)", text)
            if m:
                rel_zh, summ = m.groups()
            else:
                rel_zh, summ = "中", text
            rel_map = {"高":"high", "中":"medium", "低":"low"}
            relevance = rel_map.get(rel_zh, "medium")
            return summ[:120].strip(), relevance
        except Exception as e:
            print(f"[{attempt+1}/3] Ark 调用失败: {e}")
            time.sleep(2 + random.uniform(0,2))
    return None, None

for src, url in URLS.items():
    try:
        md = requests.get(url, timeout=20).text
        for title, link in pat.findall(md)[:5]:
            article = fetch_article_text(link)
            if not article:
                continue
            summary, rel = gen_summary(title, article)
            if not summary:
                continue
            priority = 1 if rel == "high" else 2 if rel == "medium" else 3
            items.append({
                "title": title.strip(),
                "link": link.strip(),
                "summary": summary,
                "date": today,
                "relevance": rel,
                "priority": priority,
                "source": src
            })
    except Exception as e:
        print(f"[WARN] {src} 抓取失败: {e}")

items.sort(key=lambda x: x["priority"])
out = f"hotnews_smart_{today}.json"
with open(out, "w", encoding="utf-8") as f:
    json.dump(items, f, ensure_ascii=False, indent=2)
print(f"✅ 生成完成，总条数：{len(items)} → {out}")
