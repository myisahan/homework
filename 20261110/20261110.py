from langchain_community.vectorstores import Chroma
from langchain_ollama import OllamaEmbeddings, ChatOllama
from langchain_core.tools.retriever import create_retriever_tool
from langchain.agents import create_agent

embedding_model = OllamaEmbeddings(model="qwen3-embedding:0.6b", base_url="http://192.168.1.105:11434")

# 加载向量数据库
db = Chroma(
    collection_name="car_info",
    embedding_function=embedding_model,
    persist_directory="D:/Users/myisa/Visual Studio/20261109RAG/chroma_db",
)

# 将向量存储转换为检索器，再封装成工具
retriever = db.as_retriever(search_kwargs={"k": 2})
retriever_tool = create_retriever_tool(
    retriever,
    name="info_retriever",
    description="搜索并返回领克汽车相关信息。",
)

llm = ChatOllama(model="qwen3.5:9b", base_url="http://192.168.1.105:11434")

agent = create_agent(
    model=llm,
    tools=[retriever_tool],
    system_prompt="你是一个领克汽车助手，回答汽车相关问题时调用info_retriever工具检索资料，根据检索结果来回答用户问题。",
)

query = "领克汽车车顶行李架最大载荷是多少？"
res = agent.invoke({"messages": [{"role": "user", "content": query}]})

for message in res["messages"]:
    message.pretty_print()
