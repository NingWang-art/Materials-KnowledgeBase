#!/bin/bash
# 启动HEA RAG Server和Agent服务

# 先停止旧进程
echo "停止旧进程..."
pkill -f "adk web.*50002" 2>/dev/null
pkill -f "server.*50001" 2>/dev/null
sleep 2

cd /home/knowledge_base/domains/HEA
source $(conda info --base)/etc/profile.d/conda.sh
conda activate hea_rag

# export OPIK_PROJECT_NAME="test"
# export BOHRIUM_BOHRIUM_URL="https://bohrium.test.dp.tech"
# export BOHRIUM_TIEFBLUE_URL="https://tiefblue.test.dp.tech"
# export BOHRIUM_OPENAPI_URL="https://openapi.test.dp.tech"
# export BOHRIUM_BASE_URL="https://openapi.test.dp.tech"
# export TIEFBLUE_BASE_URL="https://tiefblue-nas-acs-bj.test.bohrium.com"
# export BOHRIUM_USE_SANDBOX=1

export TIEFBLUE_BASE_URL=https://tiefblue-nas-acs-bj.bohrium.com
export BOHRIUM_USE_SANDBOX=1

# 启动Server (端口50001)
cd /home/knowledge_base/domains/HEA/server
nohup python server.py --host 0.0.0.0 --port 50001 2>&1 &

# 启动Agent (端口50002)
# 注意：adk web会在当前目录查找agent子目录，所以必须在HEA目录下运行
cd /home/knowledge_base/domains/HEA
nohup adk web --host 0.0.0.0 --port 50002 2>&1 &

echo "服务已启动"
echo "Server: 端口50001"
echo "Agent: 端口50002"
