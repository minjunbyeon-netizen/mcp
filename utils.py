#!/usr/bin/env python3
"""
공통 유틸리티 모듈
LoadingSpinner, JSON 추출, API 키 로드 등 공통 기능
"""

import os
import json
import re
import threading
import time
from pathlib import Path


class LoadingSpinner:
    """로딩 스피너 애니메이션"""
    def __init__(self, message="처리 중"):
        self.message = message
        self.running = False
        self.thread = None

    def start(self):
        self.running = True
        self.thread = threading.Thread(target=self._animate)
        self.thread.start()

    def _animate(self):
        frames = ['|', '/', '-', '\\']
        i = 0
        while self.running:
            print(f"\r  {frames[i % 4]} {self.message}...", end="", flush=True)
            time.sleep(0.2)
            i += 1

    def stop(self, success_msg="완료"):
        self.running = False
        if self.thread:
            self.thread.join()
        print(f"\r  [OK] {success_msg}" + " " * 20)


def extract_json_from_response(response_text: str) -> str:
    """AI 응답에서 JSON 문자열 추출"""
    if "```json" in response_text:
        response_text = response_text.split("```json")[1].split("```")[0]
    elif "```" in response_text:
        response_text = response_text.split("```")[1].split("```")[0]
    return response_text.strip()


def parse_json_response(response_text: str) -> dict:
    """AI 응답에서 JSON을 추출하고 파싱"""
    cleaned = extract_json_from_response(response_text)

    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        # 잘못된 이스케이프 문자 정리 후 재시도
        cleaned = re.sub(r'\\(?!["\\/bfnrtu])', r'\\\\', cleaned)
        try:
            return json.loads(cleaned)
        except json.JSONDecodeError:
            # 최종 시도: 제어 문자 제거
            cleaned = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', cleaned)
            return json.loads(cleaned)


def load_api_key(key_name: str = "GEMINI_API_KEY") -> str | None:
    """환경변수 또는 mcp_config.json에서 API 키 로드"""
    from dotenv import load_dotenv
    load_dotenv()

    api_key = os.getenv(key_name)
    if api_key:
        return api_key

    config_path = Path(__file__).parent / "mcp_config.json"
    if config_path.exists():
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
            for server in config.get("mcpServers", {}).values():
                key = server.get("env", {}).get(key_name)
                if key:
                    os.environ[key_name] = key
                    return key

    return None
