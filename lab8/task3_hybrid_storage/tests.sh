cd /home/smartkettlee/Documents/minet/osis/laba8/task3_hybrid_storage && cat > test_scenario.txt << 'EOF'
# Тестовый сценарий для проверки гибридного хранилища

echo "=== ТЕСТ 1: Сохранение файлов в HOT tier ==="
echo -e "put video1.mp4 Content_of_video1\nput project.zip Project_data\nput render.raw Render_data\nstatus\nexit" | sudo docker-compose run --rm app

echo ""
echo "=== ТЕСТ 2: Чтение файла (должен остаться в HOT) ==="
echo -e "get video1.mp4\nstatus\nexit" | sudo docker-compose run --rm app

echo ""
echo "=== ТЕСТ 3: Список всех файлов ==="
echo -e "list\nexit" | sudo docker-compose run --rm app

echo ""
echo "=== ТЕСТ 4: Ручная миграция (для демо используем короткие сроки) ==="
echo -e "migrate\nstatus\nexit" | sudo docker-compose run --rm app

echo ""
echo "=== ТЕСТ 5: Проверка MinIO Console ==="
echo "Откройте http://localhost:9001"
echo "Login: minioadmin / Password: minioadmin123"
echo "Проверьте bucket 'hybrid-storage'"

echo ""
echo "=== ТЕСТ 6: Проверка volumes ==="
sudo docker volume ls | grep hybrid

echo ""
echo "=== ТЕСТ 7: Проверка файлов в HOT tier ==="
sudo docker exec hybrid_app ls -lh /data/hot/

echo ""
echo "=== ТЕСТ 8: Проверка S3FS монтирования ==="
sudo docker exec s3fs ls -lh /mnt/s3/

echo ""
echo "✅ ВСЕ ТЕСТЫ ЗАВЕРШЕНЫ"
EOF
cat test_scenario.txt