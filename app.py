import streamlit as st

# 设置页面配置
st.set_page_config(page_title="GraphRAG智能问答系统", layout="wide")

# 定义导航页面
pages = [
    st.Page("pages/doc_manage.py", title="文档管理", icon="📤"),
    st.Page("pages/chat.py", title="智能对话", icon="💬"),
]

# 创建导航菜单
pg = st.navigation(pages)

# 首页内容
st.title("GraphRAG智能问答系统")
st.write("这是一款基于图数据库和向量检索的智能问答系统，支持文档管理和智能对话功能。")

# 运行导航
pg.run()
