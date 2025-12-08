"""
测试HEA RAG Server查询功能
"""
import sys
from pathlib import Path
import logging

# 添加项目路径
sys.path.insert(0, str(Path("/home/knowledge_base")))

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_query():
    """测试查询功能"""
    from domains.HEA.server.server import RAGSystem
    
    # 初始化RAG系统
    logger.info("初始化RAG系统...")
    rag = RAGSystem()
    logger.info(f"✓ RAG系统初始化完成，包含 {rag.vector_store.get_total_vectors()} 个向量")
    
    # ==================== 测试问题列表 ====================
    # 当前使用的测试问题
    # question = "高熵合金中的相变诱导塑性（TRIP）机制是什么？这种机制如何影响合金的力学性能？"
    
    # 其他测试问题（已注释，可以取消注释来测试）
    
    # 问题1: 相变相关
    # question = "高熵合金中的FCC到HCP相变的条件和影响因素是什么？"
    # 问题2: 力学性能
    # question = "高熵合金在低温下的力学性能如何？影响低温性能的主要因素有哪些？"
    # 问题3: 腐蚀性能
    question = "高熵合金的腐蚀行为和防护机制是什么？不同元素对腐蚀性能的影响如何？"
    # 问题4: 微观结构
    # question = "高熵合金的微观结构特征是什么？如何通过热处理调控微观结构？"
    # 问题5: 制备方法
    # question = "高熵合金的主要制备方法有哪些？不同制备方法对合金性能的影响如何？"
    # 问题6: 元素选择
    # question = "高熵合金中元素的选择原则是什么？不同元素组合对性能的影响规律？"
    # 问题7: 强化机制
    # question = "高熵合金的主要强化机制有哪些？固溶强化、析出强化、晶界强化等机制的作用？"
    # 问题8: 疲劳性能
    # question = "高熵合金的疲劳性能和疲劳裂纹扩展行为如何？影响疲劳性能的关键因素？"
    # 问题9: 高温性能
    # question = "高熵合金在高温下的性能表现如何？高温下的相稳定性和蠕变行为？"
    # 问题10: 应用领域
    # question = "高熵合金在哪些领域有应用前景？与传统合金相比有哪些优势？"
    # 问题11: 多相结构
    # question = "高熵合金中的多相结构是如何形成的？多相结构对性能的影响？"
    # 问题12: 晶格畸变
    # question = "高熵合金中的晶格畸变效应是什么？晶格畸变如何影响材料的性能？"
    
    logger.info("=" * 60)
    logger.info(f"测试问题: {question}")
    logger.info("=" * 60)
    
    # 执行查询
    result = rag.query(question, top_k=5)
    
    # 显示结果
    logger.info("\n" + "=" * 60)
    logger.info("查询结果:")
    logger.info("=" * 60)
    logger.info(f"状态码: {result['code']}")
    logger.info(f"文献总结数量: {len(result['summaries'])}")
    logger.info("\n" + "-" * 60)
    logger.info("文献总结列表:")
    logger.info("-" * 60)
    for i, summary in enumerate(result['summaries'], 1):
        logger.info(f"\n【文献总结 {i}】")
        logger.info(f"{summary}")
        logger.info("-" * 60)
    logger.info("=" * 60)
    
    return result

if __name__ == "__main__":
    result = test_query()
    print("\n✓ 测试完成！")


