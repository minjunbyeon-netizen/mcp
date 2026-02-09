#!/usr/bin/env python3
"""
기존 페르소나 파일에 버전 정보 및 blog_writing_config 추가
"""

import sys
import io
import json
from pathlib import Path
from persona_version_manager import generate_default_blog_config, PERSONA_DIR

# Windows 터미널 UTF-8 출력 설정
if sys.platform == 'win32' and not isinstance(sys.stdout, io.TextIOWrapper):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')


def migrate_personas():
    """기존 페르소나 파일들을 v1으로 마이그레이션"""
    
    print("=" * 60)
    print("[Migration] 페르소나 파일 마이그레이션")
    print("=" * 60)
    
    persona_files = list(PERSONA_DIR.glob("*.json"))
    persona_files = [f for f in persona_files if not f.name.endswith("_feedback.json") and "_v" not in f.stem]
    
    if not persona_files:
        print("\n[OK] 마이그레이션할 파일이 없습니다.")
        return
    
    print(f"\n[INFO] {len(persona_files)}개 파일 발견")
    
    for file in persona_files:
        print(f"\n처리 중: {file.name}")
        
        try:
            with open(file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # 이미 버전 정보가 있으면 스킵
            if "version" in data:
                print(f"   [SKIP] 이미 버전 정보가 있습니다 (v{data['version']})")
                continue
            
            # 버전 정보 추가
            data["version"] = 1
            
            # blog_writing_config 추가
            if "blog_writing_config" not in data:
                print(f"   [ADD] blog_writing_config 자동 생성 중...")
                data["blog_writing_config"] = generate_default_blog_config(data)
            
            # version_info 추가
            data["version_info"] = {
                "is_latest": True,
                "upgrade_reason": "Initial version (migrated)"
            }
            
            # 저장
            with open(file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            
            print(f"   [OK] 마이그레이션 완료 (v1)")
            
        except Exception as e:
            print(f"   [ERROR] 오류: {e}")
    
    print("\n" + "=" * 60)
    print("[DONE] 마이그레이션 완료!")
    print("=" * 60)


if __name__ == "__main__":
    migrate_personas()
