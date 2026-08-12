#  Copyright 2025 Google LLC
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#      https://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.

from typing import Optional, Set, Self

from pydantic import BaseModel, Field, model_validator


class CellTracesStats(BaseModel):
    connection_outcome: Optional[str]
    count: int

    @model_validator(mode='after')
    def set_defaults(self) -> Self:
        if not self.connection_outcome:
            self.connection_outcome = 'OTHER'
        return self


class MissedKPI(BaseModel):
    kpi: str = Field(description="KPI 标识")
    value: float = Field(description="KPI 数值")

    def to_descriptive_string(self) -> str:
        return f"{self.kpi}（数值={self.value}）"


class Incident(BaseModel):
    id: str = Field(description="唯一 Incident ID")
    description: str = Field(description="事故初步说明")
    severity: Optional[str] = Field(default=None, description="预估严重程度")
    kpi_missed: list[MissedKPI] = Field(description="异常 KPI 列表")
    enodeb_id: Optional[str] = Field(default=None, description="发生 KPI 异常的 eNodeB")
    cell_id: Optional[str] = Field(default=None, description="发生 KPI 异常的 Cell ID")
    status: str = Field(description="Incident 状态")
    start_time: str = Field(description="Incident 开始时间")
    end_time: Optional[str] = Field(default=None, description="Incident 结束时间")


class Document(BaseModel):
    url: str
    title: str


class ExternalSearchResult(BaseModel):
    search_results: str = Field(description="检索结果")
    references: list[Document] = Field(
        description="用于支撑结论的参考资料")


class InternalSearchResult(BaseModel):
    queries: list[str] = Field(description="检索使用的查询")
    search_result: str = Field(description="内部资料检索结果")
    references: list[Document] = Field(
        description="用于支撑结论的参考资料")


class Rules(BaseModel):
    processing_rule: str
    processing_rule_tools: Set[str]
    severity_determination_rule: str
    severity_determination_rule_tools: Set[str]
    source_document: str


class Action(BaseModel):
    tool_name: str = Field(description="执行建议动作的工具名称")
    reason_to_perform: str = Field(description="建议执行该动作的理由")
    parameters: Optional[dict] = Field(description="可选参数")
    status: str = Field(description="动作状态", default="SUGGESTED")
