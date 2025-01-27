## Команды

```shell
# Запуск
docker compose up -d

# Генерация репозитория
docker compose run --rm repo

# Просмотр журнала
docker compose exec kodi \
  tail -F /kodi/temp/kodi.log | \
  awk -F': ' '/\[plugin.vk.com\]/ {print $2}'
```

## Очистка кеша базы аддонов

```shell
docker compose exec kodi rm /kodi/userdata/Database/Addons*.db
```

## Полезные ресурсы

* https://kodi.wiki/view/JSON-RPC_API/v12
* [Конвертация команды cURL в Python](https://curlconverter.com/)
