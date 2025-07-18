import requests, re, json, datetime, os, time, random
from openai import OpenAI

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

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
import base64
import hmac
import hashlib

def volc_chat(content):
    access_key = os.getenv("VIOCE").split(":")[0]
    secret_key = os.getenv("VIOCE").split(":")[1]
    endpoint = "https://maas-api.ml-platform-cn-beijing.volces.com/api/v1/chat/completions"
    model = "chatglm-130b-r1"  # 或 "chatglm-130b-r3"

    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
        "Authorization": "",  # 火山引擎认证方式稍特殊，略下方说明
    }

    payload = {
        "model": model,
        "messages": [{"role": "user", "content": content}],
        "parameters": {"temperature": 0.7, "max_new_tokens": 80}
    }

    # 用 AccessKey / SecretKey 生成 HMAC-SHA256 签名（简化版本）
    t = int(time.time())
    to_sign = f"{access_key}{t}"
    sign = base64.b64encode(
        hmac.new(secret_key.encode(), to_sign.encode(), digestmod=hashlib.sha256).digest()
    ).decode()

    headers["Authorization"] = f"HMAC-SHA256 Credential={access_key}, Timestamp={t}, Signature={sign}"

    rsp = requests.post(endpoint, json=payload, headers=headers, timeout=15)
    if rsp.status_code == 200:
        try:
            return rsp.json()["choices"][0]["message"]["content"]
        except:
            return ""
    else:
        print("🔥 火山引擎调用失败：", rsp.text)
        return ""

def gen_summary(title):
    prompt = f"请判断以下事件与普通人生活的关联程度（高/中/低），并用一句话总结，用冒号分隔。\n标题：{title}"
    for attempt in range(3):
        text = volc_chat(prompt)
        if not text:
            time.sleep(2 + random.uniform(0, 2))
            continue
        text = text.replace("：", ":")
        m = re.match(r"(高|中|低)\s*[:：]\s*(.+)", text)
        if m:
            rel_zh, summ = m.groups()
        else:
            rel_zh, summ = "中", text
        rel_map = {"高":"high", "中":"medium", "低":"low"}
        relevance = rel_map.get(rel_zh, "medium")
        return summ.strip()[:120], relevance
    return basic_summary(title), "low"


for src, url in URLS.items():
    try:
        md = requests.get(url, timeout=25).text
        for title, link in pat.findall(md)[:10]:
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
