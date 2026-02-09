#!/usr/bin/env python3
"""
페르소나 학습 리포트 및 버전 비교
"""

import sys
from pathlib import Path
from persona_version_manager import (
    get_all_versions,
    compare_versions,
    get_feedback_history,
    PERSONA_DIR
)


def list_all_personas():
    """모든 페르소나 목록 표시"""
    persona_files = list(PERSONA_DIR.glob("*.json"))
    persona_files = [f for f in persona_files if not f.name.endswith("_feedback.json")]
    
    # client_id별로 그룹화
    personas = {}
    for file in persona_files:
        if "_v" in file.stem:
            client_id = file.stem.rsplit("_v", 1)[0]
        else:
            client_id = file.stem
        
        if client_id not in personas:
            personas[client_id] = []
        personas[client_id].append(file)
    
    return personas


def show_learning_report(client_id: str):
    """페르소나별 학습 진행 상황 리포트"""
    
    versions = get_all_versions(client_id)
    if not versions:
        print(f"❌ {client_id} 페르소나를 찾을 수 없습니다.")
        return
    
    client_name = versions[0].get("client_name", client_id)
    latest_version = versions[-1]
    
    print("\n" + "=" * 80)
    print(f"📊 {client_name} 학습 리포트")
    print("=" * 80)
    
    # 기본 정보
    print(f"\n📋 기본 정보:")
    print(f"   Client ID: {client_id}")
    print(f"   조직: {latest_version.get('organization', 'N/A')}")
    print(f"   현재 버전: v{latest_version.get('version', 1)}")
    print(f"   총 버전 수: {len(versions)}")
    
    # 피드백 통계
    feedback_data = get_feedback_history(client_id)
    stats = feedback_data.get("learning_stats", {})
    
    print(f"\n📈 학습 통계:")
    print(f"   총 생성 블로그: {stats.get('total_blogs', 0)}개")
    print(f"   평균 만족도: {stats.get('average_rating', 0)}/5 ⭐")
    
    improvement = stats.get('improvement_trend', 0)
    if improvement > 0:
        print(f"   개선 추세: +{improvement} 📈 (최근 5개가 전체 평균보다 높음)")
    elif improvement < 0:
        print(f"   개선 추세: {improvement} 📉 (최근 5개가 전체 평균보다 낮음)")
    else:
        print(f"   개선 추세: {improvement} (안정적)")
    
    # 공통 이슈
    common_issues = stats.get('common_issues', {})
    if common_issues:
        print(f"\n🔧 주요 피드백 이슈:")
        sorted_issues = sorted(common_issues.items(), key=lambda x: x[1], reverse=True)
        for issue, count in sorted_issues[:5]:
            print(f"   - {issue}: {count}회")
    
    # 버전별 변화
    print(f"\n📝 버전 히스토리:")
    for v in versions:
        version_num = v.get("version", 1)
        created = v.get("created_at", "N/A")[:10] if v.get("created_at") else "N/A"
        
        if version_num == 1:
            print(f"\n   v{version_num} ({created}) - 초기 버전")
        else:
            info = v.get("version_info", {})
            print(f"\n   v{version_num} ({created})")
            print(f"      이유: {info.get('upgrade_reason', 'N/A')}")
            
            changes = info.get("changes_from_parent", [])
            if changes:
                print(f"      변경: {len(changes)}개 항목")
    
    # 최신 설정
    if "blog_writing_config" in latest_version:
        config = latest_version["blog_writing_config"]
        print(f"\n⚙️ 현재 블로그 설정 (v{latest_version.get('version', 1)}):")
        
        if "structure" in config:
            print(f"   구조:")
            print(f"      - 시작 스타일: {config['structure'].get('intro_style', 'N/A')}")
            print(f"      - 본문 섹션: {config['structure'].get('body_sections', 'N/A')}개")
        
        if "formatting" in config:
            print(f"   포맷:")
            print(f"      - 이모티콘 위치: {config['formatting'].get('emoji_positions', 'N/A')}")
            print(f"      - 헤더 형식: {config['formatting'].get('header_format', 'N/A')}")
        
        if "content_rules" in config:
            print(f"   콘텐츠:")
            print(f"      - 길이: {config['content_rules'].get('min_length', 'N/A')} ~ {config['content_rules'].get('max_length', 'N/A')}자")
            print(f"      - 문단 길이: {config['content_rules'].get('paragraph_length', 'N/A')}")
            print(f"      - 전문용어: {config['content_rules'].get('technical_terms', 'N/A')}")
    
    print("\n" + "=" * 80)


def main():
    print("=" * 80)
    print("📊 페르소나 학습 리포트 & 버전 비교")
    print("=" * 80)
    
    personas = list_all_personas()
    
    if not personas:
        print("\n❌ 저장된 페르소나가 없습니다.")
        return
    
    print("\n📋 사용 가능한 페르소나:")
    print("-" * 80)
    
    persona_list = list(personas.keys())
    for i, client_id in enumerate(persona_list, 1):
        version_count = len(personas[client_id])
        print(f"  {i}. {client_id} ({version_count}개 버전)")
    
    print("\n🔢 페르소나 번호를 선택하세요:")
    try:
        choice = int(input(">>> ").strip())
        selected_id = persona_list[choice - 1]
    except:
        print("❌ 잘못된 선택입니다.")
        return
    
    print("\n📊 보고서 유형을 선택하세요:")
    print("1. 학습 리포트 (통계 + 설정)")
    print("2. 버전 비교 (상세 변경 내역)")
    print("3. 둘 다 보기")
    
    try:
        report_type = int(input(">>> ").strip())
    except:
        report_type = 3
    
    if report_type == 1:
        show_learning_report(selected_id)
    elif report_type == 2:
        compare_versions(selected_id)
    else:
        show_learning_report(selected_id)
        print("\n")
        compare_versions(selected_id)


if __name__ == "__main__":
    main()
