"""
Neo4j Management Query Generator (增删改操作查询生成器)
针对增删改操作生成查询，包括前置验证、操作执行和后置验证


"""

import json
import random
import re
import logging
from typing import Dict, List, Any, Optional, Tuple, Set, Union
from dataclasses import dataclass
from neo4j import GraphDatabase

# 导入 query_generator 中的相关类
from .query_generator import (
    SchemaAnalyzer,
    QueryBuilder,
    QueryExecutor,
    DEFAULT_EXCLUDED_RETURN_PROPS,
    DEFAULT_EXCLUDED_LABELS,
    Node,
    Relationship,
    logger
)

# 导入数据库构建器
import sys
from pathlib import Path
# 添加 pipeline 目录到路径，以便导入 db_builder
# manage_generator.py 在 pipeline/query_gen/generator/，需要向上3级到 pipeline
pipeline_dir = Path(__file__).parent.parent.parent
sys.path.insert(0, str(pipeline_dir))
# 直接导入 build_base 模块，避免通过 __init__.py
import importlib.util
build_base_path = pipeline_dir / "db_builder" / "build_base.py"
spec = importlib.util.spec_from_file_location("build_base", build_base_path)
build_base = importlib.util.module_from_spec(spec)
spec.loader.exec_module(build_base)
Neo4jGraphBuilder = build_base.Neo4jGraphBuilder

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class ManagementTemplate:
    """管理操作模板类"""
    operation: str  # 操作类型：CREATE, MERGE, DELETE, SET, FOREACH
    difficulty: int
    title: str
    pre_validation: str  # 前置验证查询（旧格式，兼容性保留）
    template: Union[str, List[str]]  # 操作查询（支持单个字符串或字符串列表，batch格式）
    post_validation: str  # 后置验证查询（旧格式，兼容性保留）
    validation: str  # 验证查询（新格式，在每次 template 查询前后运行）
    parameters: Dict[str, str]  # 参数定义
    example: str
    
    def is_batch(self) -> bool:
        """判断是否为 batch 格式（template 为列表）"""
        return isinstance(self.template, list)
    
    def has_validation(self) -> bool:
        """判断是否有 validation 查询（新格式）"""
        return bool(self.validation and self.validation.strip())


@dataclass
class ManagementQueryResult:
    """管理操作查询结果"""
    operation: str
    difficulty: int
    title: str
    template_id: str  # 基于 operation 和 difficulty 生成
    
    # 前置验证结果（兼容旧格式）
    pre_validation_query: str
    pre_validation_params: Dict[str, Any]
    pre_validation_answer: List[Dict]
    pre_validation_success: bool
    
    # 操作执行结果（支持单个查询或 batch 查询列表）
    template_query: Union[str, List[str]]  # batch 格式时为列表
    template_params: Dict[str, Any]
    template_success: Union[bool, List[bool]]  # batch 格式时为列表
    
    # 后置验证结果（兼容旧格式）
    post_validation_query: str
    post_validation_params: Dict[str, Any]
    post_validation_answer: List[Dict]
    post_validation_success: bool
    
    # 验证查询结果（新格式）：记录每次 validation 查询的结果
    validation_queries: Optional[List[str]] = None  # 每次执行的 validation 查询（已填充参数）
    validation_answers: Optional[List[List[Dict]]] = None  # 每次 validation 查询的结果
    validation_successes: Optional[List[bool]] = None  # 每次 validation 查询是否成功
    validation_errors: Optional[List[Optional[str]]] = None  # 每次 validation 查询的错误信息
    # 顺序：初始 validation -> template[0] -> validation -> template[1] -> validation -> ...
    
    # 有默认值的字段放在最后
    template_queries_executed: Optional[List[str]] = None  # batch 格式时记录所有执行的查询
    # 每个 template 查询的执行结果（与 template_queries_executed 对齐）
    template_answers: Optional[List[List[Dict]]] = None
    overall_success: bool = False  # 整体是否成功（所有查询都成功）
    pre_validation_error: Optional[str] = None  # 错误信息
    template_error: Optional[Union[str, List[str]]] = None  # batch 格式时为列表
    post_validation_error: Optional[str] = None


class ManagementTemplateLoader:
    """管理操作模板加载器"""
    
    def __init__(self, template_path: str):
        self.template_path = template_path
        self.templates: List[ManagementTemplate] = []
    
    def load(self):
        """加载模板文件"""
        logger.info(f"加载管理操作模板文件: {self.template_path}")
        
        with open(self.template_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # 解析 JSON 结构
        for operation_group in data:
            operation = operation_group.get('operation', 'UNKNOWN')
            templates_list = operation_group.get('templates', [])
            
            for template_data in templates_list:
                # 支持 template 为字符串或列表（batch 格式）
                template_field = template_data.get('template', '')
                # 获取 validation 字段（新格式），如果没有则使用空字符串
                validation_query = template_data.get('validation', '')
                # 兼容旧格式：如果没有 validation，尝试使用 pre_validation 和 post_validation
                if not validation_query:
                    pre_val = template_data.get('pre_validation', '')
                    post_val = template_data.get('post_validation', '')
                    # 如果旧格式存在，可以合并或使用其中一个（这里使用 post_validation 作为 validation）
                    validation_query = post_val if post_val else pre_val
                
                # 如果 template 是列表，保持为列表；如果是字符串，保持为字符串
                if isinstance(template_field, list):
                    # batch 格式：template 是字符串列表
                    template = ManagementTemplate(
                        operation=operation,
                        difficulty=template_data.get('difficulty', 1),
                        title=template_data.get('title', ''),
                        pre_validation=template_data.get('pre_validation', ''),
                        template=template_field,  # 保持为列表
                        post_validation=template_data.get('post_validation', ''),
                        validation=validation_query,  # 新格式的 validation
                        parameters=template_data.get('parameters', {}),
                        example=template_data.get('example', '')
                    )
                else:
                    # 单个查询格式：template 是字符串
                    template = ManagementTemplate(
                        operation=operation,
                        difficulty=template_data.get('difficulty', 1),
                        title=template_data.get('title', ''),
                        pre_validation=template_data.get('pre_validation', ''),
                        template=template_field,  # 保持为字符串
                        post_validation=template_data.get('post_validation', ''),
                        validation=validation_query,  # 新格式的 validation
                        parameters=template_data.get('parameters', {}),
                        example=template_data.get('example', '')
                    )
                self.templates.append(template)
        
        logger.info(f"加载了 {len(self.templates)} 个管理操作模板")
    
    def get_templates_by_operation(self, operation: str) -> List[ManagementTemplate]:
        """根据操作类型获取模板"""
        return [t for t in self.templates if t.operation == operation]
    
    def get_all_templates(self) -> List[ManagementTemplate]:
        """获取所有模板"""
        return self.templates


class ManagementQueryBuilder:
    """管理操作查询构建器：根据模板和schema生成具体查询"""
    
    def __init__(
        self,
        schema: SchemaAnalyzer,
        excluded_return_props: Optional[Set[str]] = None,
        excluded_labels: Optional[Set[str]] = None,
        dataset: Optional[str] = None,
        driver = None,
    ):
        self.schema = schema
        self.excluded_return_props: Set[str] = excluded_return_props or set()
        self.excluded_labels: Set[str] = excluded_labels or set()
        self.dataset = dataset
        
        # 复用 QueryBuilder 的逻辑
        self.query_builder = QueryBuilder(
            schema,
            excluded_return_props=excluded_return_props,
            excluded_labels=excluded_labels,
            dataset=dataset,
            driver=driver  # 传递 driver 用于节点采样
        )
    
    def build_queries(
        self, 
        template: ManagementTemplate
    ) -> Tuple[Optional[Union[str, List[str]]], Optional[Union[str, List[str]]], Optional[str], Optional[str], Dict[str, Any]]:
        """
        根据模板构建查询（pre_validation, template, post_validation, validation）
        
        Returns:
            (pre_validation_query, template_query(s), post_validation_query, validation_query, params_used)
            - 如果 template 是 batch 格式，template_query 返回列表
            - validation_query 是新格式的验证查询
            - 如果构建失败，返回的查询为 None
        """
        # 创建一个临时的 Template 对象用于参数生成
        from .query_generator import Template
        
        # 检查验证查询是否包含聚合函数
        # 优先使用新格式的 validation，如果没有则使用旧格式的 pre_validation + post_validation
        validation_query_str = template.validation if template.has_validation() else (template.pre_validation + " " + template.post_validation)
        has_aggregate = any(func in validation_query_str.upper() 
                          for func in ['COUNT', 'SUM', 'AVG', 'MAX', 'MIN', 'COLLECT'])
        
        # 检查是否包含需要数值属性的聚合函数（AVG, SUM）
        has_numeric_aggregate = any(func in validation_query_str.upper() 
                                  for func in ['AVG', 'SUM'])
        
        # 使用 template 字段来生成参数（因为三个查询共享参数）
        # 如果验证查询包含聚合函数，将验证查询合并到模板字符串中，
        # 这样 _is_aggregate_query 方法就能通过检查模板字符串识别出聚合查询
        # 对于 batch 格式，需要将所有 template 查询合并
        if template.is_batch():
            template_str = " ".join(template.template)  # batch 格式：合并所有查询
        else:
            template_str = template.template  # 单个查询格式
        
        if has_aggregate:
            # 将验证查询合并到模板字符串中，以便 _is_aggregate_query 能识别
            template_str = template_str + " " + validation_query_str
        
        temp_template = Template(
            id=f"{template.operation}_{template.difficulty}",
            template=template_str,  # 如果包含聚合函数，这里会包含验证查询
            parameters=template.parameters,
            required_numeric_props=has_numeric_aggregate,  # 如果包含AVG或SUM，需要数值属性
            type=template.operation
        )
        
        # 首先尝试从节点采样来填充相关参数
        params_used = {}
        
        # 获取模板中的 (start, rel, end) 约束，用于保证节点标签按关系语义采样
        constraints = self.query_builder._get_template_constraints(temp_template.template)
        # 先预填 REL，使 GROUP_LABEL/GL 等 end 标签在节点组填充时能按关系的合法 end 采样（避免 Company_Guarantee_Company->Account）
        # MATCH (a:L1),(b:L2) CREATE (a)-[:R1]->(b) 型：R1 必须与 (L1,L2) 匹配，模板中已约定 L1/L2 在 R1 之前，此处不预填 R1，主循环会按顺序先填 L1/L2 再填 R1
        pair_label_params = {'Label1', 'Label2', 'Label3', 'Label4', 'Label5'}
        for start, rel, end in constraints:
            if rel and rel in template.parameters and rel not in params_used:
                if start in pair_label_params and end in pair_label_params:
                    continue  # 两端均为节点对标签，关系类型必须由 (L1,L2) 决定，稍后在主循环中填
                rel_value = self.query_builder._generate_param_value(rel, temp_template, params_used)
                if rel_value is not None:
                    params_used[rel] = rel_value
                break  # 先填一个 REL 即可，用于约束 LABEL/GROUP_LABEL
        
        # 识别需要从同一节点获取的参数组
        node_param_groups = self.query_builder._identify_node_param_groups(temp_template)
        
        # 为每个节点参数组采样节点并填充参数
        for group in node_param_groups:
            if not self.query_builder._fill_params_from_sampled_node(temp_template, group, params_used):
                # 如果采样失败，回退到原来的方法
                logger.debug(f"节点采样失败，回退到原方法: {group}")
        
        # 生成剩余参数
        for param_name, param_type in template.parameters.items():
            # 如果参数已经填充，跳过
            if param_name in params_used:
                continue
            
            # AID1-5/BID1-5 必须从 L1+PROP_ID1 / L2+PROP_ID2 的 sample_values 采样，不能合成 id_
            # 若 PROP_ID1/PROP_ID2 尚未填充则优先生成，否则 _generate_param_value('AID'/'BID') 会回退到合成值
            if param_name.startswith('AID') or param_name == 'AID':
                for dep in ('Label1', 'PROP_ID1'):
                    if dep in template.parameters and dep not in params_used:
                        dep_val = self.query_builder._generate_param_value(dep, temp_template, params_used)
                        if dep_val is not None:
                            params_used[dep] = dep_val
            if param_name.startswith('BID') or param_name == 'BID':
                for dep in ('Label2', 'PROP_ID2'):
                    if dep in template.parameters and dep not in params_used:
                        dep_val = self.query_builder._generate_param_value(dep, temp_template, params_used)
                        if dep_val is not None:
                            params_used[dep] = dep_val
            
            # VALUE/VALUE1-5 与 PROP_ID 绑定时（如 {$PROP_ID: $VALUE1}）必须从 PROP_ID 对应属性采样，
            # 故优先生成 PROP_ID 和 LABEL/L1/L 等，避免 VALUE 采到 PROP 的 sample_values（如 loanId 采成 loanUsage 的值）
            if param_name in ('VALUE', 'VALUE1', 'VALUE2', 'VALUE3', 'VALUE4', 'VALUE5'):
                for dep in ('PROP_ID', 'LABEL', 'Label', 'Label1', 'Label2', 'Label3', 'Label4', 'Label5'):
                    if dep in template.parameters and dep not in params_used:
                        dep_val = self.query_builder._generate_param_value(dep, temp_template, params_used)
                        if dep_val is not None:
                            params_used[dep] = dep_val
            
            # 若当前参数是某约束的 end 标签（如 L1），先填充该约束的 rel（如 R），
            # 保证 b 等节点标签从关系 R 的合法 end 中采样（如 Company_Guarantee_Company -> Company）
            for start, rel, end in constraints:
                if end == param_name and rel and rel not in params_used:
                    rel_value = self.query_builder._generate_param_value(rel, temp_template, params_used)
                    if rel_value is not None:
                        params_used[rel] = rel_value
                    break
            
            # 关系类型 R/R1 由模板参数顺序保证：模板中 L1、L2 已写在 R、R1 之前，主循环按 template.parameters 顺序填充，故填 R 时 L1/L2 已在 params_used 中，_generate_param_value 会按 (L1,R,L2) 约束选合法关系。
            
            # 处理 list 类型参数
            if param_type == "list":
                value = self._generate_list_param(param_name, template, params_used)
            else:
                # 检查是否为带数字的参数（VALUE1-5, VAL1-5, AID1-5, BID1-5等）
                value = self._generate_indexed_param(param_name, param_type, temp_template, params_used)
                if value is None:
                    # 回退到原有的参数生成方法
                    value = self.query_builder._generate_param_value(
                        param_name, 
                        temp_template, 
                        params_used
                    )
            if value is None:
                logger.warning(f"无法生成参数 {param_name}，跳过该模板")
                return None, None, None, None, {}
            params_used[param_name] = value
        
        # 替换查询中的参数
        pre_validation_query = self._replace_parameters(
            template.pre_validation, 
            params_used
        )
        
        # 处理 template 查询（支持 batch 格式）
        if template.is_batch():
            # batch 格式：替换每个查询中的参数
            template_queries = [
                self._replace_parameters(query, params_used)
                for query in template.template
            ]
            template_query = template_queries
        else:
            # 单个查询格式
            template_query = self._replace_parameters(
                template.template, 
                params_used
            )
        
        post_validation_query = self._replace_parameters(
            template.post_validation, 
            params_used
        )
        
        # 构建新格式的 validation 查询
        validation_query = None
        if template.has_validation():
            validation_query = self._replace_parameters(
                template.validation,
                params_used
            )
        
        return pre_validation_query, template_query, post_validation_query, validation_query, params_used
    
    def _generate_indexed_param(self, param_name: str, param_type: str, 
                                temp_template, current_params: Dict[str, Any]) -> Optional[Any]:
        """
        生成带数字索引的参数值（VALUE1-5, VAL1-5, AID1-5, BID1-5等）
        这些参数遵循相同的模式，只是索引不同
        """
        import re
        
        # 匹配带数字的参数名：VALUE1, VAL2, AID3, BID4等
        match = re.match(r'^([A-Z_]+)(\d+)$', param_name)
        if not match:
            return None  # 不是带数字的参数，返回None让调用者使用原有方法
        
        base_name = match.group(1)  # 基础名称：VALUE, VAL, AID, BID等
        index = int(match.group(2))  # 索引：1, 2, 3, 4, 5等
        
        # 处理 VALUE1-5, VAL1-5, Val1-5 等（对应 VALUE, VAL, Val）
        if base_name in ('VALUE', 'VAL', 'Val'):
            # 使用原有的 VALUE/VAL/Val 生成逻辑（从对应 LABEL 的 PROP 采样，保证每行不同）
            base_param = 'VALUE' if base_name == 'VALUE' else ('VAL' if base_name == 'VAL' else 'Val')
            if base_param in current_params and base_name != 'Val':
                base_value = current_params[base_param]
                # 如果是数值类型，生成不同的数值
                if isinstance(base_value, (int, float)):
                    if param_type in ('integer', 'long', 'int'):
                        return base_value + index * random.randint(1, 10)
                    elif param_type in ('float', 'double'):
                        return base_value + index * random.uniform(0.1, 1.0)
                # 如果是字符串类型，生成不同的字符串
                elif isinstance(base_value, str):
                    return f"{base_value}_{index}"
            # 从对应 LABEL 的 PROP 采样（Val1..Val5 每行不同）
            return self.query_builder._generate_param_value(base_param, temp_template, current_params)
        
        # 处理 AID1-5, BID1-5 等（对应 AID, BID）
        elif base_name in ('AID', 'BID', 'CID'):
            # 使用原有的 AID/BID 生成逻辑
            return self.query_builder._generate_param_value(base_name, temp_template, current_params)
        
        # 处理其他带数字的参数（如 ID1-5, NAME1-5等）
        elif base_name in ('ID', 'NAME', 'GID', 'MID'):
            return self.query_builder._generate_param_value(base_name, temp_template, current_params)
        
        # 其他未知的带数字参数，返回None让调用者使用原有方法
        return None
    
    def _generate_list_param(self, param_name: str, template: ManagementTemplate, 
                             current_params: Dict[str, Any]) -> Optional[List[Any]]:
        """生成列表类型参数的值"""
        # 根据参数名推断列表元素的类型
        if param_name in ('LIST', 'IDS', 'A_IDS', 'B_IDS'):
            # 这些参数通常是 ID 列表，从数据库中采样一些 ID 值
            # 尝试从已生成的参数中获取标签信息
            label = None
            for label_key in ['LABEL', 'Label', 'Label1', 'Label2', 'Label3', 'Label4', 'Label5',
                              'GroupLabel', 'StartLabel', 'EndLabel', 'RefLabel']:
                if label_key in current_params:
                    label = current_params[label_key]
                    break
            
            if label and label in self.schema.labels:
                # 从该标签的节点中采样一些 id 值
                label_info = self.schema.labels[label]
                if 'id' in label_info.properties:
                    id_prop = label_info.properties['id']
                    if id_prop.sample_values:
                        # 随机选择 3-5 个 ID 值
                        available_count = len(id_prop.sample_values)
                        if available_count > 0:
                            sample_size = min(random.randint(3, 5), available_count)
                            if sample_size == available_count:
                                return id_prop.sample_values.copy()
                            else:
                                return random.sample(id_prop.sample_values, sample_size)
            
            # 如果没有找到，生成一些默认值
            # 根据参数名判断是字符串列表还是数字列表
            if param_name == 'LIST':
                # LIST 通常用于 FOREACH，可能是数字或字符串列表
                # 生成简单的数字列表
                return [1, 2, 3]
            else:
                # IDS 通常是字符串 ID 列表
                return ['id1', 'id2', 'id3']
        
        # 默认返回空列表
        logger.warning(f"无法生成列表参数 {param_name}，使用默认值")
        return []
    
    def _replace_parameters(self, query_template: str, params: Dict[str, Any]) -> str:
        """替换查询模板中的参数"""
        query = query_template
        replacements = {}
        
        # 不需要加引号的参数名（标签、属性名、关系类型等）
        no_quote_params = {
            # Labels (fully descriptive only; legacy shorthand L/L1/L2/GL/SL/EL/RL removed)
            'LABEL', 'LABEL1', 'LABEL2', 'LABEL3', 'LABEL4',
            'Label', 'Label1', 'Label2', 'Label3', 'Label4', 'Label5',
            'START_LABEL', 'END_LABEL', 'GROUP_LABEL', 'TARGET_LABEL',
            'StartLabel', 'EndLabel', 'GroupLabel', 'RefLabel',
            # Properties (names only; not values)
            'PROP', 'PROP1', 'PROP2', 'PROP_ID', 'PROP_ID1', 'PROP_ID2',
            'Prop', 'Prop1', 'Prop2',
            'TARGET_PROP_ID', 'TARGET_PROP_ID1', 'TARGET_PROP_ID2',
            'GROUP_PROP', 'FILTER_PROP', 'NODE_PROP', 'START_PROP',
            'BaseProp', 'StartProp', 'NumProp', 'GroupProp',
            'UPDATE_PROP', 'RET_PROP', 'REF_PROP',
            # Relationships
            'REL', 'REL_TYPE', 'REL1', 'REL2', 'REL3',
            'Rel', 'Rel1', 'Rel2', 'Rel3',
            'REL_PROP', 'RelProp',
            # Control / numeric helpers (names, not values)
            'MIN_HOPS', 'MAX_HOPS', 'D1', 'D2', 'D3', 'OP', 'OP1', 'OP2',
            'AGG_FUNC', 'AGG_FUNC1', 'AGG_FUNC2',
            'NUM_PROP', 'NUM_PROP1', 'NUM_PROP2',
        }
        
        # 列表参数名
        list_params = {'LIST', 'IDS', 'A_IDS', 'B_IDS'}
        
        def escape_string(s: str) -> str:
            """转义字符串中的单引号"""
            return s.replace("'", "\\'")
        
        for param_name, value in params.items():
            # 替换 $PARAM_NAME 格式的参数
            if param_name in list_params and isinstance(value, list):
                # 列表参数：转换为 Cypher 列表格式
                if value and isinstance(value[0], str):
                    # 字符串列表：转义单引号并加引号
                    list_str = ', '.join(f"'{escape_string(str(v))}'" for v in value)
                else:
                    # 数字列表或其他类型
                    list_str = ', '.join(str(v) for v in value)
                replacement = f"[{list_str}]"
            elif param_name in no_quote_params:
                # 标签、属性名、关系类型等：直接替换，不需要引号
                replacement = str(value)
            elif isinstance(value, str):
                # 字符串值：转义单引号并加引号
                replacement = f"'{escape_string(value)}'"
            elif isinstance(value, (int, float)) and not isinstance(value, bool):
                # 数值类型：直接替换，不需要引号
                replacement = str(value)
            elif isinstance(value, bool):
                # 布尔值：直接使用 true/false（Cypher关键字）
                replacement = str(value).lower()
            else:
                # 其他类型：转换为字符串
                replacement = str(value)
            
            replacements[f'${param_name}'] = replacement
        
        # 按照键长度倒序替换，避免短键被先替换
        sorted_keys = sorted(replacements.keys(), key=len, reverse=True)
        for key in sorted_keys:
            query = query.replace(key, replacements[key])
        
        # 修复量化路径模式的语法：Neo4j 5 使用逗号而不是两个点
        # 将 {数字..数字} 替换为 {数字,数字}
        # 注意：只替换花括号内的，不替换 *数字..数字 这种可变长度关系语法
        # 匹配 {数字..数字} 模式（量化路径模式）
        query = re.sub(r'\{(\d+)\.\.(\d+)\}', r'{\1,\2}', query)
        
        # 对于 dataset 为 "mcp" 或 "multi_fin" 的情况，为 concept 节点添加 id 属性过滤
        if self.dataset in ("mcp", "multi_fin"):
            query = self.query_builder._add_concept_id_filter(query, params)
        
        return query


class ManageGenerator:
    """管理操作查询生成器主类"""
    
    def __init__(
        self,
        uri: str = "bolt://localhost:7687",
        user: str = "neo4j",
        password: str = "password",
        template_path: str = "query_template/template_managemet_batch.json",  # 默认使用新格式的 batch 模板文件
        exclude_internal_id_as_return: bool = True,
        dataset: Optional[str] = None,
        database_backup_path: Optional[str] = None,
        database_name: str = "neo4j",
        neo4j_admin_path: Optional[str] = None,
        graph_file: Optional[str] = None,
        validation_mode: str = "agg",
        database_recovery_mode: str = "transaction-rollback",
    ):
        """
        初始化管理操作查询生成器
        
        Args:
            uri: Neo4j连接URI
            user: 用户名
            password: 密码
            template_path: 模板文件路径
            exclude_internal_id_as_return: 是否在返回属性中排除内部ID字段
            dataset: 数据集名称
            database_backup_path: 兼容旧参数，当前不使用容器/neo4j-admin恢复
            database_name: 数据库名称，默认为"neo4j"
            neo4j_admin_path: 兼容旧参数，当前不使用容器/neo4j-admin恢复
            graph_file: 图文件路径（.gpickle或.graphml），用于在恢复数据库后重新构建数据库
            database_recovery_mode: 数据库恢复方式：
                transaction-rollback=样本在事务内执行并回滚（默认，高效且不依赖容器）
                local-rebuild=使用 Neo4jGraphBuilder 从 graph_file 清库重建
                none=不额外恢复
        """
        allowed_recovery_modes = {"transaction-rollback", "local-rebuild", "none"}
        if database_recovery_mode not in allowed_recovery_modes:
            raise ValueError(
                f"不支持的 database_recovery_mode: {database_recovery_mode}，"
                f"可选值: {sorted(allowed_recovery_modes)}"
            )

        self.uri = uri
        self.user = user
        self.password = password
        self.template_path = template_path
        self.exclude_internal_id_as_return = exclude_internal_id_as_return
        self.dataset = dataset
        # 验证模式：agg=原有聚合验证；no-agg=为每条 template 生成对应的非聚合验证
        self.validation_mode = validation_mode
        
        self.excluded_return_props: Set[str] = (
            set(DEFAULT_EXCLUDED_RETURN_PROPS) if exclude_internal_id_as_return else set()
        )
        
        # 初始化组件
        self.driver = None
        self.schema = None
        self.template_loader = None
        self.builder = None
        self.executor = None
        
        # 结果存储
        self.results: List[ManagementQueryResult] = []
        
        # 数据库恢复相关
        self.database_backup_path: Optional[str] = database_backup_path
        self.neo4j_admin_path: Optional[str] = neo4j_admin_path
        self.database_recovery_mode = database_recovery_mode
        self.use_database_restore: bool = database_recovery_mode != "none"
        self.database_name = database_name  # 保存数据库名称
        self.graph_file: Optional[str] = graph_file  # 图文件路径，用于在恢复数据库后重新构建
        
        # 数据库构建器实例（用于恢复数据库）
        self.db_builder = None
    
    def connect(self):
        """连接到Neo4j数据库"""
        logger.info(f"连接到Neo4j: {self.uri}")
        self.driver = GraphDatabase.driver(self.uri, auth=(self.user, self.password))
        # 验证连接
        with self.driver.session() as session:
            session.run("RETURN 1")
        logger.info("连接成功")
    
    def initialize(self):
        """初始化所有组件"""
        if not self.driver:
            self.connect()
        
        # 初始化数据库构建器（用于恢复数据库）
        self.db_builder = Neo4jGraphBuilder(
            uri=self.uri,
            user=self.user,
            password=self.password
        )
        
        # 分析Schema
        self.schema = SchemaAnalyzer(self.driver)
        self.schema.analyze()

        # 从 YAML schema 文件加载权威三元组约束（覆盖 DB 噪声）
        if self.dataset:
            self.schema.load_schema_from_yaml(self.dataset)

        # 加载模板
        self.template_loader = ManagementTemplateLoader(self.template_path)
        self.template_loader.load()
        
        # 初始化其他组件
        excluded_labels = set(DEFAULT_EXCLUDED_LABELS)
        if self.dataset in ("mcp", "multi_fin"):
            excluded_labels.update({"passage"})
        
        self.builder = ManagementQueryBuilder(
            self.schema,
            excluded_return_props=self.excluded_return_props,
            excluded_labels=excluded_labels,
            dataset=self.dataset,
            driver=self.driver  # 传递 driver 用于节点采样
        )
        self.executor = QueryExecutor(self.driver)
    
    def restore_database(self):
        """
        恢复数据库到初始状态
        
        不调用容器或 neo4j-admin restore。恢复方式由 database_recovery_mode 控制：
        - transaction-rollback：样本级恢复依赖事务 rollback，这里不做额外操作。
        - local-rebuild：使用 Neo4jGraphBuilder 清空数据库，并从 graph_file 重新构建。
        - none：不做恢复。
        """
        if not self.use_database_restore:
            return

        if self.database_recovery_mode == "transaction-rollback":
            logger.info("当前恢复模式为 transaction-rollback，样本执行结束时已通过事务回滚恢复数据库")
            return
        
        try:
            # 确保数据库构建器已初始化
            if not self.db_builder:
                self.db_builder = Neo4jGraphBuilder(
                    uri=self.uri,
                    user=self.user,
                    password=self.password
                )
            # local-rebuild：如果提供了 graph_file，直接由 build_from_file 负责清空并重建。
            if self.graph_file:
                graph_path = Path(self.graph_file)
                if graph_path.exists():
                    logger.info(f"正在使用本地 Neo4jGraphBuilder 从图文件重建数据库: {graph_path}")
                    summary = self.db_builder.build_from_file(
                        file_path=graph_path,
                        dataset_name=self.dataset,
                        recreate_database=True,
                    )
                    logger.info(f"数据库重新构建完成: {summary}")
                else:
                    logger.warning(f"图文件不存在: {graph_path}，跳过数据库重建")
            else:
                logger.info("未提供 graph_file，仅使用 Neo4jGraphBuilder 清空数据库")
                self.db_builder._prepare_database(recreate=True)
            
        except Exception as e:
            logger.warning(f"数据库恢复过程中发生异常: {e}，继续执行...")
            # 不抛出异常，允许继续执行

    def _execute_query_in_tx(
        self,
        tx,
        query: str,
        allow_empty: bool = False,
    ) -> Tuple[bool, List[Dict], Optional[str]]:
        """
        在调用方提供的事务里执行查询，不提交事务。

        管理查询生成需要 validation 能看到刚执行的写操作，但样本结束后又要恢复
        初始状态；因此同一个样本内所有查询共享一个事务，最终由调用方 rollback。
        """
        try:
            query_with_limit = self.executor._add_limit_if_needed(query) if self.executor else query
            result = tx.run(query_with_limit)

            records = []
            record_count = 0

            def _process_value(value):
                if isinstance(value, Node):
                    try:
                        return dict(value)
                    except (TypeError, AttributeError):
                        try:
                            return dict(value.items())
                        except Exception:
                            return {k: v for k, v in value.items()}
                if isinstance(value, Relationship):
                    try:
                        return dict(value)
                    except (TypeError, AttributeError):
                        try:
                            return dict(value.items())
                        except Exception:
                            return {k: v for k, v in value.items()}
                if hasattr(value, '__iter__') and not isinstance(value, (str, dict, bytes)):
                    try:
                        if isinstance(value, (list, tuple)):
                            return [_process_value(item) for item in value]
                        return dict(value)
                    except Exception:
                        return str(value)
                return value

            max_results = self.executor.max_results if self.executor else 1000
            for record in result:
                if record_count >= max_results:
                    logger.warning(f"查询结果超过最大限制 ({max_results})，已截断")
                    result.consume()
                    break

                record_dict = {key: _process_value(record[key]) for key in record.keys()}
                records.append(record_dict)
                record_count += 1

            if records or allow_empty:
                return True, records, None
            return False, [], "查询结果为空"

        except Exception as e:
            err_msg = str(e)
            if 'transaction' in err_msg.lower() and ('timeout' in err_msg.lower() or 'time' in err_msg.lower()):
                timeout = self.executor.timeout if self.executor else "unknown"
                return False, [], f"查询执行超时 ({timeout}秒)"
            return False, [], err_msg

    def _execute_sample_with_rollback(
        self,
        template: ManagementTemplate,
        template_query: Union[str, List[str]],
        pre_query: Optional[str],
        post_query: Optional[str],
        validation_query: Optional[str],
        params_used: Dict[str, Any],
        has_validation: bool,
        is_batch: bool,
    ) -> Dict[str, Any]:
        """
        执行单个生成样本，并在样本结束后回滚所有写入。
        """
        if not self.driver:
            raise RuntimeError("Neo4j driver 未初始化")

        validation_queries_list: List[str] = []
        validation_answers_list: List[List[Dict]] = []
        validation_successes_list: List[bool] = []
        validation_errors_list: List[Optional[str]] = []

        pre_success, pre_answer, pre_error = True, [], None
        post_success, post_answer, post_error = True, [], None
        template_success: Union[bool, List[bool]] = False
        template_error: Optional[Union[str, List[Optional[str]]]] = None
        template_successes: List[bool] = []
        template_errors: List[Optional[str]] = []
        template_executed_queries: List[str] = []
        template_answers: List[List[Dict]] = []

        timeout = self.executor.timeout if self.executor else 298

        with self.driver.session() as session:
            tx = session.begin_transaction(timeout=timeout)
            try:
                if has_validation and validation_query:
                    v_success, v_answer, v_error = self._execute_query_in_tx(
                        tx,
                        validation_query,
                        allow_empty=True,
                    )
                    validation_queries_list.append(validation_query)
                    validation_answers_list.append(v_answer)
                    validation_successes_list.append(v_success)
                    validation_errors_list.append(v_error)
                    if not v_success:
                        return {
                            "pre_success": pre_success,
                            "pre_answer": pre_answer,
                            "pre_error": pre_error,
                            "post_success": post_success,
                            "post_answer": post_answer,
                            "post_error": post_error,
                            "template_success": template_success,
                            "template_successes": template_successes,
                            "template_error": template_error,
                            "template_errors": template_errors,
                            "template_executed_queries": template_executed_queries,
                            "template_answers": template_answers,
                            "validation_queries_list": validation_queries_list,
                            "validation_answers_list": validation_answers_list,
                            "validation_successes_list": validation_successes_list,
                            "validation_errors_list": validation_errors_list,
                            "overall_success": False,
                        }

                if not has_validation and pre_query and pre_query.strip():
                    pre_success, pre_answer, pre_error = self._execute_query_in_tx(
                        tx,
                        pre_query,
                        allow_empty=True,
                    )

                if is_batch:
                    template_queries_list = template_query if isinstance(template_query, list) else [template_query]

                    for idx, template_q in enumerate(template_queries_list, start=1):
                        t_success, t_answer, t_error = self._execute_query_in_tx(
                            tx,
                            template_q,
                            allow_empty=True,
                        )
                        template_successes.append(t_success)
                        template_errors.append(t_error)
                        template_executed_queries.append(template_q)
                        template_answers.append(t_answer)

                        if not t_success:
                            continue

                        if has_validation:
                            if self.validation_mode == "no-agg" and template.has_validation():
                                v_template = template.validation or ""
                                v_template_idx = self._adapt_validation_for_index(v_template, idx)
                                v_query = self.builder._replace_parameters(v_template_idx, params_used)
                            else:
                                v_query = validation_query
                            v_success, v_answer, v_error = self._execute_query_in_tx(
                                tx,
                                v_query,
                                allow_empty=True,
                            )
                            validation_queries_list.append(v_query)
                            validation_answers_list.append(v_answer)
                            validation_successes_list.append(v_success)
                            validation_errors_list.append(v_error)

                    template_success = all(template_successes)
                    template_error = template_errors if not template_success else None
                else:
                    t_success, t_answer, t_error = self._execute_query_in_tx(
                        tx,
                        template_query,
                        allow_empty=True,
                    )
                    template_success = t_success
                    template_error = t_error
                    template_executed_queries = [template_query]
                    template_answers = [t_answer]

                    if has_validation and t_success and validation_query:
                        v_success, v_answer, v_error = self._execute_query_in_tx(
                            tx,
                            validation_query,
                            allow_empty=True,
                        )
                        validation_queries_list.append(validation_query)
                        validation_answers_list.append(v_answer)
                        validation_successes_list.append(v_success)
                        validation_errors_list.append(v_error)

                if not has_validation and post_query and post_query.strip():
                    post_success, post_answer, post_error = self._execute_query_in_tx(
                        tx,
                        post_query,
                        allow_empty=True,
                    )

                if has_validation:
                    all_validations_success = all(validation_successes_list) if validation_successes_list else True
                    overall_success = bool(template_success) and all_validations_success
                else:
                    overall_success = bool(pre_success and template_success and post_success)

                return {
                    "pre_success": pre_success,
                    "pre_answer": pre_answer,
                    "pre_error": pre_error,
                    "post_success": post_success,
                    "post_answer": post_answer,
                    "post_error": post_error,
                    "template_success": template_success,
                    "template_successes": template_successes,
                    "template_error": template_error,
                    "template_errors": template_errors,
                    "template_executed_queries": template_executed_queries,
                    "template_answers": template_answers,
                    "validation_queries_list": validation_queries_list,
                    "validation_answers_list": validation_answers_list,
                    "validation_successes_list": validation_successes_list,
                    "validation_errors_list": validation_errors_list,
                    "overall_success": overall_success,
                }
            finally:
                tx.rollback()
    
    def generate_samples(
        self,
        target_count: Optional[int] = None,
        max_attempts_multiplier: int = 10,
        max_failures_per_template: int = 100,
        operations: Optional[List[str]] = None,
        success_per_template: int = 5,
        stream_output_path: Optional[str] = None,
    ) -> List[ManagementQueryResult]:
        """
        生成管理操作查询样本
        
        Args:
            target_count: 目标样本数量，默认为边数/16
            max_attempts_multiplier: 最大尝试次数倍数
            max_failures_per_template: 每个模板的最大连续失败次数
            operations: 要生成的操作类型列表，None表示所有操作
            success_per_template: 每个模板需要生成的成功查询数量
        
        Returns:
            ManagementQueryResult列表
        """
        if not self.schema:
            self.initialize()
        
        # 获取目标数量
        if target_count is None:
            target_count = max(1, self.schema.total_edges // 16)
        
        max_attempts = target_count * max_attempts_multiplier
        
        logger.info(f"开始生成管理操作查询，目标数量: {target_count}, 最大尝试次数: {max_attempts}")
        
        # 获取模板
        all_templates = self.template_loader.get_all_templates()
        if operations:
            all_templates = [t for t in all_templates if t.operation in operations]
        
        if not all_templates:
            logger.error("没有可用的模板")
            return []
        
        logger.info(f"可用模板数量: {len(all_templates)}")
        
        self.results = []
        attempts = 0
        
        # 跟踪每个模板的使用情况
        template_stats = {}
        for index, template in enumerate(all_templates):
            template_id = f"{template.operation}_{template.difficulty}_{index}"
            template_stats[template_id] = {
                'template': template,
                'success_count': 0,
                'failure_count': 0,
                'usage_count': 0
            }

        # 流式输出相关
        stream_file = None
        first_stream_record = True
        if stream_output_path:
            stream_file = open(stream_output_path, 'w', encoding='utf-8')
            stream_file.write('[\n')
        
        try:
            round_index = 0
            while len(self.results) < target_count and attempts < max_attempts:
                round_index += 1
                round_progress = False
                active_templates = 0

                logger.info(
                    f"开始第 {round_index} 轮模板采样，"
                    f"当前已生成 {len(self.results)}/{target_count}"
                )

                for index, template in enumerate(all_templates):
                    if len(self.results) >= target_count or attempts >= max_attempts:
                        break

                    template_id = f"{template.operation}_{template.difficulty}_{index}"
                    stats = template_stats[template_id]

                    if stats['failure_count'] >= max_failures_per_template:
                        continue

                    active_templates += 1
                    round_template_success = 0

                    logger.info(
                        f"第 {round_index} 轮处理模板 "
                        f"[{template.operation}] difficulty={template.difficulty}: {template.title}"
                    )

                    while round_template_success < success_per_template:
                        if len(self.results) >= target_count or attempts >= max_attempts:
                            break

                        if stats['failure_count'] >= max_failures_per_template:
                            logger.warning(
                                f"模板 {template_id} 连续失败 {stats['failure_count']} 次，跳过该模板"
                            )
                            break

                        attempts += 1
                        stats['usage_count'] += 1

                        build_result = self.builder.build_queries(template)
                        if len(build_result) == 5:
                            pre_query, template_query, post_query, validation_query, params_used = build_result
                        else:
                            pre_query, template_query, post_query, params_used = build_result
                            validation_query = None

                        if not template_query:
                            stats['failure_count'] += 1
                            logger.debug(f"构建查询失败: {template_id}")
                            continue

                        has_validation = template.has_validation() and validation_query
                        is_batch = template.is_batch()

                        if is_batch:
                            template_queries_to_check = template_query if isinstance(template_query, list) else [template_query]
                            validation_to_check = validation_query if has_validation else ''
                            has_id_agg = (
                                self._has_id_aggregate(pre_query) or
                                self._has_id_aggregate(post_query) or
                                self._has_id_aggregate(validation_to_check) or
                                any(self._has_id_aggregate(q) for q in template_queries_to_check)
                            )
                        else:
                            validation_to_check = validation_query if has_validation else ''
                            has_id_agg = (
                                self._has_id_aggregate(pre_query) or
                                self._has_id_aggregate(template_query) or
                                self._has_id_aggregate(post_query) or
                                self._has_id_aggregate(validation_to_check)
                            )

                        if has_id_agg:
                            stats['failure_count'] += 1
                            logger.debug(f"查询包含针对 ID 属性的聚合，跳过该样本: {template_id}")
                            continue

                        valid, validation_err = self._validate_management_queries(template_query)
                        if not valid:
                            stats['failure_count'] += 1
                            logger.debug(f"管理查询校验未通过，跳过该样本: {template_id} — {validation_err}")
                            continue

                        execution = self._execute_sample_with_rollback(
                            template=template,
                            template_query=template_query,
                            pre_query=pre_query,
                            post_query=post_query,
                            validation_query=validation_query,
                            params_used=params_used,
                            has_validation=has_validation,
                            is_batch=is_batch,
                        )
                        pre_success = execution["pre_success"]
                        pre_answer = execution["pre_answer"]
                        pre_error = execution["pre_error"]
                        post_success = execution["post_success"]
                        post_answer = execution["post_answer"]
                        post_error = execution["post_error"]
                        template_success = execution["template_success"]
                        template_successes = execution["template_successes"]
                        template_error = execution["template_error"]
                        template_executed_queries = execution["template_executed_queries"]
                        template_answers = execution["template_answers"]
                        validation_queries_list = execution["validation_queries_list"]
                        validation_answers_list = execution["validation_answers_list"]
                        validation_successes_list = execution["validation_successes_list"]
                        validation_errors_list = execution["validation_errors_list"]
                        overall_success = execution["overall_success"]

                        if overall_success:
                            result = ManagementQueryResult(
                                operation=template.operation,
                                difficulty=template.difficulty,
                                title=template.title,
                                template_id=template_id,
                                pre_validation_query=pre_query or '',
                                pre_validation_params=params_used,
                                pre_validation_answer=pre_answer,
                                pre_validation_success=pre_success,
                                pre_validation_error=pre_error,
                                template_query=template_query,
                                template_params=params_used,
                                template_success=template_success if not is_batch else template_successes,
                                template_queries_executed=template_executed_queries,
                                template_answers=template_answers,
                                template_error=template_error,
                                post_validation_query=post_query or '',
                                post_validation_params=params_used,
                                post_validation_answer=post_answer,
                                post_validation_success=post_success,
                                post_validation_error=post_error,
                                validation_queries=validation_queries_list if has_validation else None,
                                validation_answers=validation_answers_list if has_validation else None,
                                validation_successes=validation_successes_list if has_validation else None,
                                validation_errors=validation_errors_list if has_validation else None,
                                overall_success=overall_success
                            )

                            self.results.append(result)
                            stats['success_count'] += 1
                            stats['failure_count'] = 0
                            round_template_success += 1
                            round_progress = True

                            if stream_file:
                                record = self._build_export_record(result)
                                if not first_stream_record:
                                    stream_file.write(',\n')
                                formatted_json = json.dumps(record, ensure_ascii=False, indent=2, default=str)
                                indented_lines = []
                                for line in formatted_json.split('\n'):
                                    indented_lines.append('  ' + line)
                                stream_file.write('\n'.join(indented_lines))
                                stream_file.flush()
                                first_stream_record = False

                            logger.info(
                                f"成功生成查询 [{len(self.results)}/{target_count}]: "
                                f"[{template.operation}] difficulty={template.difficulty} "
                                f"(本轮模板成功: {round_template_success}/{success_per_template}, "
                                f"累计成功: {stats['success_count']})"
                            )
                        else:
                            stats['failure_count'] += 1
                            failure_reasons = []
                            if has_validation:
                                if validation_successes_list and not all(validation_successes_list):
                                    failed_validations = [i for i, s in enumerate(validation_successes_list) if not s]
                                    failure_reasons.append(f"validation失败: 索引 {failed_validations}")
                            else:
                                if not pre_success:
                                    failure_reasons.append(f"pre_validation失败: {pre_error}")
                                if not post_success:
                                    failure_reasons.append(f"post_validation失败: {post_error}")
                            if not template_success:
                                failure_reasons.append(f"template失败: {template_error}")

                            logger.warning(f"查询执行失败 [{template_id}]: {', '.join(failure_reasons)}")

                    if round_template_success > 0:
                        logger.info(
                            f"模板 {template_id} 第 {round_index} 轮完成，"
                            f"本轮成功生成 {round_template_success} 个查询，累计 {stats['success_count']} 个"
                        )
                    elif stats['failure_count'] >= max_failures_per_template:
                        logger.warning(
                            f"模板 {template_id} 因连续失败过多而失活，累计成功生成 {stats['success_count']} 个查询"
                        )

                if active_templates == 0:
                    logger.warning("所有模板都已失活，提前停止生成")
                    break

                if not round_progress:
                    logger.warning("本轮没有生成任何成功查询，提前停止以避免空转")
                    break
        finally:
            if stream_file:
                stream_file.write('\n]\n')
                stream_file.close()
        
        logger.info(f"生成完成，成功生成 {len(self.results)} 个管理操作查询 (尝试 {attempts} 次)")
        
        # 输出统计信息
        successful_templates = [s for s in template_stats.values() if s['success_count'] > 0]
        failed_templates = [s for s in template_stats.values() if s['success_count'] == 0 and s['usage_count'] > 0]
        
        logger.info(f"模板覆盖统计: 成功 {len(successful_templates)} 个, 失败 {len(failed_templates)} 个")
        
        return self.results
    
    @staticmethod
    def _is_id_property(prop_name: str) -> bool:
        """判断属性名是否为 ID 相关属性（与 QueryBuilder 中逻辑保持一致）"""
        prop_lower = prop_name.lower()
        # 以 id 结尾（loanId, userId, user_id 等）
        if prop_lower.endswith("id") or prop_lower.endswith("_id"):
            return True
        # 刚好等于 id
        if prop_lower == "id":
            return True
        return False

    def _validate_management_queries(
        self, template_query: Union[str, List[str]]
    ) -> Tuple[bool, Optional[str]]:
        """
        校验生成的管理查询是否合法，严格对齐 schema 的三元组约束：

        1) 节点属性必须属于其 label（如 Account { companyId } 非法）
        2) 任意关系模式 (a)-[:REL]->(b) / (a)<-[:REL]-(b) / (a)-[:REL]-(b) 的
           (start_label, rel_type, end_label) 必须存在于 schema.triplets 中：
           - 标签可来自模式内 (var:Label) 注解，或查询其他位置对同一变量的标签绑定
             (如 MATCH (n:Account) ... WHERE NOT (n)-[:Person_Invest_Company]->(:Account))
           - 对于无向关系 `-[:REL]-`，(start,rel,end) 或其反向 (end,rel,start) 之一
             在 triplets 中即视为合法
        """
        import re
        if not self.schema:
            return True, None
        queries = (
            template_query if isinstance(template_query, list) else [template_query]
        )
        triplets = getattr(self.schema, "triplets", set()) or set()
        labels = getattr(self.schema, "labels", {}) or {}

        # Cypher 标识符：字母/数字/下划线，首字符非数字（近似）
        var_re = r'[A-Za-z_][A-Za-z0-9_]*'
        # 节点模式：( [var] [:Label [:Label2 ...]]? [ {props} ]? )
        #   - 捕获 var (可为空)、第一个 label（可为空）、属性 block（可为空）
        node_re = re.compile(
            r'\(\s*(' + var_re + r')?\s*'           # 1: var (可为空)
            r'(?::\s*(' + var_re + r')(?:\s*:\s*' + var_re + r')*)?'  # 2: first label
            r'\s*(\{[^{}]*\})?'                      # 3: props block
            r'\s*\)'
        )
        # 关系模式：-[ [var] [:REL] [ {props} ]? [*range]? ]- 或 ->, <-
        # 捕获方向前后箭头及 rel_type
        rel_re = re.compile(
            r'(<-|-)\s*'                             # 1: left arrow: -, <-
            r'\[\s*(?:' + var_re + r')?\s*'          # [var]?
            r'(?::\s*(' + var_re + r'))?'            # 2: rel_type
            r'[^\[\]]*'                              # props, *range, predicate
            r'\]\s*(->|-)'                           # 3: right arrow: ->, -
        )

        def _collect_var_to_label(query: str) -> Dict[str, str]:
            """扫描整段查询，收集 (var:Label) 到标签的绑定（取首次出现）。"""
            v2l: Dict[str, str] = {}
            # 带显式 Label 的节点模式
            labeled_node_re = re.compile(
                r'\(\s*(' + var_re + r')\s*:\s*(' + var_re + r')\b'
            )
            for m in labeled_node_re.finditer(query):
                var, lb = m.group(1), m.group(2)
                if var and var not in v2l:
                    v2l[var] = lb
            return v2l

        def _iter_rel_patterns(query: str):
            """
            在整段查询中遍历形如 node-rel-node 的完整模式，返回
            (left_var, left_label, rel_type, right_var, right_label, direction)。
            direction: '->'（左->右）, '<-'（右->左）, '-'（无向）
            """
            i = 0
            n = len(query)
            while i < n:
                # 尝试在 i 处匹配节点
                nm = node_re.match(query, i)
                if not nm:
                    i += 1
                    continue
                left_var = nm.group(1) or ""
                left_label = nm.group(2) or ""
                j = nm.end()
                # 在节点之后尝试匹配关系
                rm = rel_re.match(query, j)
                if not rm:
                    # 无关系紧随，跳到下一处
                    i = j
                    continue
                left_arrow = rm.group(1)    # '<-' or '-'
                right_arrow = rm.group(3)   # '->' or '-'
                rel_type = rm.group(2) or ""
                k = rm.end()
                # 关系之后必须紧跟节点
                nm2 = node_re.match(query, k)
                if not nm2:
                    i = j
                    continue
                right_var = nm2.group(1) or ""
                right_label = nm2.group(2) or ""

                # 判定方向
                if left_arrow == "-" and right_arrow == "->":
                    direction = "->"
                elif left_arrow == "<-" and right_arrow == "-":
                    direction = "<-"
                elif left_arrow == "-" and right_arrow == "-":
                    direction = "-"
                else:
                    direction = "->"  # 其他情况按左->右

                yield (left_var, left_label, rel_type, right_var, right_label, direction)
                # 右节点可能是下一个模式的左节点（链式路径：()-[]->()-[]->()）
                i = nm2.start()
                # 避免死循环：若 right node 紧贴 j，至少前进 1
                if i <= j:
                    i = j + 1

        for q in queries:
            if not q or not q.strip():
                continue

            # 1) 任意节点 (var:Label { ... })：校验属性属于对应 Label
            for m in re.finditer(r':(' + var_re + r')\s*(\{[^{}]*\})', q):
                label_name = m.group(1)
                props_content = m.group(2)
                if label_name not in labels:
                    continue
                valid_props = set(labels[label_name].properties.keys())
                prop_keys = re.findall(r'[\{,]\s*(' + var_re + r')\s*:', props_content)
                for k in prop_keys:
                    if k not in valid_props:
                        return False, (
                            f"属性 {k} 不属于 label {label_name}: "
                            f"(:{label_name} {{{k}: ...}})"
                        )

            # 2) 收集变量到标签的绑定（跨 MATCH/WHERE/CREATE 等）
            var_to_label = _collect_var_to_label(q)

            # 3) 遍历所有关系模式，校验 (start, rel, end) 三元组
            if not triplets:
                continue
            for (lv, ll, rt, rv, rl, direction) in _iter_rel_patterns(q):
                if not rt:
                    continue  # 无显式关系类型（如匿名关系/可变长），暂不校验

                # 解析左右两端的标签：模式内标签 > 变量绑定
                left_lb = ll or (var_to_label.get(lv) if lv else "")
                right_lb = rl or (var_to_label.get(rv) if rv else "")

                if not left_lb or not right_lb:
                    continue  # 两端标签未知，跳过

                if direction == "->":
                    s_lb, e_lb = left_lb, right_lb
                    if (s_lb, rt, e_lb) not in triplets:
                        return False, (
                            f"关系类型与节点对不匹配: "
                            f"(:{s_lb})-[:{rt}]->(:{e_lb}) 不在合法三元组中"
                        )
                elif direction == "<-":
                    s_lb, e_lb = right_lb, left_lb
                    if (s_lb, rt, e_lb) not in triplets:
                        return False, (
                            f"关系类型与节点对不匹配: "
                            f"(:{left_lb})<-[:{rt}]-(:{right_lb}) 不在合法三元组中"
                        )
                else:  # '-' 无向
                    if (left_lb, rt, right_lb) not in triplets and (right_lb, rt, left_lb) not in triplets:
                        return False, (
                            f"关系类型与节点对不匹配: "
                            f"(:{left_lb})-[:{rt}]-(:{right_lb}) 在任一方向均不在合法三元组中"
                        )

        return True, None

    def _has_id_aggregate(self, query: str) -> bool:
        """
        判断查询中是否存在针对 ID 相关属性的聚合：
        如 avg(a.companyId)、sum(a.user_id) 等。
        """
        import re

        if not query:
            return False

        # 提取聚合函数调用片段：AVG(...), SUM(...), COUNT(...), MIN(...), MAX(...), COLLECT(...)
        pattern_agg = r'(?i)\b(?:avg|sum|min|max|count|collect)\s*\(([^)]*)\)'
        for agg_arg in re.findall(pattern_agg, query):
            # 在聚合参数中查找属性访问：a.prop 或 a.`prop`
            # 支持普通和反引号形式；这里只关心属性名本身
            for prop_bt, prop_plain in re.findall(r'\w+\.(?:`([^`]+)`|(\w+))', agg_arg):
                prop_name = prop_bt or prop_plain
                if not prop_name:
                    continue
                if self._is_id_property(prop_name):
                    return True

        return False
    
    def _adapt_validation_for_index(self, validation_template: str, index: int) -> str:
        """
        将 validation 模板中以 1 结尾的参数占位符（如 $VALUE1/$AID1）替换为对应行索引：
        - index=1 时返回原模板
        - index=2 时，将 $XXX1 替换为 $XXX2
        只改后缀为 1 的占位符，避免误伤无索引的参数名。
        """
        if index <= 1 or not validation_template:
            return validation_template
        
        import re
        
        pattern = re.compile(r'\$([A-Z_]+)1\b')
        
        def repl(m: "re.Match") -> str:
            name = m.group(1)
            return f"${name}{index}"
        
        return pattern.sub(repl, validation_template)
    
    def _build_export_record(self, r: ManagementQueryResult) -> Dict[str, Any]:
        """将内部结果对象转换为导出的记录格式"""

        def _extract_scalar_answer(answer: List[Dict]) -> Any:
            """
            将执行结果列表简化为标量：
            - 若为单行单列（如 [{ "cnt": 753 }]），返回该值 753
            - 其他情况原样返回（一般不会用于当前基准）
            """
            if not answer:
                return None
            if isinstance(answer, list) and len(answer) == 1 and isinstance(answer[0], dict):
                row = answer[0]
                if len(row) == 1:
                    return next(iter(row.values()))
            return answer

        # 处理 batch 格式的 template_query
        if isinstance(r.template_query, list):
            # batch 格式：template 是查询列表
            template_queries = r.template_query
        else:
            # 单个查询格式：转换为列表以保持一致性
            template_queries = [r.template_query]
        
        # 处理 validation 查询结果（新格式）
        validation_export = None
        if r.validation_queries and r.validation_answers:
            validation_export = []
            for i, (vq, va) in enumerate(zip(r.validation_queries, r.validation_answers)):
                validation_export.append({
                    "query": vq,
                    "answer": _extract_scalar_answer(va),
                    "index": i  # 记录这是第几次 validation（0=初始，1=第一次template后，...）
                })
        
        # 构建结果字典，只包含需要的字段
        # 移除 pre_validation 和 post_validation
        # 移除 template 的 answers 字段
        result_dict = {
            "template": {
                "query": template_queries,  # 始终返回列表格式
                # 不再记录 template 查询的输出（answers）
            },
        }
        
        # 如果有新格式的 validation，添加到结果中
        if validation_export:
            result_dict["validation"] = validation_export
        
        return result_dict

    def export_results(self, output_path: str):
        """一次性导出全部结果到JSON文件（与流式输出格式保持一致）"""
        output_data = [self._build_export_record(r) for r in self.results]
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(output_data, f, ensure_ascii=False, indent=2, default=str)
        logger.info(f"结果已导出到: {output_path}")
    
    def close(self):
        """关闭连接"""
        if self.db_builder:
            self.db_builder.close()
        if self.driver:
            self.driver.close()
            logger.info("连接已关闭")
    
    def __enter__(self):
        self.connect()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
