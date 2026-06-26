import re
import uuid
from typing import List
from langchain_experimental.text_splitter import SemanticChunker
try:
    from langchain.text_splitter import RecursiveCharacterTextSplitter
except ImportError:
    from langchain_text_splitters import RecursiveCharacterTextSplitter

from utils.log_utils import log
from langchain_core.documents import Document


class MarkdownParser:
    """
    专门负责markdown文件的解析和切片
    """
    def __init__(self):
        # 延迟初始化，避免在启动时就需要 embeddings
        self._text_splitter = None

    @property
    def text_splitter(self):
        if self._text_splitter is None:
            try:
                from llm_models.embeddings_model import bge_embedding
                self._text_splitter = SemanticChunker(
                    bge_embedding, breakpoint_threshold_type="percentile"
                )
            except Exception as e:
                log.warning(f"SemanticChunker 初始化失败，使用普通分割器: {e}")
                self._text_splitter = RecursiveCharacterTextSplitter(
                    chunk_size=1000, chunk_overlap=100
                )
        return self._text_splitter

    def text_chunker(self, datas: List[Document]) -> List[Document]:
        new_docs = []
        for d in datas:
            if len(d.page_content) > 5000:  # 内容超出了阈值，则按照语义再切割
                new_docs.extend(self.text_splitter.split_documents([d]))
                continue
            new_docs.append(d)
        return new_docs


    def parse_markdown_to_documents(self, md_file: str, encoding='utf-8') -> List[Document]:
        documents = self.parse_markdown(md_file)
        log.info(f'文件解析后的docs长度: {len(documents)}')

        merged_documents = self.merge_title_content(documents)

        log.info(f'文件合并后的长度: {len(merged_documents)}')

        chunk_documents = self.text_chunker(merged_documents)
        log.info(f'语义切割后的长度: {len(chunk_documents)}')
        return chunk_documents

    def parse_markdown(self, md_file: str) -> List[Document]:
        try:
            from langchain_community.document_loaders import UnstructuredMarkdownLoader
            loader = UnstructuredMarkdownLoader(
                file_path=md_file,
                mode='elements',
                strategy='fast'
            )
            docs = []
            for doc in loader.lazy_load():
                docs.append(doc)
            return docs
        except ImportError:
            log.warning("unstructured 未安装，使用内置 Markdown 解析器")
            return self._parse_markdown_fallback(md_file)

    def _parse_markdown_fallback(self, md_file: str, encoding='utf-8') -> List[Document]:
        """当 unstructured 不可用时的内置 Markdown 解析器，产出与 UnstructuredMarkdownLoader 兼容的结构。"""
        with open(md_file, 'r', encoding=encoding) as f:
            content = f.read()

        documents = []
        title_stack = []  # Stack of (level, element_id)
        current_title_id = None

        lines = content.split('\n')
        i = 0
        while i < len(lines):
            line = lines[i]

            # ATX headers (# style)
            match = re.match(r'^(#{1,6})\s+(.*)', line)
            if match:
                level = len(match.group(1))
                title_text = match.group(2).strip()
                element_id = str(uuid.uuid4())

                # Pop titles from stack that are at same or deeper level
                while title_stack and title_stack[-1][0] >= level:
                    title_stack.pop()

                parent_id = title_stack[-1][1] if title_stack else None
                title_stack.append((level, element_id))
                current_title_id = element_id

                doc = Document(
                    page_content=title_text,
                    metadata={
                        'category': 'Title',
                        'parent_id': parent_id,
                        'element_id': element_id,
                    }
                )
                documents.append(doc)
                i += 1
                continue

            # Non-empty text content
            if line.strip():
                # Collect consecutive non-empty, non-header lines
                text_lines = [line]
                while i + 1 < len(lines):
                    next_line = lines[i + 1]
                    if not next_line.strip() or re.match(r'^#{1,6}\s+', next_line):
                        break
                    text_lines.append(next_line)
                    i += 1

                text = '\n'.join(text_lines).strip()
                element_id = str(uuid.uuid4())

                doc = Document(
                    page_content=text,
                    metadata={
                        'category': 'NarrativeText',
                        'parent_id': current_title_id,
                        'element_id': element_id,
                    }
                )
                documents.append(doc)

            i += 1

        return documents

    def merge_title_content(self, datas: List[Document]) -> List[Document]:
        merged_data = []
        parent_dict = {}  # 是一个字典，保存所有的父document， key为当前父document的ID
        for document in datas:
            metadata = document.metadata
            if 'languages' in metadata:
                metadata.pop('languages')

            parent_id = metadata.get('parent_id', None)
            category = metadata.get('category', None)
            element_id = metadata.get('element_id', None)

            if category == 'NarrativeText' and parent_id is None:  # 是否为：内容document
                merged_data.append(document)
            if category == 'Title':
                document.metadata['title'] = document.page_content
                if parent_id in parent_dict:
                    document.page_content = parent_dict[parent_id].page_content + ' -> ' + document.page_content
                parent_dict[element_id] = document
            if category != 'Title' and parent_id:
                parent_dict[parent_id].page_content = parent_dict[parent_id].page_content + ' ' + document.page_content
                parent_dict[parent_id].metadata['category'] = 'content'

        # 处理字典
        if parent_dict is not None:
            merged_data.extend(parent_dict.values())

        return merged_data


if __name__ == '__main__':
    file_path = r'E:\my_project\RAG_PROJECT\datas\md\tech_report_0tfhhamx.md'
    parser = MarkdownParser()
    docs = parser.parse_markdown_to_documents(file_path)
    for item in docs:
        print(f"元数据: {item.metadata}")
        print(f"标题: {item.metadata.get('title', None)}")
        print(f"doc的内容: {item.page_content}\n")
        print("------" * 10)
