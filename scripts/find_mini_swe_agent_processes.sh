#!/bin/bash
# 查找所有属于 mini-swe-agent 的进程

echo "============================================================"
echo "查找 mini-swe-agent 相关进程"
echo "============================================================"
echo ""

# 查找所有相关进程
echo "【所有相关进程】"
ps aux | grep -E "(mini_extra|minisweagent)" | grep -v grep | grep -v "$0" | while read line; do
    pid=$(echo "$line" | awk '{print $2}')
    cpu=$(echo "$line" | awk '{print $3}')
    mem=$(echo "$line" | awk '{print $4}')
    rss=$(echo "$line" | awk '{print $6}')
    cmd=$(echo "$line" | awk '{for(i=11;i<=NF;i++) printf "%s ", $i; print ""}')
    output_dir=$(echo "$cmd" | grep -o "results/[^ ]*" | head -1)
    
    printf "PID: %-8s CPU: %-6s MEM: %-6s RSS: %-10s\n" "$pid" "${cpu}%" "${mem}%" "$(numfmt --to=iec-i --suffix=B $((rss*1024)) 2>/dev/null || echo "${rss}KB")"
    echo "  输出目录: ${output_dir:-未知}"
    echo "  命令: $cmd"
    echo ""
done

echo ""
echo "【资源统计】"
total_cpu=$(ps aux | grep -E "(mini_extra|minisweagent)" | grep -v grep | grep -v "$0" | awk '{sum+=$3} END {printf "%.1f", sum}')
total_mem=$(ps aux | grep -E "(mini_extra|minisweagent)" | grep -v grep | grep -v "$0" | awk '{sum+=$4} END {printf "%.1f", sum}')
total_rss=$(ps aux | grep -E "(mini_extra|minisweagent)" | grep -v grep | grep -v "$0" | awk '{sum+=$6} END {print sum}')
count=$(ps aux | grep -E "(mini_extra|minisweagent)" | grep -v grep | grep -v "$0" | wc -l)

echo "总进程数: $count"
echo "总 CPU 使用率: ${total_cpu}%"
echo "总内存使用率: ${total_mem}%"
if [ -n "$total_rss" ] && [ "$total_rss" != "0" ]; then
    total_rss_mb=$((total_rss / 1024))
    total_rss_gb=$(echo "scale=2; $total_rss_mb / 1024" | bc)
    echo "总内存占用: ${total_rss_mb} MB (${total_rss_gb} GB)"
fi

echo ""
echo "【按输出目录分组】"
ps aux | grep -E "(mini_extra|minisweagent)" | grep -v grep | grep -v "$0" | while read line; do
    pid=$(echo "$line" | awk '{print $2}')
    cmd=$(echo "$line" | awk '{for(i=11;i<=NF;i++) printf "%s ", $i; print ""}')
    output_dir=$(echo "$cmd" | grep -o "results/[^ ]*" | head -1)
    
    if [ -n "$output_dir" ]; then
        echo "输出目录: $output_dir"
        echo "  PID: $pid"
        
        # 检查是否有对应的 pid.txt
        if [ -f "/home/ps/yyf/mini-swe-agent/$output_dir/pid.txt" ]; then
            saved_pid=$(cat "/home/ps/yyf/mini-swe-agent/$output_dir/pid.txt" 2>/dev/null | head -1)
            if [ "$saved_pid" = "$pid" ]; then
                echo "  ✓ pid.txt 匹配"
            else
                echo "  ⚠ pid.txt 不匹配 (保存的 PID: $saved_pid)"
            fi
        else
            echo "  ⚠ 未找到 pid.txt"
        fi
        echo ""
    fi
done

echo ""
echo "【停止进程命令】"
echo "要停止所有进程，可以使用："
ps aux | grep -E "(mini_extra|minisweagent)" | grep -v grep | grep -v "$0" | awk '{print $2}' | while read pid; do
    cmd=$(ps -p "$pid" -o cmd --no-headers 2>/dev/null)
    output_dir=$(echo "$cmd" | grep -o "results/[^ ]*" | head -1)
    echo "  kill $pid  # $output_dir"
done

echo ""
echo "或者停止所有："
pids=$(ps aux | grep -E "(mini_extra|minisweagent)" | grep -v grep | grep -v "$0" | awk '{print $2}' | tr '\n' ' ')
echo "  kill $pids"

