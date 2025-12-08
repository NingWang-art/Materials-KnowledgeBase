"""
通用常量定义模块
"""

# ==================== 状态码定义 ====================
class StatusCode:
    """查询状态码"""
    SUCCESS = 0              # 正常完成
    NO_RESULTS = 1          # 未找到相关信息
    NO_LITERATURE = 2       # 无法读取文献全文
    REPORT_FAILED = 3       # 生成报告失败
    OTHER_ERROR = 4         # 其他异常


