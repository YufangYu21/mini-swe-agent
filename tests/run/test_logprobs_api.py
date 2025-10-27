#!/usr/bin/env python3
"""测试logprobs参数对响应的影响"""

import json
import os
from pathlib import Path

from minisweagent.models import get_model


def test_with_logprobs():
    """测试带logprobs参数的响应"""
    print("=== 测试带logprobs参数的响应 ===")

    config_with_logprobs = {
        "model_name": "gpt-4o-mini",
        "model_kwargs": {
            "temperature": 0.0,
            "drop_params": True,
            "custom_llm_provider": "openai",
            "api_base": "https://aizex.top/v1",
            "logprobs": True,
            "top_logprobs": 20,
        },
    }

    model = get_model(config=config_with_logprobs)

    messages = [{"role": "user", "content": "Hello, please say 'test' and nothing else."}]

    response = model.query(messages)

    print(f"响应内容: {response['content']}")
    print(f"响应键: {list(response.keys())}")

    if "extra" in response and "response" in response["extra"]:
        raw_response = response["extra"]["response"]
        print(f"原始响应键: {list(raw_response.keys())}")

        if "choices" in raw_response and len(raw_response["choices"]) > 0:
            choice = raw_response["choices"][0]
            print(f"Choice键: {list(choice.keys())}")

            if "logprobs" in choice:
                logprobs = choice["logprobs"]
                print(f"Logprobs键: {list(logprobs.keys())}")
                print(f"Logprobs内容: {json.dumps(logprobs, indent=2)}")
            else:
                print("未找到logprobs字段")
        else:
            print("未找到choices字段")
    else:
        print("未找到extra.response字段")

    return response


def test_without_logprobs():
    """测试不带logprobs参数的响应"""
    print("\n=== 测试不带logprobs参数的响应 ===")

    config_without_logprobs = {
        "model_name": "gpt-4o-mini",
        "model_kwargs": {
            "temperature": 0.0,
            "drop_params": True,
            "custom_llm_provider": "openai",
            "api_base": "https://aizex.top/v1",
            # 不包含logprobs参数
        },
    }

    model = get_model(config=config_without_logprobs)

    messages = [{"role": "user", "content": "Hello, please say 'test' and nothing else."}]

    response = model.query(messages)

    print(f"响应内容: {response['content']}")
    print(f"响应键: {list(response.keys())}")

    if "extra" in response and "response" in response["extra"]:
        raw_response = response["extra"]["response"]
        print(f"原始响应键: {list(raw_response.keys())}")

        if "choices" in raw_response and len(raw_response["choices"]) > 0:
            choice = raw_response["choices"][0]
            print(f"Choice键: {list(choice.keys())}")

            if "logprobs" in choice:
                print("意外：找到了logprobs字段")
            else:
                print("未找到logprobs字段（符合预期）")
        else:
            print("未找到choices字段")
    else:
        print("未找到extra.response字段")

    return response


def compare_responses(response_with, response_without):
    """比较两个响应的差异"""
    print("\n=== 响应差异比较 ===")

    # 比较响应内容
    print(f"内容相同: {response_with['content'] == response_without['content']}")

    # 比较extra字段
    if "extra" in response_with and "extra" in response_without:
        extra_with = response_with["extra"]
        extra_without = response_without["extra"]

        print(f"Extra字段键相同: {set(extra_with.keys()) == set(extra_without.keys())}")

        if "response" in extra_with and "response" in extra_without:
            raw_with = extra_with["response"]
            raw_without = extra_without["response"]

            print(f"原始响应键相同: {set(raw_with.keys()) == set(raw_without.keys())}")

            if "choices" in raw_with and "choices" in raw_without:
                choice_with = raw_with["choices"][0]
                choice_without = raw_without["choices"][0]

                print(f"Choice键相同: {set(choice_with.keys()) == set(choice_without.keys())}")

                # 检查logprobs字段
                has_logprobs_with = "logprobs" in choice_with
                has_logprobs_without = "logprobs" in choice_without

                print(f"带logprobs参数有logprobs字段: {has_logprobs_with}")
                print(f"不带logprobs参数有logprobs字段: {has_logprobs_without}")


def main():
    """主函数"""
    # 检查API密钥
    if not os.getenv("AIZEX_API_KEY"):
        print("错误：请设置AIZEX_API_KEY环境变量")
        return

    try:
        # 测试带logprobs参数
        response_with = test_with_logprobs()

        # 测试不带logprobs参数
        response_without = test_without_logprobs()

        # 比较响应
        compare_responses(response_with, response_without)

        # 保存结果到文件
        results = {"with_logprobs": response_with, "without_logprobs": response_without}

        # 确保输出目录存在
        output_dir = Path("tests/test_data")
        output_dir.mkdir(parents=True, exist_ok=True)
        output_file = output_dir / "logprobs_test_results.json"
        output_file.write_text(json.dumps(results, indent=2, ensure_ascii=False))
        print(f"\n结果已保存到: {output_file}")

    except Exception as e:
        print(f"测试过程中出现错误: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    main()
