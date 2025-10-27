#!/usr/bin/env python3
"""简化的logprobs保存测试"""

import json
import os
import tempfile
from pathlib import Path

from minisweagent.models import get_model
from minisweagent.run.utils.save import save_traj


def test_logprobs_extraction():
    """测试logprobs数据提取功能"""
    print("=== 测试logprobs数据提取功能 ===")

    # 检查API密钥
    if not os.getenv("AIZEX_API_KEY"):
        print("错误：请设置AIZEX_API_KEY环境变量")
        return

    # 创建模型配置（带logprobs）
    config = {
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

    # 创建模型
    model = get_model(config=config)

    # 直接调用模型的query方法
    messages = [{"role": "user", "content": "Please say 'test' and nothing else."}]

    print("发送请求到模型...")
    try:
        response = model.query(messages)
        print("✅ 模型响应成功")
        print(f"响应内容: {response['content']}")

        # 检查响应中是否包含logprobs
        if "extra" in response and "response" in response["extra"]:
            raw_response = response["extra"]["response"]
            if "choices" in raw_response and len(raw_response["choices"]) > 0:
                choice = raw_response["choices"][0]
                if "logprobs" in choice:
                    print("✅ 响应中包含logprobs数据")

                    # 创建模拟的agent messages
                    mock_messages = [
                        {"role": "user", "content": "Please say 'test' and nothing else."},
                        {"role": "assistant", "content": response["content"], "extra": response["extra"]},
                    ]

                    # 测试logprobs提取
                    from minisweagent.run.utils.save import _extract_logprobs_from_messages

                    logprobs_data = _extract_logprobs_from_messages(mock_messages)

                    print(f"✅ 提取到 {len(logprobs_data)} 个logprobs数据")

                    if len(logprobs_data) > 0:
                        first_logprobs = logprobs_data[0]
                        print(f"第一个logprobs消息索引: {first_logprobs['message_index']}")
                        print(f"包含的token数量: {len(first_logprobs['logprobs']['content'])}")

                        # 显示第一个token信息
                        if first_logprobs["logprobs"]["content"]:
                            first_token = first_logprobs["logprobs"]["content"][0]
                            print(f"第一个token: '{first_token['token']}'")
                            print(f"对数概率: {first_token['logprob']}")
                            print(f"Top logprobs数量: {len(first_token['top_logprobs'])}")

                    # 测试保存功能
                    print("\n=== 测试保存功能 ===")
                    with tempfile.TemporaryDirectory() as temp_dir:
                        temp_path = Path(temp_dir)
                        traj_file = temp_path / "test.traj.json"
                        logprobs_file = traj_file.with_suffix(".logprobs.json")

                    # 创建模拟的agent对象
                    class MockAgent:
                        def __init__(self, messages, model):
                            self.messages = messages
                            # 创建一个带有可序列化config的模拟model
                            self.model = type(
                                "MockModel",
                                (),
                                {
                                    "config": {
                                        "model_name": model.config.model_name,
                                        "model_kwargs": model.config.model_kwargs,
                                    },
                                    "cost": model.cost,
                                    "n_calls": model.n_calls,
                                },
                            )()
                            self.config = {}  # 使用空字典而不是对象
                            self.env = type("Env", (), {"config": {}})()  # 使用空字典

                    mock_agent = MockAgent(mock_messages, model)

                    # 保存traj
                    save_traj(mock_agent, traj_file, exit_status="Test", result="test result", print_path=True)

                    # 检查文件
                    if traj_file.exists():
                        print(f"✅ Traj文件已创建: {traj_file}")
                        traj_size = traj_file.stat().st_size
                        print(f"Traj文件大小: {traj_size} bytes")

                    if logprobs_file.exists():
                        print(f"✅ Logprobs文件已创建: {logprobs_file}")
                        logprobs_size = logprobs_file.stat().st_size
                        print(f"Logprobs文件大小: {logprobs_size} bytes")

                        # 读取logprobs文件内容
                        logprobs_content = json.loads(logprobs_file.read_text())
                        print(f"Logprobs文件包含 {logprobs_content['info']['logprobs_count']} 个logprobs数据")
                    else:
                        print("❌ Logprobs文件未创建")
                else:
                    print("❌ 响应中不包含logprobs数据")
            else:
                print("❌ 响应中不包含choices字段")
        else:
            print("❌ 响应中不包含extra字段")

    except Exception as e:
        print(f"❌ 测试过程中出现错误: {e}")
        import traceback

        traceback.print_exc()


def main():
    """主函数"""
    test_logprobs_extraction()


if __name__ == "__main__":
    main()
