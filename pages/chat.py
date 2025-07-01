import streamlit as st
from services.rag_service import RAGService
import networkx as nx
import matplotlib.pyplot as plt
from pyvis.network import Network
import streamlit.components.v1 as components

# 初始化RAG服务
rag_service = RAGService()

st.title("智能对话")

# 初始化会话状态
if "messages" not in st.session_state:
    st.session_state.messages = []

if "graph_data" not in st.session_state:
    st.session_state.graph_data = None

# 显示历史消息
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# 显示知识图谱（如果有）
if st.session_state.graph_data is not None:
    st.subheader("相关知识图谱")
    
    # 创建一个基于HTML的交互式图表
    net = Network(height="500px", width="100%", bgcolor="#ffffff", font_color="black")
    
    # 添加节点和边
    for node in st.session_state.graph_data["nodes"]:
        net.add_node(node["id"], label=node["label"], title=node["title"], color=node["color"])
    
    for edge in st.session_state.graph_data["edges"]:
        net.add_edge(edge["from"], edge["to"], title=edge["label"])
    
    # 设置图的物理布局
    net.barnes_hut(gravity=-80000, central_gravity=0.3, spring_length=250, spring_strength=0.001, damping=0.09)
    
    # 保存并显示交互式图表
    net.save_graph("temp_graph.html")
    with open("temp_graph.html", "r", encoding="utf-8") as f:
        html_content = f.read()
    
    # 使用streamlit组件显示HTML内容
    components.html(html_content, height=500)

# 用户输入区域
if prompt := st.chat_input("请输入您的问题"):
    # 添加用户消息到历史记录
    st.session_state.messages.append({"role": "user", "content": prompt})
    
    # 显示用户消息
    with st.chat_message("user"):
        st.markdown(prompt)
    
    # 显示助手思考中的消息
    with st.chat_message("assistant"):
        message_placeholder = st.empty()
        message_placeholder.markdown("思考中...")
        
        # 调用RAG服务获取回复和知识图谱
        try:
            response_data = rag_service.get_response(prompt)
            
            # 更新回复内容
            message_placeholder.markdown(response_data["response"])
            
            # 添加助手消息到历史记录
            st.session_state.messages.append({"role": "assistant", "content": response_data["response"]})
            
            # 如果有知识图谱数据，则保存并刷新页面以显示
            if response_data["graph_data"] is not None and len(response_data["graph_data"]["nodes"]) > 0:
                st.session_state.graph_data = response_data["graph_data"]
                st.rerun()
        
        except Exception as e:
            error_message = f"处理您的问题时出错：{str(e)}"
            message_placeholder.markdown(error_message)
            st.session_state.messages.append({"role": "assistant", "content": error_message})
