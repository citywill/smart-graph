import streamlit as st
import os
import datetime
import pandas as pd
from services.doc_service import DocumentService

# 初始化文档服务
doc_service = DocumentService()

st.header("文档管理")

# 创建两个选项卡：文档上传和文档管理
tab1, tab2 = st.tabs(["文档上传", "文档管理"])

# 文档上传选项卡
with tab1:
    st.subheader("上传文档")
    
    # 文件上传组件
    uploaded_file = st.file_uploader("选择要上传的文档", type=["txt", "md"], help="目前仅支持txt和md格式")
    
    # 分块配置
    st.subheader("分块配置")
    col1, col2 = st.columns(2)
    
    with col1:
        chunk_separator = st.text_input("分块分隔符", value="\\n\\n", help="用于分割文档的分隔符")
    
    with col2:
        chunk_size = st.number_input("分块最大长度", value=500, min_value=100, max_value=1000, help="每个分块的最大字符数")
    
    if uploaded_file is not None:
        if st.button("开始处理"):
            # 显示进度条
            progress_bar = st.progress(0, "准备处理文档...")
            
            # 保存上传的文件
            file_path = os.path.join("uploads", uploaded_file.name)
            with open(file_path, "wb") as f:
                f.write(uploaded_file.getbuffer())
            
            # 处理文档
            try:
                progress_bar.progress(10, "文件已保存，正在处理...")
                
                # 调用文档服务进行处理
                result = doc_service.process_document(
                    file_path=file_path, 
                    separator=chunk_separator.replace("\\n", "\n"), 
                    max_chunk_size=chunk_size
                )
                
                if result["success"]:
                    progress_bar.progress(100, "处理完成！")
                    st.success(f"文档 {uploaded_file.name} 处理成功！共生成 {result['chunks_count']} 个分块，识别出 {result['entities_count']} 个实体。")
                else:
                    progress_bar.progress(100, "处理失败！")
                    st.error(f"文档处理失败：{result['error']}")
            
            except Exception as e:
                progress_bar.progress(100, "处理失败！")
                st.error(f"处理过程中发生错误：{str(e)}")

# 文档管理选项卡
with tab2:
    st.subheader("文档列表")
    
    # 搜索和过滤
    search_query = st.text_input("按标题搜索文档", "")
    
    # 文档列表刷新按钮
    if st.button("刷新文档列表"):
        st.rerun()
    
    # 获取文档列表
    try:
        documents = doc_service.get_documents(title_filter=search_query)
        
        if not documents:
            st.info("没有找到任何文档。")
        else:
            # 分页控制
            docs_per_page = 5
            total_pages = (len(documents) + docs_per_page - 1) // docs_per_page
            
            col1, col2 = st.columns([4, 1])
            with col2:
                current_page = st.selectbox("页码", options=list(range(1, total_pages + 1)), index=0)
            
            # 计算当前页的文档
            start_idx = (current_page - 1) * docs_per_page
            end_idx = min(start_idx + docs_per_page, len(documents))
            current_docs = documents[start_idx:end_idx]
            
            # 显示文档列表
            for doc in current_docs:
                with st.expander(f"{doc['title']} (上传于: {doc['created']})"):
                    col1, col2 = st.columns([3, 1])
                    
                    with col1:
                        st.write(f"**摘要**: {doc['summary']}")
                        st.write(f"**大小**: {doc['size']} 字节")
                        
                        # 查看文档内容按钮
                        if st.button("查看内容", key=f"view_{doc['id']}"):
                            chunks = doc_service.get_document_chunks(doc['id'])
                            st.subheader("文档内容")
                            for chunk in chunks:
                                st.text_area(f"块 {chunk['position']}", chunk['content'], height=150, key=f"chunk_{doc['id']}_{chunk['position']}")
                    
                    with col2:
                        # 下载文档按钮
                        if st.button("下载文档", key=f"download_{doc['id']}"):
                            doc_content = doc_service.get_document_content(doc['id'])
                            st.download_button(
                                label="点击下载",
                                data=doc_content,
                                file_name=doc['title'],
                                mime="text/plain",
                                key=f"dl_btn_{doc['id']}"
                            )
                        
                        # 删除文档按钮
                        if st.button("删除文档", key=f"delete_{doc['id']}"):
                            if doc_service.delete_document(doc['id']):
                                st.success(f"文档 {doc['title']} 已删除")
                                st.rerun()
                            else:
                                st.error("删除文档失败")
    
    except Exception as e:
        st.error(f"获取文档列表时出错：{str(e)}")
