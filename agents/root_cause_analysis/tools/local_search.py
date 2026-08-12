from __future__ import annotations

import html
import json
import re
from pathlib import Path

import httpx
from google.adk.tools import ToolContext

from root_cause_analysis.constants import (
    KEY_EXTERNAL_SEARCH_RESULTS,
    KEY_INTERNAL_SEARCH_RESULTS,
)
from root_cause_analysis.models import (
    Document,
    ExternalSearchResult,
    InternalSearchResult,
    MissedKPI,
    Rules,
)
from telco_local.settings import REPOSITORY_ROOT, settings
from telco_local.similarity import cosine_similarity


RULES_DIR = REPOSITORY_ROOT / "data" / "rca-rules"
DOCS_DIR = REPOSITORY_ROOT / "docs"
EXTERNAL_SITES = ["https://ourtechplanet.com/lte-erab-success-rate/"]


async def find_rca_rules(missed_kpis: list[MissedKPI]) -> list[Rules]:
    """加载本地 JSON RCA 规则，并按照异常 KPI 进行匹配。"""

    requested = {item.kpi for item in missed_kpis}
    result: list[Rules] = []
    for path in sorted(RULES_DIR.glob("*.json")):
        data = json.loads(path.read_text(encoding="utf-8"))
        if not requested.intersection(data.get("kpi_missed", [])):
            continue
        result.append(
            Rules(
                processing_rule=data["processing_rule"],
                processing_rule_tools=set(data.get("processing_rule_tools", [])),
                severity_determination_rule=data["severity_determination_rule"],
                severity_determination_rule_tools=set(
                    data.get("severity_determination_rule_tools", [])
                ),
                source_document=str(path.resolve()),
            )
        )
    return result


def _markdown_chunks(path: Path) -> list[str]:
    content = path.read_text(encoding="utf-8")
    sections = re.split(r"(?=^#{1,3}\s)", content, flags=re.MULTILINE)
    return [section.strip()[:3500] for section in sections if section.strip()]


async def search_internal_documentation(
    tool_context: ToolContext,
    query: str,
) -> dict:
    """搜索本地 Markdown 资料和 RCA 规则文件。"""

    candidates: list[tuple[float, str, Path]] = []
    for path in sorted(DOCS_DIR.glob("*.md")):
        for chunk in _markdown_chunks(path):
            candidates.append((cosine_similarity(query, chunk), chunk, path))

    for path in sorted(RULES_DIR.glob("*.json")):
        text = path.read_text(encoding="utf-8")
        candidates.append((cosine_similarity(query, text), text, path))

    best = sorted(candidates, key=lambda item: item[0], reverse=True)[:3]
    useful = [item for item in best if item[0] > 0]
    search_result = "\n\n".join(item[1] for item in useful)
    references = [
        Document(url=str(item[2].resolve()), title=item[2].name)
        for item in useful
    ]
    result = InternalSearchResult(
        queries=[query],
        search_result=search_result or "未找到相关本地资料。",
        references=references,
    )
    tool_context.state[KEY_INTERNAL_SEARCH_RESULTS] = result.model_dump_json()
    return {"status": "success", "result": result}


def _plain_text_from_html(content: str) -> str:
    content = re.sub(r"<(script|style)[^>]*>.*?</\1>", " ", content, flags=re.I | re.S)
    content = re.sub(r"<[^>]+>", " ", content)
    return re.sub(r"\s+", " ", html.unescape(content)).strip()


async def retrieve_external_documentation(tool_context: ToolContext) -> dict:
    """不使用 Google 工具，按需检索允许列表中的公开资料。"""

    if not settings.external_docs_enabled:
        result = ExternalSearchResult(
            search_results="外部资料检索当前已关闭。",
            references=[],
        )
        tool_context.state[KEY_EXTERNAL_SEARCH_RESULTS] = result.model_dump_json()
        return {"status": "disabled", "result": result}

    excerpts: list[str] = []
    references: list[Document] = []
    async with httpx.AsyncClient(timeout=15, follow_redirects=True) as client:
        for url in EXTERNAL_SITES:
            try:
                response = await client.get(url)
                response.raise_for_status()
                excerpts.append(_plain_text_from_html(response.text)[:5000])
                references.append(Document(url=url, title=url))
            except Exception as exc:
                excerpts.append(f"无法检索 {url}：{exc}")

    result = ExternalSearchResult(
        search_results="\n\n".join(excerpts),
        references=references,
    )
    tool_context.state[KEY_EXTERNAL_SEARCH_RESULTS] = result.model_dump_json()
    return {"status": "success", "result": result}
