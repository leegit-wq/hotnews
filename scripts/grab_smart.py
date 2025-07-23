import requests, re, json, datetime, os, time, random
import feedparser
from bs4 import BeautifulSoup
from openai import OpenAI

client = OpenAI(
    base_url="https://ark.cn-beijing.volces.com/api/v3",
    api_key=os.getenv("ARK_API_KEY")
)

today = datetime.date.today().strftime("%Y-%m-%d")
items = []

# 头条热文源
TOUTIAO_URL = f"https://raw.githubusercontent.com/SnailDev/toutiao-hot-hub/main/archives/{today}.md"
PAT_MD = re.compile(r'\d+\.\s*\[(.+?)\]\((https?://[^)]+)\)')

# 人民网民生新闻 RSS（AnyFeeder 源示例）
PEOPLE_RSS = "https://feed.anyfeeder.com/people/news"
# 澎湃新闻 RSS
THEPAPER_RSS = "https://feed.anyfeeder.com/thepaper/news"
# 腾讯新闻 RSS
QQ_NEWS_RSS = "https://feed.anyfeeder.com/qq/news/china"

def fetch_article_text(url):
    try:
        res = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=10)
        soup = BeautifulSoup(res.text, "html.parser")
        for tag in soup(["script", "style"]):
            tag.decompose()
        text = soup.get_text(separator="\n", strip=True)
        if len(text) < 100 or "请登录" in text:
            return None
        return text[:1000]
    except:
        return None

def gen_summary(title, content):
    if not content:
        return None, None
    prompt = f"""请根据以下新闻标题和正文片段，提取事件的主要内容，用一句话简洁明确地描述清楚“何时、何地、谁、做了什么”。不要进行其它评价词。
格式：高/中/低: 事件描述
标题：{title}
正文：{content[:500]}
"""
    for _ in range(3):
        try:
            rsp = client.chat.completions.create(
                model="ep-20250721132115-4hpdj",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.5,
                max_tokens=120
            )
            out = rsp.choices[0].message.content.strip().replace("：", ":")
            m = re.match(r"(高|中|低)\s*[:：]\s*(.+)", out)
            rel_zh, summ = m.groups() if m else ("中", out)
            rel = {"高":"high","中":"medium","低":"low"}[rel_zh]
            return summ[:120].strip(), rel
        except Exception as e:
            print("Ark 调用错误:", e)
            time.sleep(1)
    return None, None

def process_md(source, url):
    try:
        md = requests.get(url, timeout=10).text
        for title, link in PAT_MD.findall(md)[:5]:
            content = fetch_article_text(link)
            if not content:
                continue
            summary, rel = gen_summary(title, content)
            if summary:
                items.append({
                    "source": source, "title": title, "link": link,
                    "summary": summary, "date": today,
                    "relevance": rel, "priority": 1 if rel=="high" else 2 if rel=="medium" else 3
                })
    except Exception as e:
        print(source, "失败:", e)

def process_rss(source, url):
    try:
        feed = feedparser.parse(url)
        for entry in feed.entries[:5]:
            title, link = entry.title, entry.link
            content = fetch_article_text(link)
            if not content:
                continue
            summary, rel = gen_summary(title, content)
            if summary:
                items.append({
                    "source": source, "title": title, "link": link,
                    "summary": summary, "date": entry.get("published", today)[:10],
                    "relevance": rel, "priority": 1 if rel=="high" else 2 if rel=="medium" else 3
                })
    except Exception as e:
        print(source, "RSS 失败:", e)

# 执行各平台抓取
process_md("头条", TOUTIAO_URL)
process_rss("人民网", PEOPLE_RSS)
process_rss("澎湃新闻", THEPAPER_RSS)
process_rss("腾讯新闻", QQ_NEWS_RSS)

# 输出 JSON
items.sort(key=lambda x: x["priority"])
out = f"hotnews_smart_{today}.json"
with open(out, "w", encoding="utf-8") as f:
    json.dump(items, f, ensure_ascii=False, indent=2)
print("✅ 完成，总条数:", len(items))