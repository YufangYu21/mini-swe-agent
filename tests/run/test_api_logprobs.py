import os

import requests


def test_api_logprobs_summary():
    """使用 requests 库发送请求并总结 logprobs 数据"""
    print("=== 简化 API Log Probs 测试 ===")

    # 1. 配置和检查 API 密钥
    api_key = os.getenv("AIZEX_API_KEY")
    if not api_key:
        print("❌ 错误：请设置 AIZEX_API_KEY 环境变量")
        return

    # 2. API 端点和参数 (采用标准的 OpenAI 兼容格式)
    API_BASE = "https://aizex.top/v1"
    MODEL_NAME = "gemini-2.5-pro"  # 目标模型
    # MODEL_NAME = "gpt-4o-mini"

    URL = f"{API_BASE}/chat/completions"

    HEADERS = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    # 标准 OpenAI 兼容格式的 Payload
    PAYLOAD = {
        "model": MODEL_NAME,
        "messages": [{"role": "user", "content": "say test and nothing else"}],
        "temperature": 0.0,
        "logprobs": True,  # 启用 Log Probs (布尔型)
        "top_logprobs": 5,  # 返回 Top 5 替代项 (数字型)
        # "responseLogprobs": True,  # (❌ Gemini 风格，且大小写可能不匹配)
        # "logprobs": 20,            # (❌ Gemini 风格，标准 API 中，这个位置应该是布尔值)
        # "response_logprobs": True,
        # "logprobs": 20,
    }

    print(f"发送请求到: {URL}")
    print(f"使用的模型: {MODEL_NAME}")

    # 3. 发送请求
    try:
        response = requests.post(URL, headers=HEADERS, json=PAYLOAD, timeout=60)
        response.raise_for_status()
        raw_response = response.json()

        print("✅ API 请求成功")
        print(raw_response)

        # 4. 总结 Log Probs 数据

        # 检查 Log Probs 路径：choices[0].logprobs.content
        logprobs_root = raw_response["choices"][0].get("logprobs")

        if logprobs_root and logprobs_root.get("content"):
            logprobs_data = logprobs_root["content"]

            print("✅ 响应中包含 Log Probs 数据")

            choice = raw_response["choices"][0]
            content = choice["message"]["content"]

            # 总结信息
            total_tokens = len(logprobs_data)
            first_token_data = logprobs_data[0]

            first_token = first_token_data.get("token", "")
            first_logprob = first_token_data.get("logprob")
            top_n = len(first_token_data.get("top_logprobs", []))

            print("\n--- Log Probs 总结 ---")
            print(f"生成的内容: '{content.strip()}'")
            print(f"总计包含 Log Probs 的 Token 数量: {total_tokens}")
            print(f"每个 Token 返回 Top N 数量: {top_n}")
            print(f"第一个 Token ('{first_token.strip()}') 的对数概率: {first_logprob:.4f}")

        else:
            print("❌ 响应成功，但未找到 Log Probs 数据。请检查模型或服务支持。")

    except requests.exceptions.HTTPError as e:
        print(f"❌ HTTP 请求错误: {e}")
        if response.text:
            print(f"状态码: {response.status_code}")
            print(f"内容: {response.text}")
    except requests.exceptions.RequestException as e:
        print(f"❌ 请求发生错误: {e}")
    except Exception as e:
        print(f"❌ 发生了未知错误: {e}")


if __name__ == "__main__":
    test_api_logprobs_summary()
