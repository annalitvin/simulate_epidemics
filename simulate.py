from threading import Thread  # Параллельные потоки
from http.server import BaseHTTPRequestHandler, HTTPServer # Базовый объект для обработчика запросов в HTTP сервере

from time import sleep

from argparse import ArgumentParser # Для передачи аргументов через командную строку
from sys import exit

from urllib.request import urlopen
from urllib.parse import parse_qs
import socketserver

import errno
import socket
import random

global_threads = []

class SimpleServer(socketserver.ThreadingMixIn, socketserver.TCPServer, Thread):
    '''
    Класс для сервера, работающего в отдельном потоке
    '''
    daemon_threads = True # чтобы поток завершался при закрытии программы
    allow_reuse_address = True # Позволяем повторно использовать адрес, на котоом был запущен этот сервер

    def __init__(self, server_address, RequestHandlerClass, x):
        # Инициализируем родительские классы Thread и socketserver.TCPServer
        socketserver.TCPServer.__init__(
            self, server_address, RequestHandlerClass)
        Thread.__init__(self, name="HTTP_Thread")
        self.running = True # Запускаем сервер сразу при создании
        self.messages_codes = []
        self.sneding_process = False
        self.x_messages = x


    def run(self, poll_interval=0.5):

        try:
            while self.running:
                self._handle_request_noblock() # Обрабатывать запросы не блокируя основной процесс
        finally:
            self.running = False # В случае огибки остановить сервер

    def stop(self):
        # Грамотное завершение работы сервера
        self.running = False
        urlopen('http://%s:%s' % self.server_address).read()
        self.server_close()

    def send_first(self, id):
        # Функция для отправки первого пакета
        self.sending_process = True
        thr = random.sample(global_threads, self.x_messages) # Делаем выборку из X потоков
        self.messages_codes.append({"id": id, "last_iteration": 0}) # Сохраняеи информацию о факте отправки
        for t in thr:
            u = t.server_address # олучаем адрес для отправки
            urlopen('http://' + str(u[0]) + ':' + str(u[1]) + '/?id=' + str(id) + "&iteration=0").read() # Отправляем сообщение
        self.sending_process = False


class HTTPHandler(BaseHTTPRequestHandler):
    # Класс для обработки HTTP запросом, используется классом SimpleServer
    allow_reuse_address = 1

    def _set_headers(self):
        self.send_response(200)
        self.end_headers()

    def address_string(self):
        host, port = self.client_address[:2]
        return host

    def do_GET(self):
        global a1
        qs = {}
        path = self.path
        if '?' in path:
            path, tmp = path.split('?', 1)
            qs = parse_qs(tmp)
        self._set_headers()
        try:
            id = qs['id']
            if id:
                for i in self.server.messages_codes:
                    if id[0] == i["id"]:
                        return
                else:
                    self.server.sending_process = True
                    iteration = int(qs['iteration'][0]) + 1
                    self.server.messages_codes.append({"id": id[0], "last_iteration" : iteration})

                    thr = random.sample(global_threads, self.server.x_messages)

                    for t in thr:
                        u =  t.server_address
                        urlopen('http://' + str(u[0]) + ':' + str(u[1]) + '/?id=' + id[0] + "&iteration=" + str(iteration))

            self.wfile.write(bytes('200', 'UTF-8'))
            self.server.sending_process = False
            return
        except KeyError:
            pass
        self.server.sending_process = False


def run_server(port, server_address, threads, x=4):
    # Функция для запуска сервера в отдельном параллельном потоке
    socketserver.TCPServer.allow_reuse_address = True
    try:
        httpd_thread = SimpleServer(
            (server_address, port), HTTPHandler, x)
        threads.append(httpd_thread)
        httpd_thread.daemon = True
        httpd_thread.allow_reuse_address = True
        httpd_thread.server_activate()
        httpd_thread.start()
    except socket.error as e:
        if e.errno == errno.EADDRINUSE:
            print('Address is in use, terminating')
            exit(1)
        else:
            print(str(e))

def stop_threads():
    # Функция, останавливающая и обнуляющая все потоки
    for thr in global_threads:
        thr.stop()
        thr.join()
    global_threads[:] = []


def if_open_server(threads):
    # Функция для опеределения, есть ли серверы в процессе посылки сообщений
    for i in threads:
        try:
            if i.sending_process:
                return True
        except:
            pass
    return False


def count_threads(threads):
    # Функция для подсчёта количества серверов, получивших сообщение
    n = 0
    for i in threads:
        if len(i.messages_codes) > 0:
            n += 1
    return n


def get_max_iterations(threads):
    # Функция для подсчёта максимального количества итераций до завершения рассылки
    max_iterations = 0
    for i in threads:
        if len(i.messages_codes) > 0:
            for j in i.messages_codes:
                if (j["last_iteration"] > max_iterations):
                    max_iterations = j["last_iteration"]
    return max_iterations

if __name__ == "__main__":
    # Создаём объект парсера аргументов, передаваемых черех командную строку
    parser = ArgumentParser(description='Test epidemic simulation')
    # Считываем акргументы командной строки
    # Количество узлов (серверов):
    parser.add_argument(
        '-n', '--nodes', help='Number of nodes', dest='n_servers', default=20, type=int)
    # Количество тестовых запусков:
    parser.add_argument(
        '-i', '--times', help='How many times run the test task', dest='i_times', default=100, type=int)
    # Количество отправляемых за один раз сообщений
    parser.add_argument(
        '-x', '--messages', help='How many messages will be sent in one time', dest='x_messages', default=4, type=int)
    # IP адрес
    parser.add_argument(
        '-l', help='Listen address', dest='l_addr', default='127.0.0.1')
    # Порт первого узла
    parser.add_argument(
        '-p', help='Start port (TCP)', dest='port', default=8000, type=int)
    # Сохраняем считанные аргументы в переменную args
    # В переменной unknown окажется то, что было введенно через командную строку но не определено выше (если такое будет введено)
    args, unknown = parser.parse_known_args()
    del (unknown) # Удаляем ненужное :)
    sum = 0 # Тут суммируем количекство раз, когда все узлы получили пакеты (нужно для вычисления среднего потом)
    sum_iterations = 0 # Тут суммируем количекство итераций до завершения процесса рассылки (нужно для вычисления среднего потом)
    for j in range(args.i_times): # Запускаем симуляцию заданное количество раз
        try:
            # Создаём из запусукаем заденное количество HTTP серверов
            for i in range(args.n_servers):
                run_server(port=args.port + i, server_address=args.l_addr, threads=global_threads, x=args.x_messages)
        except(KeyboardInterrupt, SystemExit): # Чтобы можно было беболезнено прервать аросесс черех Ctrl+C
            stop_threads() # Принудительно завершаем все потоки
            exit(0) # Выходим из программы

        # Посылаем первое (затравочное) сообщение
        if (len(global_threads) > 0): # Это делаем только если потоки с серверами созданы
            global_threads[0].send_first(id=random.randrange(0, 100000000000))


        while if_open_server(global_threads): # Проверяем наличие серверов, находящихся в стадии отправки сообщений
                                              # и крутим цикц, пока хоть кто-то передаёт сообщения
            try:
                sleep(0.01)
            except(KeyboardInterrupt, SystemExit):
                stop_threads()
                exit(0)

        if count_threads(global_threads) == len(global_threads): # Если все сеерверы получили сообщения увеличиваем чсётчик sum на 1
            sum += 1

        # Подсчитываем количество итераций, потребовавшихся до завершения процесса рассылки
        sum_iterations += get_max_iterations(global_threads)

        stop_threads() # Останавливаем и обнуляем все потоки

    # Выводим конечный результат
    print ('In ' + str(100* float(sum) /  args.i_times)  + "% cases all nodes received the packet")
    print('Average number of iterations before the process is complete is ' + str(float(sum_iterations) / args.i_times))
