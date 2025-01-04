## Команды

```shell
# Запуск
docker compose up -d

# Генерация репозитория
docker compose run --rm repo

# Просмотр журнала
docker compose exec kodi \
  tail -F /kodi/temp/kodi.log | \
  awk -F': ' '/\[plugin.video.demo\]/ {print $2}'
```
