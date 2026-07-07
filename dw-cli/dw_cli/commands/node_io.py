# -*- coding: utf-8 -*-
"""节点 IO 查询类命令（探活确认可用，2026-07-07 封装）。"""
from __future__ import annotations

from typing import Optional

import typer
from alibabacloud_dataworks_public20200518 import models as dw_models

from dw_cli.commands import auth_params, output_option, query_option
from dw_cli.core import client, errors, output

app = typer.Typer(help="节点输入输出查询", )

_PROJ_ENV_HELP = "环境：PROD（生产，默认）/ DEV（开发）"


def _call(ctx: typer.Context, api_name: str, request, *, query, output_fmt):
    auth = auth_params(ctx)
    dw_client = client.build_client(**auth)
    runtime = client.build_runtime()
    method = getattr(dw_client, f"{api_name}_with_options")
    try:
        resp = method(request, runtime)
        output.emit(resp, query=query, output=output_fmt)
    except Exception as error:
        errors.fail(error)


@app.command("list-nodes-by-output")
def list_nodes_by_output(
    ctx: typer.Context,
    outputs: str = typer.Option(..., "--outputs",
                                help="节点输出名，多个用逗号分隔（如 dqsc_prod.some_node）"),
    project_env: str = typer.Option("PROD", "--project-env", help=_PROJ_ENV_HELP),
    query: Optional[str] = query_option(),
    output_fmt: str = output_option(),
):
    """根据输出名查询下游节点（谁依赖了这个输出）。

    
    🚀 Examples:
      # 查依赖某输出的节点
      dw-cli list-nodes-by-output --outputs "shouquanyunyingyu_ybz.ads_auth_access_data" \
        --project-env PROD

      # 只取节点 ID 和名称
      dw-cli list-nodes-by-output --outputs "dqsc_prod.123456789.sql" --project-env PROD \
        --query "Data[*].NodeList[*].{Id:NodeId,Name:NodeName}"

    
    📦 Output JSON Structure:
      - Data 是数组，每项 {NodeList: [{NodeId, NodeName, BaselineId, ...}], OutputName}
    """
    _call(ctx, "list_nodes_by_output", dw_models.ListNodesByOutputRequest(
        outputs=outputs, project_env=project_env,
    ), query=query, output_fmt=output_fmt)


@app.command("list-node-input-or-output")
def list_node_input_or_output(
    ctx: typer.Context,
    node_id: int = typer.Option(..., "--node-id", help="节点 ID"),
    project_env: str = typer.Option("PROD", "--project-env", help=_PROJ_ENV_HELP),
    io_type: str = typer.Option(..., "--io-type",
                                help="IO 类型：input（查上游依赖）或 output（查下游输出）"),
    query: Optional[str] = query_option(),
    output_fmt: str = output_option(),
):
    """查询节点的输入（上游依赖）或输出（下游产出）。

    
    🚀 Examples:
      # 查节点上游依赖
      dw-cli list-node-input-or-output --node-id 2587817 --project-env PROD --io-type input

      # 查节点输出
      dw-cli list-node-input-or-output --node-id 2587817 --project-env PROD --io-type output

    
    📦 Output JSON Structure:
      - Data 是数组，每项 {Data: 输入/输出名, NodeId, TableName, ParseType}

    
    ⚠️ 注意：io-type 只支持 input / output 字符串，传数字会报
    "非法IO类型，只支持 input / output 类型"。
    """
    _call(ctx, "list_node_input_or_output", dw_models.ListNodeInputOrOutputRequest(
        node_id=node_id, project_env=project_env, io_type=io_type,
    ), query=query, output_fmt=output_fmt)
