#!/bin/bash
# Выкатка с GitHub: забрать main в bare-репу, разложить в /opt, перезапустить сервис.
# Зовёт GitHub Actions по SSH (ключ с forced command) или руками: mbti-predict-deploy
set -e
REPO=/var/repo/mbti-predict.git
TREE=/opt/mbti-predict
UV=/root/.local/bin/uv

# Два пуша подряд не должны драться за рабочее дерево
exec 9>/run/mbti-predict-deploy.lock
flock 9

git --git-dir=$REPO fetch -q origin +main:main
git --git-dir=$REPO --work-tree=$TREE checkout -q -f main
echo "[mbti-predict] $(git --git-dir=$REPO log --oneline -1 main)"
cd $TREE

$UV venv --python 3.11 --allow-existing -q .venv
$UV pip install --python $TREE/.venv/bin/python -q -r requirements.txt

install -m 644 deploy/mbti-predict.service /etc/systemd/system/mbti-predict.service
systemctl daemon-reload
# Скрипт обновляет сам себя: следующий деплой пойдёт уже по новой версии
install -m 755 deploy/deploy.sh /usr/local/bin/mbti-predict-deploy

# Без обоих ключей сервис упадёт в цикл рестартов — ждём заполнения /etc/mbti-predict.env
if grep -q '^BOT_TOKEN=.\+' /etc/mbti-predict.env \
   && grep -q '^OPENROUTER_API_KEY=.\+' /etc/mbti-predict.env; then
  systemctl enable -q mbti-predict
  systemctl restart mbti-predict
  sleep 3
  systemctl is-active -q mbti-predict || { journalctl -u mbti-predict -n 20 --no-pager; exit 1; }
  echo "[mbti-predict] deployed to $TREE, service running"
else
  echo "[mbti-predict] deployed to $TREE"
  echo "[mbti-predict] сервис не запущен: заполни /etc/mbti-predict.env"
  exit 1
fi
