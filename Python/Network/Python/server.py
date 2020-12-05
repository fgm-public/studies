#!/usr/bin/env python3

# Импортируем библиотеку "socket" содержащую набор классов для работы с сетью 
from socket import *

# Выбираем произвольный номер TCP порта для нашего сервера
# На этот порт сервер будет принимать подключения (слушать порт)
port = 12002
# Создаём объект сетевого (AF_INET) TCP (SOCK_STREAM) слушателя
# Слушатель ожидает клиентских подключений на связанном интерфейсе и порту 
socket_listener = socket(AF_INET, SOCK_STREAM)
# Связываем объект слушателя с выбранным интерфейсом и номером порта
socket_listener.bind(('',port))
# Запрашиваем у ОС создание слушателя
socket_listener.listen(1)
# Просто выводим сообщение о запуске сервера в консоль сервера
print('\n The server is ready to receive messages \n')

# Теперь наш сервер готов принимать подключения, но логика его работы не определена
# Определяем логику работы сервера...

# Запускаем бесконечный цикл
while True:
    # Ожидаем клиентов
    # В момент подключения клиента получаем объект сокета
    # и пару IP адрес и порт клиента
    socket_worker, client_addr = socket_listener.accept()
    # Выводим информацию о IP адресе и порте клиента
    print(f'We have a guest from {client_addr}')
    # Вычитываем полученные от клиента данные из сокета
    sentence = socket_worker.recv(1024)
    # Приводим полученные данные к верхнему регистру
    capitalized_sentence = sentence.upper()
    # Отправляем модифицированные данные клиенту
    socket_worker.send(capitalized_sentence)
    # Запрашиваем у ОС закрытие сокета
    socket_worker.close()
