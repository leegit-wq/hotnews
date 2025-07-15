import requests, re, json, datetime, os, openai, time
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

def gen_summary(title):
    prompt = f"请判断以下事件与普通人生活的关联程度（高/中/低），并生成一句摘要，用“：”分隔。标题：{title}"
    for _ in range(3):
        try:
            rsp = openai.ChatCompletion.create(
                model="gpt-4o-mini",
                messages=[{"role":"user","content":prompt}],
                temperature=0.7, max_tokens=80)
            text = rsp.choices[0].message.content.strip()
            if "：" in text:
                rel, summ = text.split("：", 1)
            elif ":" in text:
                rel, summ = text.split(":", 1)
            else:
                rel, summ = "中", text
            rel_map = {"高": "high", "中": "medium", "低": "low"}
            relevance = rel_map.get(rel.strip(), "medium")
            return summ.strip()[:120], relevance
        except Exception:
            time.sleep(2)
    return "（生成失败）", "low"

for src, url in URLS.items():
    try:
        md = requests.get(url, timeout=20).text
        for title, link in pat.findall(md)[:10]:
            summary, rel = gen_summary(title)
            priority = 1 if rel == "high" else 2 if rel == "medium" else 3
            items.append({
                "title": title.strip(),
                "link": link.strip(),
                "summary": summary,
                "date": today,
                "relevance": rel,
                "priority": priority
            })
    except Exception as e:
        print(f"[WARN] {src} 获取失败: {e}")

items.sort(key=lambda x: x["priority"])
out = f"hotnews_smart_{today}.json"
with open(out, "w", encoding="utf-8") as f:
    json.dump(items, f, ensure_ascii=False, indent=2)
print(f"✅ Summary 完成，共 {len(items)} 条 → {out}")