
///https://docs.microsoft.com/en-us/dotnet/api/system.net.sockets.tcplistener?view=net-5.0


using System;
using System.Text;
///We include the namespaces System.Net and System.Net.Sockets because we need some types/methods from there.
using System.Net;
using System.Net.Sockets;

namespace ConsoleApp2
{
    class Program
    {
        static void Main(string[] args)
        {
            ///Переменная с TCP портом принимающим подключения
            int tcpPort = 12002;
            ///Создаём объект слущателя (ожидает подключения от клиента)
            ///https://docs.microsoft.com/ru-ru/dotnet/api/system.net.sockets.tcplistener?view=netframework-4.8
            TcpListener tcpListener = new TcpListener(IPAddress.Any, tcpPort);
            ///Начинаем прослушивать порт на сетевом интерфейсе в ожидании клиентских подключений
            tcpListener.Start();

            ///Ok, we have the server but it’s not doing anything. So, we’ll make him accept connections from a Tcp Client:
            ///Наш сервер запущен, и принимает подклчения, определяем логику работы сервера
            ///Запускаем бесконечный цикл
            while (true)
            {
                TcpClient client = tcpListener.AcceptTcpClient();

                ///After the client connects, the server will send using the NetworkStream
                NetworkStream netStream = client.GetStream();
                ///Because we can’t directly send/receive strings, we have to transform our messange into a byte array
                byte[] hello = new byte[100];
                hello = Encoding.Default.GetBytes("hello world");

                ///After the message is converted, it can be sent
                netStream.Write(hello, 0, hello.Length);


                ///We have the tcp client which connects to our server and sends data.
                ///While client.Connected returns true the server will be ‘blocked’ waiting for new messages, and won’t check/accept a new Tcp Client.
                ///This is usually solved using a different thread for every client connected or simply using an asynchronous server
                while (client.Connected)  // пока клиент подключен, ждем приходящие сообщения
                {
                    byte[] msg = new byte[1024];     // готовим место для принятия сообщения

                    ///The last part consists in reading the messages received from the client. Any incoming message is read using the same NetworkStream
                    int count = netStream.Read(msg, 0, msg.Length);   // читаем сообщение от клиента
                    Console.Write(Encoding.Default.GetString(msg, 0, count)); // выводим на экран полученное сообщение в виде строки
                }
            }
        }
    }
}
