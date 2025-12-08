#!/bin/bash
# 启动SSEBrain Structured Search Server和Agent服务

# 先停止旧进程（只停止ssebrain相关的，不影响其他服务）
echo "停止旧进程..."
pkill -f "adk web.*50006" 2>/dev/null
pkill -f "server.*50005" 2>/dev/null
sleep 2

cd /home/knowledge_base/domains/ssebrain
source $(conda info --base)/etc/profile.d/conda.sh
conda activate hea_rag

export TIEFBLUE_BASE_URL=https://tiefblue-nas-acs-bj.bohrium.com
export BOHRIUM_USE_SANDBOX=1

# 启动Server (端口50005)
cd /home/knowledge_base/domains/ssebrain/server
nohup python server.py --host 0.0.0.0 --port 50005 2>&1 &

# 启动Agent (端口50006)
# 注意：adk web会在当前目录查找agent子目录，所以必须在ssebrain目录下运行
cd /home/knowledge_base/domains/ssebrain
nohup adk web --host 0.0.0.0 --port 50006 2>&1 &

echo "服务已启动"
echo "Server: 端口50005"
echo "Agent: 端口50006"

