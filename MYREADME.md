# 实验记录

## litellm API Key 读取机制

### 问题描述

在执行以下命令时：

```bash
mini-extra swebench-single \
    --subset verified \
    --split test \
    --model gpt-4o-mini \
    -i sympy__sympy-15599
```

需要了解 litellm 如何根据配置文件中的 `custom_llm_provider` 字段来读取对应的 API_KEY。

### 机制说明

1. **配置文件位置**：`mini-swe-agent/src/minisweagent/config/extra/swebench.yaml`

2. **关键配置字段**：在 `model.model_kwargs` 中设置 `custom_llm_provider`，例如：

   ```yaml
   model:
     model_kwargs:
       custom_llm_provider: "openai"
   ```

3. **API Key 读取规则**：
   - litellm 会根据 `custom_llm_provider` 的值，自动从环境变量中查找对应的 API_KEY
   - 环境变量命名规则：`{PROVIDER}_API_KEY`（全大写）
   - 例如：`custom_llm_provider: "openai"` → 读取 `OPENAI_API_KEY`
   - 例如：`custom_llm_provider: "anthropic"` → 读取 `ANTHROPIC_API_KEY`

4. **环境变量来源**：
   - 全局配置文件：`~/.config/mini-swe-agent/.env`
   - 该文件在 mini-swe-agent 启动时自动加载（见 `minisweagent/__init__.py`）
   - 也可以通过系统环境变量设置（优先级更高）

### 示例

如果配置文件中设置了：

```yaml
model:
  model_kwargs:
    custom_llm_provider: "openai"
```

那么需要在 `~/.config/mini-swe-agent/.env` 文件中设置：

```bash
OPENAI_API_KEY=sk-your-key-here
```

### 注意事项

- 确保 `.env` 文件中的 API_KEY 变量名与 `custom_llm_provider` 的值匹配
- 变量名必须全大写，格式为 `{PROVIDER}_API_KEY`
- 如果使用自定义的 API base URL（如 `api_base: "https://aizex.top/v1"`），仍然需要设置正确的 API_KEY

## 常用运行命令

### 单个任务运行

运行单个 SWE-Bench 任务：

```bash
mini-extra swebench-single \
    --subset verified \
    --split test \
    --model gpt-4o-mini \
    -i sympy__sympy-15599
```

或者使用脚本：

```bash
cd /home/ps/yyf/mini-swe-agent
bash scripts/4o-mini-verified-single.sh
```

### 批量运行（带镜像缓存监控）

使用 `wait_and_run_4o_mini.sh` 脚本可以：

1. 监控镜像缓存重试进程
2. 等待所有镜像缓存完成
3. 自动启动批量运行

**基本用法**：

```bash
cd /home/ps/yyf/mini-swe-agent
bash scripts/wait_and_run_4o_mini.sh
```

**脚本功能**：

- 监控重试进程是否运行
- 验证所有镜像是否成功缓存到私有仓库（`localhost:5000`）
- 如果仍有未缓存的镜像，会提示是否继续
- 确认完成后，启动 4o-mini 批量运行 swebench

**控制参数**：

- `--skip-wait`：跳过等待镜像缓存完成（直接进入验证或启动阶段）
- `--skip-verify`：跳过验证镜像缓存状态（直接启动批量运行）
- `-h, --help`：显示帮助信息

**使用示例**：

```bash
# 正常流程：等待并验证缓存
bash scripts/wait_and_run_4o_mini.sh

# 跳过等待，直接验证缓存
bash scripts/wait_and_run_4o_mini.sh --skip-wait

# 跳过等待和验证，直接启动批量运行（推荐，当你知道镜像已缓存完毕时）
bash scripts/wait_and_run_4o_mini.sh --skip-wait --skip-verify

# 只跳过验证，但仍会等待缓存完成
bash scripts/wait_and_run_4o_mini.sh --skip-verify
```

**批量运行参数**：

- 模型：`gpt-4o-mini`
- 子集：`verified`
- 数据集：`test`
- 工作进程数：`2`
- 输出目录：`results/4o-mini-verified-YYYYMMDD_HHMMSS/`

**监控命令**：

```bash
# 查看运行日志（注意：实际日志在 minisweagent.log，不是 run.log）
tail -f results/4o-mini-verified-*/minisweagent.log

# 检查进程
ps aux | grep mini-extra | grep results/4o-mini-verified-*

# 停止运行（pid.txt 中保存的是实际的 python 进程 PID）
kill $(cat results/4o-mini-verified-*/pid.txt)
```

**关于 PID 文件**：

- `pid.txt`：保存实际的 `python -m minisweagent.run.mini_extra` 进程 PID（用于停止进程）
- `bash_pid.txt`：保存初始的 bash 进程 PID（如果存在，用于参考）

**注意**：脚本会自动查找并保存实际的 python 进程 PID，而不是 bash 进程 PID，这样可以确保 `kill $(cat pid.txt)` 能够正确停止运行中的进程。

**管理进程的辅助脚本**：

```bash
# 查找所有 mini-swe-agent 相关进程
bash scripts/find_mini_swe_agent_processes.sh

# 更新所有结果目录中的 pid.txt 文件（修复旧的 PID 文件）
bash scripts/update_pid_files.sh
```

这些脚本可以帮助你：
- 查看所有正在运行的 mini-swe-agent 进程及其资源占用
- 检查 pid.txt 文件是否正确
- 更新旧的 pid.txt 文件以匹配实际运行的进程

**输出文件结构**：

```
results/4o-mini-verified-YYYYMMDD_HHMMSS/
├── minisweagent.log          # 主日志文件
├── run.log                    # nohup 启动日志（通常为空）
├── pid.txt                    # 进程 ID
├── preds.json                 # 所有实例的预测结果汇总
└── {instance_id}/             # 每个实例的子目录
    └── {instance_id}.traj.json  # 轨迹文件（包含完整的 agent 运行轨迹）
```

**轨迹文件路径**：

轨迹文件（`.traj.json`）保存在每个实例的子目录中：
- 路径格式：`results/4o-mini-verified-YYYYMMDD_HHMMSS/{instance_id}/{instance_id}.traj.json`
- 例如：`results/4o-mini-verified-20251111_231355/astropy__astropy-12907/astropy__astropy-12907.traj.json`

轨迹文件包含：
- 完整的 agent 运行消息历史（messages）
- 退出状态（exit_status）
- 提交结果（submission）
- 模型统计信息（成本、API 调用次数等）
- 配置信息

**注意**：agent 的实际日志输出到 `minisweagent.log` 文件，而不是 `run.log`。`run.log` 只包含 nohup 的启动信息。

### 直接批量运行（不监控镜像缓存）

如果镜像已经缓存完成，可以直接运行：

```bash
cd /home/ps/yyf/mini-swe-agent
mini-extra swebench \
    --model gpt-4o-mini \
    --subset verified \
    --split test \
    --workers 2 \
    --config src/minisweagent/config/extra/swebench.yaml
```
