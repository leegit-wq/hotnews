import requests, re, json, datetime, os, openai, time, random
openai.api_key = os.getenv("OPENAI_API_KEY")

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
    """兜底：用标题前 30-40 个字作为摘要"""
    return (title[:38] + '…') if len(title) > 40 else title

def gen_summary(title):
    prompt = f"请判断以下事件与普通人生活的关联程度（高/中/低），并用一句话总结，用冒号分隔。\n标题：{title}"
    for attempt in range(3):
        try:
            rsp = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=[{"role":"user","content":prompt}],
                temperature=0.6,
                max_tokens=80)
            text = rsp.choices[0].message.content.strip()
            # 统一冒号
            text = text.replace("：", ":")
            m = re.match(r"(高|中|低)\s*[:：]\s*(.+)", text)
            if m:
                rel_zh, summ = m.groups()
            else:      # 若模型没按格式返
                rel_zh, summ = "中", text
            rel_map = {"高":"high", "中":"medium", "低":"low"}
            relevance = rel_map.get(rel_zh, "medium")
            return summ.strip()[:120], relevance
        except Exception as e:
            print(f"[{attempt+1}/3] OpenAI 调用失败: {e}")
            time.sleep(2 + random.uniform(0,2))
    # 三次都失败
    return basic_summary(title), "low"

for src, url in URLS.items():
    try:
        md = requests.get(url, timeout=25).text
        for title, link in pat.findall(md)[:10]:          # 每个平台前 10 条 → 总 50
            summary, rel = gen_summary(title)
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
        print(f"[WARN] {src} 获取失败: {e}")

items.sort(key=lambda x: x["priority"])
out = f"hotnews_smart_{today}.json"
with open(out, "w", encoding="utf-8") as f:
    json.dump(items, f, ensure_ascii=False, indent=2)

print(f"✅ 生成完成，共 {len(items)} 条 → {out}")