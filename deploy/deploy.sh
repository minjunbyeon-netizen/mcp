#!/bin/bash
# VPS 배포 스크립트 — mcp auto-blog
# 실행: bash deploy/deploy.sh
set -e

VPS="vps-dev"
REMOTE_DIR="/home/dev/work/mcp"
SERVICE="mcp"

echo "=== [1/5] 소스 코드 동기화 ==="
ssh $VPS "mkdir -p $REMOTE_DIR/logs"
rsync -avz --exclude='.git' \
           --exclude='__pycache__' \
           --exclude='*.pyc' \
           --exclude='.env' \
           --exclude='logs/' \
           --exclude='allowed_emails.txt' \
           --exclude='blog_pull/output/' \
           --exclude='cookies.txt' \
           --exclude='tmp_*.json' \
           --exclude='tmp_*.txt' \
           ./ $VPS:$REMOTE_DIR/

echo "=== [2/5] Python 가상환경 & 패키지 설치 ==="
ssh $VPS "
cd $REMOTE_DIR
python3 -m venv .venv --system-site-packages 2>/dev/null || true
.venv/bin/pip install -q --upgrade pip
.venv/bin/pip install -q -r requirements.txt
"

echo "=== [3/5] systemd 서비스 등록 ==="
ssh $VPS "sudo cp $REMOTE_DIR/deploy/mcp.service /etc/systemd/system/$SERVICE.service"
ssh $VPS "sudo systemctl daemon-reload && sudo systemctl enable $SERVICE"

echo "=== [4/5] nginx 설정 추가 ==="
ssh $VPS "
# nginx 설정에 /mcp/ 블록이 없으면 추가
NGINX_CONF=/etc/nginx/sites-enabled/default
if ! grep -q 'location /mcp/' \$NGINX_CONF; then
    # server 블록 닫는 } 바로 앞에 삽입
    sudo sed -i '/^}$/i\\    include /home/dev/work/mcp/deploy/nginx-mcp.conf;' \$NGINX_CONF
    echo 'nginx 설정 추가 완료'
else
    echo 'nginx 설정 이미 존재'
fi
sudo nginx -t && sudo systemctl reload nginx
"

echo "=== [5/5] 서비스 시작 ==="
ssh $VPS "sudo systemctl restart $SERVICE && sleep 2 && sudo systemctl status $SERVICE --no-pager | head -15"

echo ""
echo "배포 완료!"
echo "접속 URL: http://137.184.82.157/mcp/"
echo ""
echo "다음 단계:"
echo "  1. VPS에 .env 파일 생성: ssh vps-dev 'nano /home/dev/work/mcp/.env'"
echo "  2. Google OAuth 리디렉션 URI 추가: http://137.184.82.157/mcp/callback"
