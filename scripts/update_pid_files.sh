#!/bin/bash
# 更新所有结果目录中的 pid.txt 文件，保存正确的 python 进程 PID

echo "============================================================"
echo "更新 pid.txt 文件"
echo "============================================================"
echo ""

results_dir="/home/ps/yyf/mini-swe-agent/results"
updated=0
not_found=0

# 遍历所有结果目录
for result_dir in "$results_dir"/4o-mini-verified-*/; do
    if [ ! -d "$result_dir" ]; then
        continue
    fi
    
    # 从目录名中提取输出路径（相对路径）
    output_path=$(basename "$result_dir")
    full_output_path="$results_dir/$output_path"
    
    # 查找该输出目录对应的实际 python 进程（排除 conda run 进程）
    python_pid=$(ps aux | grep "python -m minisweagent.run.mini_extra swebench" | grep "$full_output_path" | grep -v "conda run" | grep -v grep | awk '{print $2}' | head -1)
    
    if [ -n "$python_pid" ]; then
        # 找到进程，更新 pid.txt
        echo "$python_pid" > "$result_dir/pid.txt"
        echo "✓ 更新: $output_path -> PID: $python_pid"
        updated=$((updated + 1))
    else
        # 未找到进程
        echo "⚠ 未找到进程: $output_path"
        not_found=$((not_found + 1))
    fi
done

echo ""
echo "============================================================"
echo "更新完成: $updated 个文件已更新, $not_found 个目录未找到进程"
echo "============================================================"

