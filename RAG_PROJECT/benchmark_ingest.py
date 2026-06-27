"""
吞吐量测试脚本 v2：分阶段测试解析和写入
用法：cd RAG_PROJECT && python benchmark_ingest.py
"""
import time
import os
import sys
import shutil
import threading

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from documents.markdown_parser import MarkdownParser
from pymilvus import MilvusClient, DataType, IndexType, Function, FunctionType
from pymilvus.client.types import MetricType
from langchain_milvus import Milvus, BM25BuiltInFunction
from llm_models.embeddings_model import bge_embedding
from langchain_core.documents import Document

MD_DIR = r"../md"
DB_PATH = "benchmark_test.db"
COLLECTION = "bench_col"

def cleanup_db():
    if os.path.exists(DB_PATH):
        shutil.rmtree(DB_PATH, ignore_errors=True)

def main():
    md_files = sorted([f for f in os.listdir(MD_DIR) if f.endswith('.md')])
    total_files = len(md_files)
    print(f"=== 文档入库吞吐量测试 ===")
    print(f"待入库文件数: {total_files}")

    # ---- 阶段1：解析吞吐量 ----
    print(f"\n[阶段1] 解析吞吐量测试（Markdown → Document chunks）...")
    parser = MarkdownParser()
    all_docs = []
    parse_start = time.time()

    for i, filename in enumerate(md_files, 1):
        file_path = os.path.join(MD_DIR, filename)
        try:
            docs = parser.parse_markdown_to_documents(file_path)
            all_docs.extend(docs)
        except Exception as e:
            pass
        if i % 50 == 0:
            elapsed = time.time() - parse_start
            rate = len(all_docs) / (elapsed / 60) if elapsed > 0 else 0
            print(f"  解析进度: {i}/{total_files} | {len(all_docs)} chunks | {rate:.0f} docs/min")

    parse_elapsed = time.time() - parse_start
    parse_min = parse_elapsed / 60
    total_chunks = len(all_docs)
    parse_rate = total_chunks / parse_min if parse_min > 0 else 0

    print(f"\n  解析完成: {total_files} 文件 → {total_chunks} 文档块")
    print(f"  解析耗时: {parse_elapsed:.1f}s ({parse_min:.2f}min)")
    print(f"  解析吞吐: {parse_rate:.0f} docs/min")

    # ---- 阶段2：Milvus Lite 写入吞吐量 ----
    print(f"\n[阶段2] Milvus Lite 写入吞吐量测试...")
    cleanup_db()

    # 简化schema避免Windows os.rename bug：不用BM25，只用Dense
    os.environ.pop("MILVUS_URI", None)
    from langchain_milvus import Milvus as LCMilvus

    vector_store = LCMilvus(
        embedding_function=bge_embedding,
        collection_name=COLLECTION,
        consistency_level="Strong",
        auto_id=True,
        connection_args={"uri": DB_PATH},
    )

    # 分批写入并计时
    BATCH_SIZE = 50
    write_start = time.time()
    written = 0

    for i in range(0, len(all_docs), BATCH_SIZE):
        batch = all_docs[i:i+BATCH_SIZE]
        try:
            vector_store.add_documents(batch)
            written += len(batch)
        except Exception as e:
            print(f"  写入批次 {i} 失败: {e}")
        if written % 200 == 0 and written > 0:
            elapsed = time.time() - write_start
            rate = written / (elapsed / 60) if elapsed > 0 else 0
            print(f"  写入进度: {written}/{total_chunks} | {rate:.0f} docs/min")

    write_elapsed = time.time() - write_start
    write_min = write_elapsed / 60
    write_rate = written / write_min if write_min > 0 else 0

    print(f"\n  写入完成: {written}/{total_chunks} 文档块")
    print(f"  写入耗时: {write_elapsed:.1f}s ({write_min:.2f}min)")
    print(f"  写入吞吐: {write_rate:.0f} docs/min")

    # ---- 总结 ----
    total_elapsed = parse_elapsed + write_elapsed
    total_min = total_elapsed / 60
    total_rate = written / total_min if total_min > 0 else 0

    print(f"\n{'='*40}")
    print(f"=== 最终测试结果 ===")
    print(f"源文件数:       {total_files} 篇")
    print(f"文档块总数:     {total_chunks} 块")
    print(f"解析吞吐:       {parse_rate:.0f} docs/min")
    print(f"写入吞吐:       {write_rate:.0f} docs/min")
    print(f"端到端吞吐:     {total_rate:.0f} docs/min")
    print(f"端到端耗时:     {total_elapsed:.1f}s ({total_min:.2f}min)")
    print(f"{'='*40}")

    # 清理
    cleanup_db()
    print("已清理测试数据库")

if __name__ == '__main__':
    main()
