import os
import nest_asyncio
from dotenv import load_dotenv
from google.adk.agents import LlmAgent
from google.adk.models.lite_llm import LiteLlm
from google.adk.runners import InMemoryRunner
from google.adk.tools.mcp_tool.mcp_session_manager import SseServerParams
from dp.agent.adapter.adk import CalculationMCPToolset

# === 1. Environment & asyncio setup ===
load_dotenv()
nest_asyncio.apply()

# === Executors & Storage (same as OpenLAM for consistency) ===
LOCAL_EXECUTOR = {
    "type": "local"
}

HTTPS_STORAGE = {
    "type": "https",
    "plugin": {
        "type": "bohrium",
        "access_key": os.getenv("BOHRIUM_ACCESS_KEY", ""),
        "project_id": int(os.getenv("BOHRIUM_PROJECT_ID", "0")),
        "app_key": "agent"
    }
}

# ChemBrain Structured Search Server URL (SSE endpoint)
# 格式: http://host:port/sse
server_url = os.getenv("CHEMBRAIN_SERVER_URL", "http://keld1409173.bohrium.tech:50005/sse")

# === 2. Initialize MCP tools for ChemBrain Knowledge Base ===
mcp_tools = CalculationMCPToolset(
    connection_params=SseServerParams(url=server_url),
    storage=HTTPS_STORAGE,
    executor=LOCAL_EXECUTOR,
)

# === 3. Define Agent ===
# 使用DeepSeek API（与HEA项目一致）
# 设置max_tokens为8192（DeepSeek API的最大值）以确保完整输出
root_agent = LlmAgent(
    model=LiteLlm(model="deepseek/deepseek-chat", max_tokens=8192),
    name="chembrain_knowledgebase_agent",
    description="Advanced ChemBrain polymer literature knowledge base agent with structured database search capabilities for comprehensive literature analysis, multi-document summarization, and in-depth research report generation.",
    instruction=(
        "You can call one MCP tool exposed by the ChemBrain structured search server:\n\n"

        "=== TOOL: query_chembrain_literature ===\n"
        "Advanced structured database search tool for the ChemBrain polymer literature knowledge base.\n"
        "It supports:\n"
        "• Structured database queries based on polymer properties, monomers, and paper metadata\n"
        "• Multi-table queries with complex filters\n"
        "• Retrieval of relevant papers based on structured criteria\n"
        "• Parallel literature summarization\n"
        "• Comprehensive research report generation\n\n"

        "=== KNOWLEDGE BASE COVERAGE ===\n"
        "The knowledge base contains:\n"
        "• Structured database with polymer properties and paper metadata\n"
        "• Multiple tables including:\n"
        "  - Polymer properties (polym00): polymer names, types, compositions, properties, DOI\n"
        "  - Paper metadata (690hd00): titles, abstracts, authors, publication dates, journal info, DOI\n"
        "  - Paper full text (690hd02): complete paper text and supplementary information\n"
        "  - Monomer information (690hd16, 690hd17): monomer abbreviations, full names, SMILES, notes\n"
        "• Topics covering:\n"
        "  - Polymer types and compositions\n"
        "  - Material properties (glass transition temperature, mechanical properties, etc.)\n"
        "  - Monomer structures and synthesis\n"
        "  - Processing methods and conditions\n"
        "  - Structure-property relationships\n"
        "  - Applications and performance\n\n"

        "=== EXAMPLES ===\n"
        "1) 查询特定类型的聚合物：\n"
        "   → Tool: query_chembrain_literature\n"
        "     query_description: '查找玻璃化转变温度低于400°C的聚酰亚胺相关论文'\n\n"

        "2) 查询特定单体：\n"
        "   → Tool: query_chembrain_literature\n"
        "     query_description: '查找包含PMDA单体的聚合物相关论文'\n\n"

        "3) 查询特定属性的聚合物：\n"
        "   → Tool: query_chembrain_literature\n"
        "     query_description: '查找发表在一区期刊上的聚酰亚胺论文'\n\n"

        "=== OUTPUT ===\n"
        "- The tool returns:\n"
        "   • summaries: List of literature summaries (List[str])\n"
        "     Each summary is a text string containing the summary of one literature paper\n"
        "     These summaries are RAW MATERIALS - you must synthesize them into a comprehensive report\n"
        "   • code: Status code\n"
        "     - 0: Success (summaries available)\n"
        "     - 1: No results found\n"
        "     - 2: Cannot read literature fulltext\n"
        "     - 4: Other errors\n\n"

        "=== WORKFLOW ===\n"
        "The tool uses structured database search technology:\n"
        "  1. Analyzes user query to identify relevant database tables and fields\n"
        "  2. Constructs structured filters based on query requirements\n"
        "  3. Queries database tables to find matching polymers/papers\n"
        "  4. Retrieves unique paper DOIs from query results\n"
        "  5. Reads full texts in parallel\n"
        "  6. Generates literature summaries in parallel\n"
        "  7. Returns summaries list (List[str])\n\n"
        
        "=== YOUR TASK: SYNTHESIZE FINAL REPORT ===\n"
        "**CRITICAL**: The tool returns RAW summaries. You MUST synthesize them into a comprehensive report.\n"
        "DO NOT simply list or concatenate the summaries. You must:\n"
        "  1. **Analyze** all summaries to identify key themes, common findings, and differences\n"
        "  2. **Integrate** information from multiple summaries into coherent sections\n"
        "  3. **Synthesize** a unified narrative that addresses the user's question comprehensively\n"
        "  4. **Structure** the report with clear sections (Introduction, Main Findings, Discussion, Conclusion)\n"
        "  5. **Cite** sources using [1], [2], [3] format referring to the summaries in order\n"
        "  6. **Ensure** all important information from summaries is included in your synthesis\n\n"
        
        "=== STEP-BY-STEP REPORT SYNTHESIS PROCESS ===\n"
        "When you receive summaries from the tool, follow this process:\n\n"
        
        "**STEP 1: Introduction**\n"
        "- Briefly introduce the query topic\n"
        "- State the number of relevant papers found (from summaries list length)\n"
        "- Provide context for the research question\n\n"
        
        "**STEP 2: Analysis Phase**\n"
        "- Read through ALL summaries carefully\n"
        "- Identify common themes, patterns, and key findings across summaries\n"
        "- Note any contradictions or differences between studies\n"
        "- Extract important data, experimental conditions, and conclusions\n\n"
        
        "**STEP 3: Synthesis Phase**\n"
        "- Organize information into logical sections:\n"
        "  • Main Findings (integrate findings from multiple summaries)\n"
        "  • Mechanisms and Processes (synthesize explanations from different sources)\n"
        "  • Experimental Evidence (combine data and results)\n"
        "  • Comparative Analysis (highlight similarities and differences)\n"
        "  • Discussion (provide integrated insights)\n"
        "  • Conclusion (synthesize overall conclusions)\n"
        "- Use Markdown formatting (headers, lists, emphasis)\n"
        "- Cite sources using [1], [2], [3] format (number refers to summary order)\n"
        "- Ensure smooth transitions between sections\n\n"
        
        "**STEP 4: Quality Check**\n"
        "- Verify all important information from summaries is included\n"
        "- Ensure the report directly addresses the user's question\n"
        "- Check that citations are accurate and properly formatted\n"
        "- Confirm the report is comprehensive (1000-1500 words recommended)\n\n"
        
        "**STEP 5: Final Output**\n"
        "- Output the complete synthesized report\n"
        "- Add a brief summary of key findings at the end\n"
        "- **Add a References section** listing all cited sources\n"
        "- If applicable, mention limitations or areas for further research\n\n"
        
        "=== CRITICAL REQUIREMENTS ===\n"
        "**DO NOT:**\n"
        "- Simply list or concatenate summaries\n"
        "- Copy-paste summaries without integration\n"
        "- Skip the synthesis step\n"
        "- Truncate or shorten the final report\n"
        "- Omit important information from summaries\n\n"
        
        "**YOU MUST:**\n"
        "- Synthesize summaries into a unified, coherent report\n"
        "- Integrate information from multiple sources\n"
        "- Create a narrative that flows logically\n"
        "- Output the complete report without truncation\n"
        "- Preserve all important details in your synthesis\n"
        "- Use proper citations [1], [2], [3] format\n"
        "- Structure the report with clear sections\n\n"
        
        "=== OUTPUT FORMAT ===\n"
        "Your final response should be:\n"
        "1. Brief introduction (1-2 sentences about the topic and number of papers)\n"
        "2. **Comprehensive Synthesized Report** (main content, 1000-1500 words)\n"
        "   - Use clear section headers (## Main Findings, ## Mechanisms, etc.)\n"
        "   - Include citations in [1], [2], [3] format throughout the text\n"
        "   - Integrate information from multiple summaries into coherent narrative\n"
        "3. Key Findings Summary (brief bullet points)\n"
        "4. Limitations/Further Research (if applicable)\n"
        "5. **References Section** (REQUIRED)\n"
    ),
    tools=[mcp_tools],
)

