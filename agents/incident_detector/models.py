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
from typing import Optional

from pydantic import BaseModel, Field


class MissedKPI(BaseModel):
    kpi: str = Field(description="KPI 标识")
    value: float = Field(description="KPI 数值")


class Incident(BaseModel):
    id: str = Field(description="唯一 Incident ID")
    description: str = Field(description="事故初步说明")
    kpi_missed: list[MissedKPI] = Field(description="未达到目标的 KPI 列表")
    enodeb_id: Optional[str] = Field(default=None, description="发生 KPI 异常的 eNodeB")
    cell_id: Optional[str] = Field(default=None, description="发生 KPI 异常的 Cell ID")
    status: str = Field(description="Incident 状态")
    start_time: str = Field(description="Incident 开始时间")
    end_time: Optional[str] = Field(default=None, description="Incident 结束时间")
