from generator.manage_generator import ManageGenerator
from pathlib import Path
import sys
import argparse

# 添加 pipeline 目录到路径，以便导入 db_builder
# management_test.py 在 pipeline/query_gen/，需要向上2级到 pipeline
pipeline_dir = Path(__file__).parent.parent
sys.path.insert(0, str(pipeline_dir))

# 直接导入 build_base 模块
import importlib.util
build_base_path = pipeline_dir / "db_builder" / "build_base.py"
spec = importlib.util.spec_from_file_location("build_base", build_base_path)
build_base = importlib.util.module_from_spec(spec)
spec.loader.exec_module(build_base)
Neo4jGraphBuilder = build_base.Neo4jGraphBuilder

# 获取当前文件所在目录
current_dir = Path(__file__).parent
DEFAULT_TEMPLATE_PATH = current_dir / "query_template" / "template_managemet.json"

# 项目根目录（用于默认 GRAPH_PATH）
PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_GRAPH_PATH = (
    PROJECT_ROOT
    / "data_gen"
    / "graph_gen"
    / "graph_buffer"
    / "Primekg_gnd.gpickle"
)
DEFAULT_LOCAL_NEO4J_URI = "bolt://localhost:7687"
DEFAULT_CONTAINER_NEO4J_URI = "bolt://localhost:7692"
# python management_test.py --neo4j-uri bolt://localhost:7691 --dataset ldbc_bi --graph-path data_gen/graph_gen/graph_buffer/ldbc_snb_bi.gpickle
# 解析命令行参数
parser = argparse.ArgumentParser(description="管理查询生成测试脚本")
parser.add_argument(
    "--skip-build",
    action="store_true",
    help="跳过数据库构建步骤（默认：False，会构建数据库）"
)
parser.add_argument(
    "--neo4j-uri",
    default=None,
    help=(
        "Neo4j 连接 URI；不传时根据 --neo4j-target 选择 "
        f"local={DEFAULT_LOCAL_NEO4J_URI} 或 container={DEFAULT_CONTAINER_NEO4J_URI}"
    )
)
parser.add_argument(
    "--neo4j-target",
    choices=["local", "container"],
    default="local",
    help="Neo4j 目标类型：local=本地 Neo4j，container=容器端口映射（默认：local）"
)
parser.add_argument(
    "--neo4j-user",
    default="neo4j",
    help="Neo4j 用户名（默认：neo4j）"
)
parser.add_argument(
    "--neo4j-password",
    default="fei123456",
    help="Neo4j 密码（默认：fei123456）"
)
parser.add_argument(
    "--dataset",
    default="ldbc_fin",
    help="数据集名称（默认：ldbc_fin）"
)
parser.add_argument(
    "--validation-mode",
    choices=["agg", "no-agg"],
    default="no-agg",
    help="验证模式：agg=按原有聚合逻辑；no-agg=为每条 template 生成对应的非聚合验证（默认：agg）"
)
parser.add_argument(
    "--template-path",
    default=None,
    type=Path,
    help=f"管理查询模板文件路径（默认：{DEFAULT_TEMPLATE_PATH}）"
)
parser.add_argument(
    "--graph-path",
    default=None,
    type=Path,
    help=f"图文件路径（默认：{DEFAULT_GRAPH_PATH}）"
)
parser.add_argument(
    "--recovery-mode",
    choices=["transaction-rollback", "local-rebuild", "none"],
    default="transaction-rollback",
    help=(
        "管理查询执行后的恢复方式：transaction-rollback=事务回滚（默认，高效且不依赖容器）；"
        "local-rebuild=使用本地 Neo4jGraphBuilder 从 graph 文件清库重建；"
        "none=不额外恢复"
    )
)
parser.add_argument(
    "--target-count",
    type=int,
    default=1000,
    help="目标生成查询数量（默认：1000）"
)
parser.add_argument(
    "--success-per-template",
    type=int,
    default=100,
    help="每个模板最多成功生成的查询数量（默认：100）"
)
parser.add_argument(
    "--max-failures-per-template",
    type=int,
    default=500,
    help="每个模板最大连续失败次数（默认：500）"
)
args = parser.parse_args()

# 从命令行或默认值设置变量
NEO4J_URI = args.neo4j_uri or (
    DEFAULT_LOCAL_NEO4J_URI if args.neo4j_target == "local" else DEFAULT_CONTAINER_NEO4J_URI
)
NEO4J_USER = args.neo4j_user
NEO4J_PASSWORD = args.neo4j_password
dataset_name = args.dataset
GRAPH_PATH = args.graph_path if args.graph_path is not None else DEFAULT_GRAPH_PATH
validation_mode = args.validation_mode
template_path = args.template_path if args.template_path is not None else DEFAULT_TEMPLATE_PATH
recovery_mode = args.recovery_mode
target_count = args.target_count
success_per_template = args.success_per_template
max_failures_per_template = args.max_failures_per_template

if not template_path.exists():
    raise FileNotFoundError(f"找不到模板文件: {template_path}")

template_name = template_path.name.lower()
if "agg" in template_name and validation_mode != "agg":
    print(
        f"Warning: 当前模板文件看起来是聚合模板 {template_path.name}，"
        f"但 --validation-mode={validation_mode}"
    )
elif "agg" not in template_name and validation_mode != "no-agg":
    print(
        f"Warning: 当前模板文件看起来是非聚合模板 {template_path.name}，"
        f"但 --validation-mode={validation_mode}"
    )

# 确定是否构建数据库（默认构建，除非指定 --skip-build）
BUILD_DB = not args.skip_build

# 第一步：构建数据库
if BUILD_DB:
    print("=" * 60)
    print("第一步：构建数据库")
    print("=" * 60)
    if not GRAPH_PATH.exists():
        raise FileNotFoundError(f"找不到图文件: {GRAPH_PATH}")

    with Neo4jGraphBuilder(
        uri=NEO4J_URI,
        user=NEO4J_USER,
        password=NEO4J_PASSWORD,
        batch_size=300,
    ) as builder:
        summary = builder.build_from_file(
            file_path=GRAPH_PATH,
            dataset_name=dataset_name,
            recreate_database=True,
        )
        print("数据库构建完成:", summary)
else:
    print("=" * 60)
    print("跳过数据库构建步骤")
    print("=" * 60)

# 第二步：生成查询
print("\n" + "=" * 60)
print("第二步：生成查询")
print("=" * 60)

# 创建生成器
generator = ManageGenerator(
    uri=NEO4J_URI,
    user=NEO4J_USER,
    password=NEO4J_PASSWORD,
    template_path=str(template_path),
    graph_file=str(GRAPH_PATH) if GRAPH_PATH.exists() else None,  # 传入图文件路径，用于在恢复数据库后重新构建
    validation_mode=validation_mode,
    database_recovery_mode=recovery_mode,
)

# 初始化（连接数据库并分析schema）
generator.initialize()

# 生成查询样本
results = generator.generate_samples(
    target_count=target_count,
    operations=["MIX", "CREATE", "DELETE", "SET", "MERGE"],  # 包含 MIX 才会处理模板文件里排在首位的 MIX；不传或传 None 表示所有类型
    success_per_template=success_per_template,
    max_failures_per_template=max_failures_per_template,
    # 开启流式输出：边生成边写入 JSON 文件
    stream_output_path=f"management_query_{dataset_name}.json",
)

# 关闭连接
generator.close()
