"""
测试SSEBrain Structured Search Server查询功能
"""
import sys
from pathlib import Path
import logging

# 添加项目路径
sys.path.insert(0, str(Path("/home/knowledge_base")))
sys.path.insert(0, str(Path("/home/knowledge_base/domains")))

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_query():
    """测试查询功能"""
    from domains.ssebrain.server.server import StructuredSearchSystem
    
    # 初始化结构化检索系统
    logger.info("初始化结构化检索系统...")
    search_system = StructuredSearchSystem()
    logger.info("✓ 结构化检索系统初始化完成")
    
    # ==================== 测试问题列表 ====================
    # 当前使用的测试问题
    query_description = "查找具有特定性能的材料相关论文"
    
    # 其他测试问题（已注释，可以取消注释来测试）
    
    # 问题1: 特定材料类型
    # query_description = "查找特定材料类型的相关论文"
    
    # 问题2: 特定属性范围
    # query_description = "查找具有特定性能范围的材料论文"
    
    logger.info("=" * 60)
    logger.info(f"测试查询: {query_description}")
    logger.info("=" * 60)
    
    # 执行查询
    result = search_system.query(query_description)
    
    # 显示结果
    logger.info("\n" + "=" * 60)
    logger.info("查询结果:")
    logger.info("=" * 60)
    logger.info(f"状态码: {result['code']}")
    logger.info(f"文献总结数量: {len(result['summaries'])}")
    
    if result['code'] == 0:
        logger.info("\n" + "-" * 60)
        logger.info("文献总结列表:")
        logger.info("-" * 60)
        for i, summary in enumerate(result['summaries'], 1):
            logger.info(f"\n【文献总结 {i}】")
            logger.info(f"{summary}")
            logger.info("-" * 60)
    else:
        logger.warning(f"查询失败，状态码: {result['code']}")
        if result['code'] == 1:
            logger.warning("未找到相关论文")
        elif result['code'] == 2:
            logger.warning("无法读取文献全文")
        else:
            logger.warning("其他错误")
    
    logger.info("=" * 60)
    
    return result

if __name__ == "__main__":
    result = test_query()
    print("\n✓ 测试完成！")

