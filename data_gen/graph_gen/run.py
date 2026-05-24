from dataload_toolkit import build_graph_from_data_ldbcbi, load_graph, save_graph
import os
import random
from pathlib import Path
# from ..data_analyser.graph_handler import GraphInspector 
if __name__ == "__main__":
    # LDBC SNB FinBench 数据
    default_data_path = (
        Path(__file__).resolve().parents[1]
        / "gnd_dataset"
        / "ldbc_snb_bi"
        / "out-sf1"
        / "csv"
        / "bi"
        / "composite-projected-fk"
        / "initial_snapshot"
    )
    data_path = os.getenv("LDBC_SNB_BI_DATA_PATH", str(default_data_path))
    graph_name = "ldbc_snb_bi"
    file_format = ".csv.gz"
    graph_path = Path(f"graph_buffer/{graph_name}.gpickle")
    
    # 确保 graph_buffer 目录存在
    graph_path.parent.mkdir(parents=True, exist_ok=True)
    
    if graph_path.exists():
        graph = load_graph(graph_path)
        print(f"从 {graph_path} 加载图")
    else:
        graph = build_graph_from_data_ldbcbi(data_path, file_format)
        save_graph(graph, graph_path)
    
    # 创建图检查器
    # graph_inspector = GraphInspector(graph)
    
    # # 显示图的统计信息
    # print("\n" + "="*60)
    # print("【图的整体统计信息】")
    # print("="*60)
    # graph_inspector.summary()
    
    # 随机采样一些节点进行测试
    all_nodes = list(graph.nodes())
    sample_size = min(5, len(all_nodes))  # 采样5个节点，如果节点数少于5则全部采样
    sampled_nodes = random.sample(all_nodes, sample_size)
    
    print("\n" + "="*60)
    print(f"【随机采样 {sample_size} 个节点进行测试】")
    print("="*60)
    
    for i, node in enumerate(sampled_nodes, 1):
        print(f"\n{'─'*60}")
        print(f"📍 节点 {i}: {node}")
        print(f"{'─'*60}")
        
        # 测试度数相关功能
        in_deg = graph_inspector.in_degree(node)
        out_deg = graph_inspector.out_degree(node)
        total_deg = graph_inspector.degree(node)
        print(f"📥 入度: {in_deg}")
        print(f"📤 出度: {out_deg}")
        print(f"📊 总度数: {total_deg}")
        
        # 测试按关系统计出度
        rel_outdegree = graph_inspector.out_degree_by_relation(node)
        if rel_outdegree:
            print(f"\n🔗 按关系类型统计出度:")                                                                                                                                          
            for rel, count in sorted(rel_outdegree.items(), key=lambda x: x[1], reverse=True):
                print(f"  - {rel}: {count}")
        else:
            print(f"\n🔗 该节点没有出边")
        
        # 测试入边和出边
        # in_edges = graph_inspector.in_edges(node)
        # out_edges = graph_inspector.out_edges(node)
        
        # # 显示部分入边示例（最多显示3条）
        # if in_edges:
        #     print(f"\n📥 入边示例 (共 {len(in_edges)} 条，显示前3条):")
        #     for src, dst, data in in_edges[:3]:
        #         print(f"  {src} --[{data.get('label', 'N/A')}]--> {dst}")
        
        # # 显示部分出边示例（最多显示3条）
        # if out_edges:
        #     print(f"\n📤 出边示例 (共 {len(out_edges)} 条，显示前3条):")
        #     for src, dst, data in out_edges[:3]:
        #         print(f"  {src} --[{data.get('label', 'N/A')}]--> {dst}")
        
        # # 如果有关系类型，测试按关系查询边
        # if rel_outdegree:
        #     # 选择出度最高的关系类型
        #     top_relation = max(rel_outdegree.items(), key=lambda x: x[1])[0]
        #     edges_of_relation = graph_inspector.edges_by_relation(node, top_relation)
        #     print(f"\n🎯 关系类型 '{top_relation}' 的边 (共 {len(edges_of_relation)} 条，显示前3条):")
        #     for src, dst in edges_of_relation[:3]:
        #         print(f"  {src} --> {dst}")
    
    print("\n" + "="*60)
    print("✅ GraphInspector 功能测试完成！")
    print("="*60)
