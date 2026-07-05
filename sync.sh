#!/bin/bash

# Этот скрипт автоматизирует синхронизацию локальной папки проекта с удаленным GitHub-репозиторием.
# Перед запуском убедитесь, что переменная окружения GITHUB_TOKEN установлена с вашим персональным токеном GitHub,
# который имеет достаточные права (repo scope) для доступа к репозиторию.
# Пример: export GITHUB_TOKEN="your_github_personal_access_token"

PROJECT_DIR="/home/ubuntu/azs/fuel-map-bot"
REPO_URL="https://oauth2:${GITHUB_TOKEN}@github.com/kfedoseeva2112-cell/azs.git"

cd "$PROJECT_DIR" || { echo "Ошибка: Не удалось перейти в директорию проекта."; exit 1; }

echo "\n--- Начинаю синхронизацию Git ---"

# 1. Убедимся, что Git-репозиторий инициализирован
if [ ! -d ".git" ]; then
    echo "Инициализация нового Git-репозитория..."
    git init
    git remote add origin "$REPO_URL"
else
    echo "Git-репозиторий уже инициализирован."
    # Обновляем URL удаленного репозитория на случай, если токен изменился
    git remote set-url origin "$REPO_URL"
fi

# 2. Подтягиваем последние изменения с удаленного репозитория, чтобы избежать конфликтов
echo "\nПодтягиваю последние изменения с удаленного репозитория..."
git pull origin main || git pull origin master || { echo "Предупреждение: Не удалось выполнить git pull. Возможно, ветка не main/master или есть конфликты."; }

# 3. Добавляем все изменения (новые, измененные, удаленные файлы)
echo "\nДобавляю все изменения в индекс Git..."
git add .
git add -u

# 4. Проверяем, есть ли что коммитить
if git diff-index --quiet HEAD --;
then
    echo "\nНет изменений для коммита."
else
    # 5. Делаем коммит с осмысленным сообщением
    COMMIT_MESSAGE="Автосинхронизация от $(date +'%Y-%m-%d %H:%M:%S')"
    echo "\nСоздаю коммит: '$COMMIT_MESSAGE'"
    git commit -m "$COMMIT_MESSAGE"

    # 6. Выполняем git push
    echo "\nВыгружаю изменения на GitHub..."
    # Используем --force только если это абсолютно необходимо и безопасно
    # В данном случае, по запросу пользователя, используем --force
    if git push -u origin main --force; then
        echo "\n--- Синхронизация успешно завершена! ---"
        echo "Файлы успешно выгружены на GitHub."
    elif git push -u origin master --force; then
        echo "\n--- Синхронизация успешно завершена! ---"
        echo "Файлы успешно выгружены на GitHub."
    else
        echo "\n--- Ошибка синхронизации! ---"
        echo "Не удалось выгрузить изменения на GitHub. Проверьте права доступа и токен."
        exit 1
    fi
fi

# 7. Выводим краткий отчет (количество добавленных, удаленных, измененных файлов)
echo "\n--- Отчет о состоянии репозитория ---"
git status --short

echo "\nСкрипт синхронизации завершен."
