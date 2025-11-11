#!/bin/bash
# 监控镜像缓存完成并启动 4o-mini 批量运行
# 功能：
# 1. 监控重试进程是否运行
# 2. 进程结束后，验证所有镜像是否成功缓存
# 3. 如果仍有未缓存的镜像，可以选择继续等待或报告
# 4. 确认完成后，启动 4o-mini 批量运行
#
# 使用方法：
#   ./wait_and_run_4o_mini.sh [选项]
#
# 选项：
#   --skip-wait     跳过等待镜像缓存完成（直接进入验证或启动阶段）
#   --skip-verify   跳过验证镜像缓存状态（直接启动批量运行）
#   -h, --help      显示帮助信息

set -e

# 控制参数
SKIP_WAIT=false
SKIP_VERIFY=false

# 配置
RETRY_LOG="/home/ps/yyf/swebench_cache/logs/swebench_retry_20251111_050224.log"
UNCACHED_IMAGES_FILE="/home/ps/yyf/swebench_cache/logs/uncached_images.txt"
IMAGE_LIST_FILE="/tmp/swebench_verified_images.txt"
REGISTRY="localhost:5000"
CHECK_INTERVAL=60  # 检查间隔（秒）
MAX_WAIT_HOURS=3   # 最大等待时间（小时）
OUTPUT_DIR="/home/ps/yyf/mini-swe-agent/results/4o-mini-verified-$(date +%Y%m%d_%H%M%S)"

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

log() {
    echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} $1"
}

warn() {
    echo -e "${YELLOW}[$(date +'%Y-%m-%d %H:%M:%S')] WARNING:${NC} $1"
}

error() {
    echo -e "${RED}[$(date +'%Y-%m-%d %H:%M:%S')] ERROR:${NC} $1"
}

info() {
    echo -e "${BLUE}[$(date +'%Y-%m-%d %H:%M:%S')] INFO:${NC} $1"
}

# 显示帮助信息
show_help() {
    cat << EOF
镜像缓存监控与 4o-mini 批量运行启动脚本

使用方法:
    $0 [选项]

选项:
    --skip-wait     跳过等待镜像缓存完成（直接进入验证或启动阶段）
    --skip-verify   跳过验证镜像缓存状态（直接启动批量运行）
    -h, --help      显示此帮助信息

示例:
    $0                    # 正常流程：等待并验证缓存
    $0 --skip-wait        # 跳过等待，直接验证缓存
    $0 --skip-verify      # 跳过等待和验证，直接启动批量运行
    $0 --skip-wait --skip-verify  # 完全跳过，直接启动批量运行

EOF
}

# 解析命令行参数
parse_args() {
    while [[ $# -gt 0 ]]; do
        case $1 in
            --skip-wait)
                SKIP_WAIT=true
                shift
                ;;
            --skip-verify)
                SKIP_VERIFY=true
                shift
                ;;
            -h|--help)
                show_help
                exit 0
                ;;
            *)
                error "未知参数: $1"
                echo ""
                show_help
                exit 1
                ;;
        esac
    done
}

# 检查重试进程是否还在运行
check_retry_process() {
    if pgrep -f "retry_uncached_images.py" > /dev/null; then
        return 0  # 进程正在运行
    else
        return 1  # 进程已结束
    fi
}

# 检查私有仓库是否可访问
check_registry() {
    if curl -s -f --max-time 5 "http://${REGISTRY}/v2/" > /dev/null 2>&1; then
        return 0
    else
        return 1
    fi
}

# 获取已缓存的镜像数量
get_cached_count() {
    local result=$(curl -s "http://${REGISTRY}/v2/_catalog?n=1000" 2>/dev/null)
    if [ $? -eq 0 ]; then
        echo "$result" | python3 -c "import sys, json; data=json.load(sys.stdin); print(len([r for r in data.get('repositories', []) if 'swebench' in r]))" 2>/dev/null || echo "0"
    else
        echo "0"
    fi
}

# 检查未缓存的镜像数量
check_uncached_images() {
    if [ ! -f "$UNCACHED_IMAGES_FILE" ]; then
        # 如果文件不存在，运行 find_uncached_images.py 来检查
        info "未缓存镜像列表文件不存在，正在检查..."
        cd /home/ps/yyf/swebench_cache
        conda run -n mini-swe-agent python3 scripts/find_uncached_images.py > /dev/null 2>&1
    fi
    
    if [ -f "$UNCACHED_IMAGES_FILE" ]; then
        local count=$(wc -l < "$UNCACHED_IMAGES_FILE" 2>/dev/null || echo "0")
        echo "$count"
    else
        echo "0"
    fi
}

# 验证所有镜像是否成功缓存
verify_all_cached() {
    info "验证镜像缓存状态..."
    
    # 检查私有仓库
    if ! check_registry; then
        error "无法访问私有仓库 ${REGISTRY}"
        return 1
    fi
    
    # 获取总镜像数
    if [ ! -f "$IMAGE_LIST_FILE" ]; then
        error "镜像列表文件不存在: $IMAGE_LIST_FILE"
        return 1
    fi
    
    local total=$(wc -l < "$IMAGE_LIST_FILE")
    local cached=$(get_cached_count)
    
    # 重新检查未缓存的镜像（确保数据是最新的）
    info "正在重新检查未缓存的镜像..."
    cd /home/ps/yyf/swebench_cache
    conda run -n mini-swe-agent python3 scripts/find_uncached_images.py > /tmp/find_uncached_output.log 2>&1
    
    local uncached=0
    if [ -f "$UNCACHED_IMAGES_FILE" ]; then
        uncached=$(wc -l < "$UNCACHED_IMAGES_FILE" 2>/dev/null || echo "0")
    fi
    
    info "总镜像数: $total"
    info "已缓存: $cached"
    info "未缓存: $uncached"
    
    if [ "$uncached" -eq 0 ] || [ ! -f "$UNCACHED_IMAGES_FILE" ]; then
        log "✓ 所有镜像都已成功缓存！"
        return 0
    else
        warn "仍有 $uncached 个镜像未缓存"
        if [ -f "$UNCACHED_IMAGES_FILE" ]; then
            warn "未缓存的镜像列表:"
            head -10 "$UNCACHED_IMAGES_FILE" | while read img; do
                warn "  - $img"
            done
            if [ $uncached -gt 10 ]; then
                warn "  ... 还有 $((uncached - 10)) 个镜像"
            fi
        fi
        return 1
    fi
}

# 等待镜像缓存完成
wait_for_cache_completion() {
    # 首先检查进程是否还在运行
    if ! check_retry_process; then
        log "重试进程已结束，跳过等待，直接验证缓存状态..."
        # 验证所有镜像是否成功缓存
        if verify_all_cached; then
            return 0
        else
            return 1
        fi
    fi
    
    # 进程还在运行，开始监控
    local start_time=$(date +%s)
    local max_wait_seconds=$((MAX_WAIT_HOURS * 3600))
    local last_log_line=0
    
    log "开始监控镜像缓存进程..."
    log "最大等待时间: ${MAX_WAIT_HOURS} 小时"
    log "检查间隔: ${CHECK_INTERVAL} 秒"
    echo ""
    
    while true; do
        local current_time=$(date +%s)
        local elapsed=$((current_time - start_time))
        
        # 检查是否超过最大等待时间
        if [ $elapsed -gt $max_wait_seconds ]; then
            warn "已达到最大等待时间 (${MAX_WAIT_HOURS} 小时)"
            break
        fi
        
        # 检查进程是否还在运行
        if check_retry_process; then
            # 进程还在运行，显示最新日志
            if [ -f "$RETRY_LOG" ]; then
                local current_lines=$(wc -l < "$RETRY_LOG" 2>/dev/null || echo "0")
                if [ $current_lines -gt $last_log_line ]; then
                    tail -n +$((last_log_line + 1)) "$RETRY_LOG" | tail -3
                    last_log_line=$current_lines
                fi
            fi
            
            # 显示进度
            local cached=$(get_cached_count)
            local elapsed_min=$((elapsed / 60))
            info "进程运行中... 已缓存: $cached 个镜像 | 已等待: ${elapsed_min} 分钟"
        else
            # 进程已结束
            log "重试进程已结束"
            break
        fi
        
        sleep $CHECK_INTERVAL
    done
    
    echo ""
    log "进程监控结束，开始验证缓存状态..."
    
    # 验证所有镜像是否成功缓存
    if verify_all_cached; then
        return 0
    else
        return 1
    fi
}

# 启动 4o-mini 批量运行
start_4o_mini_batch() {
    log "准备启动 4o-mini 批量运行..."
    
    # 检查 .env 文件
    local env_file="$HOME/.config/mini-swe-agent/.env"
    if [ ! -f "$env_file" ]; then
        error ".env 文件不存在: $env_file"
        return 1
    fi
    
    if ! grep -q "AIZEX_API_KEY" "$env_file"; then
        warn ".env 文件中未找到 AIZEX_API_KEY"
    else
        log "✓ 找到 AIZEX_API_KEY 配置"
    fi
    
    # 检查配置文件
    local config_file="/home/ps/yyf/mini-swe-agent/src/minisweagent/config/extra/swebench.yaml"
    if [ ! -f "$config_file" ]; then
        error "配置文件不存在: $config_file"
        return 1
    fi
    
    # 检查 logprobs 配置
    if ! grep -q "logprobs: true" "$config_file"; then
        warn "配置文件中未找到 logprobs: true"
        warn "请检查配置文件: $config_file"
    else
        log "✓ 确认 logprobs 配置已启用"
    fi
    
    # 检查 litellm_model_registry 路径
    local registry_path=$(grep "litellm_model_registry:" "$config_file" | awk '{print $2}' | tr -d '"')
    if [ -n "$registry_path" ] && [ ! -f "$registry_path" ]; then
        warn "litellm_model_registry 路径不存在: $registry_path"
        warn "将使用默认路径: /home/ps/yyf/mini-swe-agent/custom_model_registry.json"
        # 检查默认路径
        if [ -f "/home/ps/yyf/mini-swe-agent/custom_model_registry.json" ]; then
            log "✓ 找到默认的 custom_model_registry.json"
        fi
    fi
    
    # 创建输出目录
    mkdir -p "$OUTPUT_DIR"
    log "输出目录: $OUTPUT_DIR"
    
    # 切换到 mini-swe-agent 目录
    cd /home/ps/yyf/mini-swe-agent
    
    # 启动批量运行
    log "启动 4o-mini 批量运行..."
    log "命令: mini-extra swebench --model gpt-4o-mini --subset verified --split test --workers 2"
    echo ""
    
    # 使用 nohup 在后台运行，并保存日志
    # 直接使用 conda run，避免 conda activate 的问题
    # 使用 python -m 方式调用，确保使用 conda 环境中的包
    nohup bash -c "
        cd /home/ps/yyf/mini-swe-agent
        conda run -n mini-swe-agent python -m minisweagent.run.mini_extra swebench \\
            --model gpt-4o-mini \\
            --subset verified \\
            --split test \\
            --workers 2 \\
            --output \"$OUTPUT_DIR\" \\
            --config src/minisweagent/config/extra/swebench.yaml
    " > "$OUTPUT_DIR/run.log" 2>&1 &
    
    local bash_pid=$!
    log "批量运行已启动，bash PID: $bash_pid"
    log "日志文件: $OUTPUT_DIR/run.log"
    log "输出目录: $OUTPUT_DIR"
    
    # 等待几秒，让进程启动
    sleep 3
    
    # 查找实际的 python 进程 PID（mini_extra 进程）
    local python_pid=$(ps aux | grep "python -m minisweagent.run.mini_extra swebench" | grep "$OUTPUT_DIR" | grep -v grep | awk '{print $2}' | head -1)
    
    if [ -n "$python_pid" ]; then
        log "找到实际的 python 进程 PID: $python_pid"
        echo "$python_pid" > "$OUTPUT_DIR/pid.txt"
        echo "$bash_pid" > "$OUTPUT_DIR/bash_pid.txt"
    else
        warn "未能找到实际的 python 进程，保存 bash PID: $bash_pid"
        echo "$bash_pid" > "$OUTPUT_DIR/pid.txt"
        warn "提示：可以使用以下命令查找实际进程："
        warn "  ps aux | grep 'mini_extra swebench' | grep '$OUTPUT_DIR'"
    fi
    
    return 0
}

# 主函数
main() {
    echo "============================================================"
    echo "镜像缓存监控与 4o-mini 批量运行启动脚本"
    echo "============================================================"
    echo ""
    
    # 显示当前配置
    if [ "$SKIP_WAIT" = true ]; then
        info "已启用: 跳过等待镜像缓存完成"
    fi
    if [ "$SKIP_VERIFY" = true ]; then
        info "已启用: 跳过验证镜像缓存状态"
    fi
    echo ""
    
    # 步骤1: 等待镜像缓存完成（如果未跳过）
    if [ "$SKIP_WAIT" = false ]; then
        log "步骤 1: 等待镜像缓存完成"
        if wait_for_cache_completion; then
            log "✓ 镜像缓存验证通过"
        else
            warn "⚠️  镜像缓存验证未完全通过！"
            warn "重试进程已结束，但仍有部分镜像未成功缓存"
            echo ""
            warn "可能的原因："
            warn "  1. 部分镜像在 Docker Hub 上不存在"
            warn "  2. 网络问题导致拉取失败"
            warn "  3. 镜像名称格式问题"
            echo ""
            warn "你可以选择："
            warn "  1. 继续运行（使用已缓存的镜像，未缓存的会从 Docker Hub 拉取）"
            warn "  2. 取消并手动检查问题"
            echo ""
            read -p "是否继续启动批量运行？(y/n) " -n 1 -r
            echo
            if [[ ! $REPLY =~ ^[Yy]$ ]]; then
                error "用户取消操作"
                error "请检查日志文件: $RETRY_LOG"
                error "未缓存镜像列表: $UNCACHED_IMAGES_FILE"
                exit 1
            fi
            warn "继续执行，但请注意未缓存的镜像可能会从 Docker Hub 拉取（较慢）"
        fi
        echo ""
    else
        log "步骤 1: 跳过等待镜像缓存完成"
        # 如果跳过等待但未跳过验证，则只进行验证
        if [ "$SKIP_VERIFY" = false ]; then
            log "进行镜像缓存验证..."
            if verify_all_cached; then
                log "✓ 镜像缓存验证通过"
            else
                warn "⚠️  镜像缓存验证未完全通过！"
                warn "仍有部分镜像未成功缓存"
                echo ""
                warn "可能的原因："
                warn "  1. 部分镜像在 Docker Hub 上不存在"
                warn "  2. 网络问题导致拉取失败"
                warn "  3. 镜像名称格式问题"
                echo ""
                warn "你可以选择："
                warn "  1. 继续运行（使用已缓存的镜像，未缓存的会从 Docker Hub 拉取）"
                warn "  2. 取消并手动检查问题"
                echo ""
                read -p "是否继续启动批量运行？(y/n) " -n 1 -r
                echo
                if [[ ! $REPLY =~ ^[Yy]$ ]]; then
                    error "用户取消操作"
                    error "请检查日志文件: $RETRY_LOG"
                    error "未缓存镜像列表: $UNCACHED_IMAGES_FILE"
                    exit 1
                fi
                warn "继续执行，但请注意未缓存的镜像可能会从 Docker Hub 拉取（较慢）"
            fi
            echo ""
        else
            log "同时跳过验证，直接启动批量运行"
            echo ""
        fi
    fi
    
    # 步骤2: 启动 4o-mini 批量运行
    log "步骤 2: 启动 4o-mini 批量运行"
    if start_4o_mini_batch; then
        log "✓ 批量运行已启动"
        echo ""
        echo "============================================================"
        log "监控命令: tail -f $OUTPUT_DIR/minisweagent.log"
        log "检查进程: ps aux | grep mini-extra | grep $OUTPUT_DIR"
        log "停止运行: kill \$(cat $OUTPUT_DIR/pid.txt)"
        if [ -f "$OUTPUT_DIR/bash_pid.txt" ]; then
            log "注意: pid.txt 中保存的是实际的 python 进程 PID"
        fi
        echo "============================================================"
    else
        error "批量运行启动失败"
        exit 1
    fi
}

# 解析命令行参数
parse_args "$@"

# 运行主函数
main

