#!/bin/bash
# 使用hea_rag环境运行测试

cd /home/knowledge_base/domains/HEA/server
source $(conda info --base)/etc/profile.d/conda.sh
conda activate hea_rag

python3 test_query.py




