import os
import time
import hmac
import hashlib
import base64
import requests

# 🔐 火山引擎密钥（自动读取 GitHub secrets 方式）
ak_sk = os.getenv("VIOCE", "替换为你的AccessKeyId:SecretAccessKey")
ACCESS_KEY, SECRET_KEY = ak_sk.split(":")

def get_signature(access_key, secret_key):
    t = int(time.time())
    sign_str = f"{access_key}{t}"
    signature = base64.b64encode(
        hmac.new(secret_key.encode(), sign_str.encode(), digestmod=hashlib.sha256).digest()
    ).decode()
    return t, signature

def volc_chat(prompt):
    model = "chatglm-130b-r1"  # 可换成 deepsseek-chat、skychat、chatglm-130b-r3
    url = "https://maas-api.ml-platform-cn-beijing.volces.com/api/v1/chat/completions"
    t, sig = get_signature(ACCESS_KEY, SECRET_KEY)

    headers = {
        "Content-Type": "application/json",
        "Authorization": f'HMAC-SHA256 Credential={ACCESS_KEY}, Timestamp={t}, Signature={sig}'
    }

    payload = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "parameters": {"temperature": 0.6, "max_new_tokens": 100}
    }

    resp = requests.post(url, headers=headers, json=payload, timeout=20)
    if resp.status_code == 200:
        data = resp.json()
        print("✅ 模型返回内容：")
        print(data["choices"][0]["message"]["content"])
    else:
        print(f"❌ 调用失败，状态码：{resp.status_code}")
        print(resp.text)

# 🔍 测试一句热点标题
hot_title = "蔚来发布全新电池回收计划，引发新能源车主关注"
prompt = f"请判断以下事件与普通人生活的关联程度（高/中/低），并用一句话总结，用冒号分隔。\n标题：{hot_title}"
volc_chat(prompt)