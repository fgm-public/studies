#!/usr/bin/env python3

# Импортируем библиотеку "socket" содержащую набор классов для работы с сетью 
from socket import *
# Указываем адрес сервера
server = 'localhost'
# Указываем номер TCP порта сервера для нашего приложения
# Мы будем обращаться к серверу на этот порт
port = 12002
# Создаём объект сетевого (AF_INET) TCP (SOCK_STREAM) сокета
socket = socket(AF_INET, SOCK_STREAM)
# Запрашиваем у ОС создание сокета и подключаемся к серверу
socket.connect((server,port))
# Просто выводим сообщение с приглашением к вводу строки
sentence = input('\n Input lowercase sentence: ')
# Отправляем сообщение серверу
socket.send(sentence.encode())
# Получаем модифицированное сообщение (ответ) от сервера
modified_sentence = socket.recv(1024)
# Выводим сообщение полученное от сервера
print('\n Server said:', modified_sentence.decode(), '\n')
# Запрашиваем у ОС закрытие сокета
socket.close()
