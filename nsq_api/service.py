import sys
import time
import socket
import json

from tornado import gen, concurrent
import tornado.ioloop
import tornado.web
import requests
from nsq.reader import Reader, Message
from basescript import BaseScript
from deeputil import generate_random_string, AttrDict, keeprunning 
from logagg_utils import NSQSender
from logagg_utils import start_daemon_thread, log_exception

class NsqAPI(tornado.web.RequestHandler):

    NSQ_MAX_IN_FLIGHT = 200
    CHANNEL_NAME_LENGTH = 6
    DELETE_CHANNEL_URL = 'http://{}/channel/delete?topic={}&channel={}'
    executor = concurrent.futures.ThreadPoolExecutor(5)

    def initialize(self, log):

        self.log = log

    def _parse_query(self, query_arguments):
        '''
        query_arguments: {'topic': ['Heartbeat'], 'nsqd_tcp_address': ['195.201.98.142:4150']}
        '''
        nsqd_tcp_addresses = query_arguments.get('nsqd_tcp_address', [''])[0]
        nsqd_http_address = query_arguments.get('nsqd_http_address', [''])[0]
        topic = query_arguments.get('topic', [''])[0]
        if query_arguments.get('empty_lines') == ['yes']:
            empty_lines = True
        else:
            empty_lines = False

        return nsqd_tcp_addresses, nsqd_http_address, topic, empty_lines

    def _remove_channel(self, nsqd_http_address,
            topic, channel):
        '''
        Delete a Nsq channel
        '''
        requests.post(self.DELETE_CHANNEL_URL.format(nsqd_http_address,
            topic, channel))

    @gen.coroutine
    def get(self):
        '''
        Sample uri: /tail?nsqd_tcp_address=localhost:4150&nsqd_http_address=localhost:4151&topic=Heartbeat&empty_lines='yes/no'
        '''
        loop = tornado.ioloop.IOLoop.current()

        nsqd_tcp_addresses, nsqd_http_address, topic, empty_lines = self._parse_query(self.request.query_arguments)
        if not nsqd_tcp_addresses:
            self.finish('nsqd_tcp_addresses not found')
        elif not nsqd_http_address:
            self.finish('nsqd_http_address not found')
        elif not topic:
            self.finish('topic not found')
        else:
            channel = generate_random_string(self.CHANNEL_NAME_LENGTH)


            nsq_reader = Reader(nsqd_tcp_addresses=[nsqd_tcp_addresses],
                    topic=topic,
                    channel=channel,
                    max_in_flight=self.NSQ_MAX_IN_FLIGHT)

            def cleanup():
                nsq_reader.close()
                self._remove_channel(nsqd_http_address=nsqd_http_address,
                        topic=topic, channel=channel)
                self.log.debug('channel_deleted', channel=channel)
                self.finish()
            
            try:
                with nsq_reader.connection_checker():
                    start = time.time()
                    msg_list = list()

                    while True:
                        if self.request.connection.stream.closed():
                            self.log.info('stream_closed')
                            cleanup()
                            break
                        
                        msg = nsq_reader.read()
                        for m in msg:
                            self.log.debug('preparing_list', nsqd_tcp_addresses=nsqd_tcp_addresses, topic=topic, channel=channel)
                            if isinstance(m, Message):
                                msg_list.append(m.body + '\n')
                                m.fin()

                        if time.time() - start >= 1:
                            if msg_list:
                                result = ''.join(msg_list)
                                self.log.debug('yield', nsqd_tcp_addresses=nsqd_tcp_addresses, topic=topic, channel=channel, result=result)
                                self.write(result)
                                yield self.flush()
                                msg_list = list()
                                start = time.time()
                            else:
                                self.log.debug('empty', nsqd_tcp_addresses=nsqd_tcp_addresses, topic=topic, channel=channel)
                                if empty_lines: self.write('\n')
                                yield self.flush()

            except KeyboardInterrupt:
                cleanup()
                sys.exit(0)


class NsqServer(BaseScript):
    NAME = 'NsqServer'
    DESC = 'Reads nsq topics'
    NAMESPACE = 'nsq_api'
    REGISTER_URL = 'http://{master_address}/logagg/v1/register_nsq_api?key={key}&secret={secret}&host={host}&port={port}'


    def _parse_master_args(self):

        if self.args.no_master: return None

        master = AttrDict()
        try:
            m = self.args.master.split(':')
            for a in m:
                a = a.split('=')
                if a[0] == 'host': master.host = a[-1]
                elif a[0] == 'port': master.port = a[-1]
                elif a[0] == 'key': master.key = a[-1]
                elif a[0] == 'secret': master.secret = a[-1]
                else: raise ValueError
        except ValueError:
            raise Exception('Invalid Argument', self.args.master)
        if not master.keys() == ['host', 'port', 'key', 'secret']:
            raise Exception('Invalid Argument', self.args.master)
        return master
 

    def register_to_master(self):
        '''
        'http://localhost:1088/logagg/v1/register_nsq_api?key=xyz&secret=xxxx&host=172.168.0.12&port=1077' 
        '''
        master = self.master

        register_url = self.REGISTER_URL.format(master_address=master.host+':'+master.port,
                                                host=self.host,
                                                port=self.port,
                                                key=self.master.key,
                                                secret=self.master.secret)

        try:
            register = requests.get(register_url)
            register_response = json.loads(register.content.decode('utf-8'))
        except requests.exceptions.ConnectionError:
            raise Exception('Could not reach master, url: {}'.format(register_url))

        return register_response


    def prepare_api(self):
        return tornado.web.Application([
        (r'/tail', NsqAPI,
        dict(log=self.log)),
        ])

    def start(self):
        self.actively_tailing = dict()
        self.master = self._parse_master_args()
        self.host = self.args.host
        self.port = self.args.port

        if not self.master:
            self.log.info('no_master')

        else:
            register_response = self.register_to_master()
            if register_response.get('result', {}).get('success', {}): self.log.info('authentication_passed')
            else: raise Exception(register_response.get('result', {}).get('details', {}))

        try:
            app = self.prepare_api()
            app.listen(self.args.port)
            tornado.ioloop.IOLoop.current().start()
        except KeyboardInterrupt:
            # FIXME: cleanup if exited
            self.log.info('exiting')


    def define_subcommands(self, subcommands):
        super(NsqServer, self).define_subcommands(subcommands)

        runserver_cmd = subcommands.add_parser('runserver',
                help='NsqServer Service')

        runserver_cmd.set_defaults(func=self.start)

        runserver_cmd.add_argument('-p', '--port',
                default=1077,
                help='NsqServer port, default: %(default)s')
        runserver_cmd.add_argument('-i', '--host',
                default=socket.gethostname(),
                help='Hostname of this service for other components to contact to, default: %(default)s')
        runserver_cmd.add_argument('-m', '--master',
                help='Master address, format: host=<hostname>:port=<port>:key=<master_key>:secret=<master_secret>')
        runserver_cmd.add_argument('-n', '--no-master',
                action='store_true',
                help= 'If NSQ-API is to run independently, without a master service')

def main():
    NsqServer().start()

if __name__ == '__main__':
    main()
