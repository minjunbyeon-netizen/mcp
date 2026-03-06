#!/usr/bin/env python3
"""
design-guide MCP Server
작업 시 공통 디자인 톤앤매너 가이드 제공
"""

from mcp.server.fastmcp import FastMCP
import json
from pathlib import Path

mcp = FastMCP("design-guide")

GUIDE_PATH = Path("G:/내 드라이브/01_work/design-tone-guide.json")


def _load_guide() -> dict:
    with open(GUIDE_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


@mcp.tool()
def get_design_guide() -> dict:
    """
    프로젝트 공통 디자인 가이드 전체를 반환합니다.
    UI/UX 작업 시 반드시 이 가이드를 기준으로 작업하세요.

    포함 항목:
    - colors: 색상 팔레트
    - typography: 폰트, 크기, 굵기, 줄간격
    - layout: 최대 너비, 컨테이너 패딩
    - spacing: 간격 스케일
    - components: button / card / form 컴포넌트 스펙
    - decoration_policy: 이모지, 그라디언트 등 사용 금지 정책
    - checklist: 작업 전 체크리스트
    """
    return _load_guide()


@mcp.tool()
def get_design_section(section: str) -> dict:
    """
    디자인 가이드의 특정 섹션만 반환합니다.

    Args:
        section: 조회할 섹션 이름
                 (colors / typography / layout / spacing /
                  components / decoration_policy / checklist / meta)

    Returns:
        해당 섹션의 내용
    """
    guide = _load_guide()
    if section not in guide:
        available = list(guide.keys())
        return {"error": f"섹션 '{section}'을 찾을 수 없습니다. 사용 가능: {available}"}
    return {section: guide[section]}


@mcp.tool()
def get_design_checklist() -> list:
    """
    작업 전 확인해야 할 디자인 체크리스트를 반환합니다.
    카테고리별로 분류됩니다 (color / typography / component / decoration).
    """
    guide = _load_guide()
    return guide.get("checklist", [])


if __name__ == "__main__":
    mcp.run()
