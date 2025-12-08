#!/bin/bash

# ==================== 默认值 ====================
ENV="test"
KNOWLEDGE_BASE="all"
NOHUP="true"

# ==================== 参数解析 ====================
while [[ $# -gt 0 ]]; do
    case $1 in
        -e|--env)
            ENV="$2"
            shift 2
            ;;
        -kb|--knowledge-base)
            KNOWLEDGE_BASE="$2"
            shift 2
            ;;
        -nohup|--nohup)
            NOHUP="$2"
            shift 2
            ;;
        -h|--help)
            echo "Usage: $0 [-e|--env ENVIRONMENT] [-kb|--knowledge-base KB] [-nohup|--nohup VALUE]"
            echo ""
            echo "Options:"
            echo "  -e, --env ENVIRONMENT        环境选择: test, uat, prod (默认: test)"
            echo "  -kb, --knowledge-base KB     知识库选择: hea, ssebrain, chembrain, stainless_steel, all (默认: all)"
            echo "  -nohup, --nohup VALUE       是否后台运行: true, false (默认: true)"
            echo "  -h, --help                   显示此帮助信息"
            echo ""
            echo "Examples:"
            echo "  $0                                    # 启动所有知识库服务（测试环境，后台运行）"
            echo "  $0 -e uat                            # 启动所有知识库服务（UAT环境）"
            echo "  $0 -kb hea                           # 只启动HEAkb服务（端口50001）"
            echo "  $0 -kb ssebrain                      # 只启动SSEkb服务（端口50002）"
            echo "  $0 -kb chembrain                    # 只启动POLYMERkb服务（端口50003）"
            echo "  $0 -kb stainless_steel              # 只启动STEELkb服务（端口50004）"
            echo "  $0 -e prod -kb hea                  # 启动HEAkb服务（生产环境）"
            echo "  $0 --nohup false -kb hea           # 以前台方式运行HEAkb服务"
            exit 0
            ;;
        *)
            echo "错误: 未知参数 '$1'"
            echo "使用 '$0 --help' 查看帮助信息"
            exit 1
            ;;
    esac
done

# ==================== 参数验证 ====================
# 验证环境参数
if [[ "$ENV" != "test" && "$ENV" != "uat" && "$ENV" != "prod" ]]; then
    echo "错误: 无效的环境参数 '$ENV'"
    echo "支持的环境: test, uat, prod"
    exit 1
fi

# 验证知识库参数
if [[ "$KNOWLEDGE_BASE" != "hea" && "$KNOWLEDGE_BASE" != "ssebrain" && \
      "$KNOWLEDGE_BASE" != "chembrain" && "$KNOWLEDGE_BASE" != "stainless_steel" && \
      "$KNOWLEDGE_BASE" != "all" ]]; then
    echo "错误: 无效的知识库参数 '$KNOWLEDGE_BASE'"
    echo "支持的知识库: hea, ssebrain, chembrain, stainless_steel, all"
    exit 1
fi

# 验证nohup参数
if [[ "$NOHUP" != "true" && "$NOHUP" != "false" ]]; then
    echo "错误: 无效的nohup参数 '$NOHUP'"
    echo "支持的nohup参数: true, false"
    exit 1
fi

# 非后台模式下，禁止一次性启动全部服务
if [[ "$NOHUP" == "false" && "$KNOWLEDGE_BASE" == "all" ]]; then
    echo "错误: 非后台模式(--nohup false)下不能使用 -kb all"
    echo "请指定单个知识库或改为后台运行"
    exit 1
fi

# ==================== 显示配置信息 ====================
echo "=========================================="
echo "知识库服务启动配置"
echo "=========================================="
echo "环境: $ENV"
echo "知识库: $KNOWLEDGE_BASE"
echo "后台运行: $NOHUP"
echo "=========================================="
echo ""

# ==================== 加载环境配置 ====================
source /home/Mr-Dice/bohrium_setup_env.sh

case $ENV in
    "test")
        source /home/Mr-Dice/export_test_env.sh
        echo "✓ 已加载测试环境配置"
        ;;
    "uat")
        source /home/Mr-Dice/export_uat_env.sh
        echo "✓ 已加载UAT环境配置"
        ;;
    "prod")
        source /home/Mr-Dice/export_prod_env.sh
        echo "✓ 已加载生产环境配置"
        ;;
esac
echo ""

# ==================== 停止旧进程 ====================
echo "停止旧的知识库server进程..."

# 通过端口号停止进程（最可靠的方法：直接通过ps查找PID）
for port in 50001 50002 50003 50004; do
    # 查找占用该端口的进程PID
    pid=$(ps aux | grep "[p]ython server.py --host 0.0.0.0 --port $port" | awk '{print $2}' | head -1)
    
    if [[ -n "$pid" && "$pid" =~ ^[0-9]+$ ]]; then
        echo "  停止端口 $port 上的进程 (PID: $pid)..."
        kill -9 "$pid" 2>/dev/null
    fi
done

sleep 1
echo "✓ 旧进程已停止"
echo ""

# ==================== 设置运行环境 ====================
# 设置conda环境
source $(conda info --base)/etc/profile.d/conda.sh
conda activate hea_rag

# 设置环境变量
export TIEFBLUE_BASE_URL=https://tiefblue-nas-acs-bj.bohrium.com
export BOHRIUM_USE_SANDBOX=1

# ==================== 知识库服务配置 ====================
# 定义知识库服务配置：名称 -> (目录, 端口, 显示名称)
declare -A KB_CONFIG
KB_CONFIG["hea"]="/home/knowledge_base/domains/HEA/server:50001:HEAkb"
KB_CONFIG["ssebrain"]="/home/knowledge_base/domains/ssebrain/server:50002:SSEkb"
KB_CONFIG["chembrain"]="/home/knowledge_base/domains/chembrain/server:50003:POLYMERkb"
KB_CONFIG["stainless_steel"]="/home/knowledge_base/domains/stainless_steel/server:50004:STEELkb"

# ==================== 启动服务 ====================
echo "开始启动知识库服务..."
echo ""

# 确定要启动的知识库列表
if [[ "$KNOWLEDGE_BASE" == "all" ]]; then
    KB_LIST=("hea" "ssebrain" "chembrain" "stainless_steel")
else
    KB_LIST=("$KNOWLEDGE_BASE")
fi

# 启动每个知识库服务
for kb in "${KB_LIST[@]}"; do
    if [[ -z "${KB_CONFIG[$kb]}" ]]; then
        echo "⚠ 警告: 未知的知识库 '$kb'，跳过"
        continue
    fi
    
    # 解析配置
    IFS=':' read -r kb_dir kb_port kb_name <<< "${KB_CONFIG[$kb]}"
    
    echo "启动 $kb_name 服务 (端口 $kb_port)..."
    cd "$kb_dir" || {
        echo "✗ 错误: 无法进入目录 $kb_dir"
        continue
    }
    
    if [[ "$NOHUP" == "true" ]]; then
        # 后台运行
        nohup python server.py --host 0.0.0.0 --port "$kb_port" > "server_${kb_port}.log" 2>&1 &
        local pid=$!
        echo "✓ $kb_name 服务已启动 (端口 $kb_port, PID: $pid)"
        echo "  日志文件: $(pwd)/server_${kb_port}.log"
        
        # 等待一小段时间，检查进程是否还在运行
        sleep 3
        if ! kill -0 "$pid" 2>/dev/null; then
            echo "  ⚠ 警告: 进程 $pid 已退出，请检查日志文件查看错误信息"
            echo "  最后10行日志:"
            tail -10 "server_${kb_port}.log" 2>/dev/null | sed 's/^/    /'
        fi
    else
        # 前台运行
        echo "  前台运行模式，按 Ctrl+C 停止服务"
        python server.py --host 0.0.0.0 --port "$kb_port"
    fi
    echo ""
done

# ==================== 显示运行状态 ====================
if [[ "$NOHUP" == "true" ]]; then
    echo "=========================================="
    echo "服务状态检查（等待初始化完成...）"
    echo "=========================================="
    sleep 5  # 给服务更多初始化时间
    
    local all_running=true
    # 检查每个服务的运行状态
    for kb in "${KB_LIST[@]}"; do
        if [[ -z "${KB_CONFIG[$kb]}" ]]; then
            continue
        fi
        IFS=':' read -r kb_dir kb_port kb_name <<< "${KB_CONFIG[$kb]}"
        
        if ps aux | grep -q "[p]ython server.py --host 0.0.0.0 --port $kb_port"; then
            echo "✓ $kb_name (端口 $kb_port) - 运行中"
        else
            echo "✗ $kb_name (端口 $kb_port) - 未运行（可能初始化失败或被系统终止）"
            all_running=false
            # 显示最后几行日志帮助排查
            if [[ -f "$kb_dir/server_${kb_port}.log" ]]; then
                echo "  最后5行日志:"
                tail -5 "$kb_dir/server_${kb_port}.log" 2>/dev/null | sed 's/^/    /'
            fi
        fi
    done
    
    echo ""
    if [[ "$all_running" == "true" ]]; then
        echo "✓ 所有服务启动完成！"
    else
        echo "⚠ 部分服务启动失败，请检查日志文件或系统资源（内存/磁盘）"
        echo "  提示: 如果看到 'Killed' 或 'Out of memory'，可能是内存不足"
    fi
    echo ""
    echo "提示: 使用以下命令查看详细进程信息"
    echo "  ps aux | grep 'server.py --host' | grep -v grep"
fi
