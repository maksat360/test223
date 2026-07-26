#!/bin/bash
set -e

echo "📦 Установка V2 MES-бота..."

if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 не найден. Установите Python 3.11+ и повторите."
    exit 1
fi

python3 -m venv venv
source venv/bin/activate

pip install --upgrade pip
pip install -r requirements.txt

mkdir -p cloud_storage data fonts

echo ""
echo "✅ Установка завершена."
echo "Теперь откройте config.py и вставьте токен бота (BOT_TOKEN)."
echo "После этого запустите ./start.sh"
