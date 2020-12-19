using System;
using System.Text;
using System.Net;
using System.Net.Sockets;

namespace SimpleTcpServer
{
    class Program
    {
        static void Main()
        {
            // Выбираем произвольный номер TCP порта для нашего сервера
            // На этот порт сервер будет принимать подключения (слушать порт)
            int tcpPort = 12002;
            // Создаём объект сетевого TCP слушателя
            // Слушатель ожидает клиентских подключений на связанном интерфейсе и порту 
            TcpListener tcpListener = new TcpListener(IPAddress.Any, tcpPort);
            // Начинаем прослушивать порт на сетевом интерфейсе в ожидании клиентских подключений
            // Запрашиваем у ОС создание слушателя
            tcpListener.Start();

            // Просто выводим сообщение о запуске сервера в консоль сервера
            Console.WriteLine("The server is ready to receive messages");
          
            //Наш сервер запущен, и принимает подклчения, определяем логику работы сервера
            //Запускаем бесконечный цикл
            while (true)
            {
                // В момент подключения клиента получаем объект сокета
                TcpClient client = tcpListener.AcceptTcpClient();
                // Получаем объект сетевого потока
                NetworkStream netStream = client.GetStream();
                // Готовим место для принятия сообщения
                byte[] byte_sentence = new byte[1024];
                // Читаем сообщение от клиента
                int count = netStream.Read(byte_sentence, 0, byte_sentence.Length);
                // Восстанавливаем строку из массива байтов
                string sentence = Encoding.ASCII.GetString(byte_sentence);
                // Приводим строку к верхнему регистру
                string capitalized_sentence = sentence.ToUpper();
                // Формируем массив байтов из модифицированной строки
                byte[] response_sentence = Encoding.ASCII.GetBytes(capitalized_sentence);
                // Возвращаем клиенту модифицированное сообщение
                netStream.Write(response_sentence, 0, response_sentence.Length);
                // Выводим на экран полученное сообщение в виде строки
                Console.Write(Encoding.Default.GetString(response_sentence, 0, count));
                // Запрашиваем у ОС закрытие сокета
                client.Close();
            }
        }
    }
}
