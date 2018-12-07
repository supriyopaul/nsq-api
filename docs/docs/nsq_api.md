## Prerequisites
- Python = 2.7

## Installation
Install nsq-api package to start the service.
```
pip install git+https://github.com/deep-compute/nsq-api.git
```

## Run nsq-api service
Start service without a [logagg-master](https://github.com/deep-compute/logagg-master).
```
$ nsq-api runserver --host <IP/DNS> --port <port_number> --no-master
```
Start service and register it to [logagg-master](https://github.com/deep-compute/logagg-master).
```
nsq-api runserver --host <IP/DNS> --port <port_number> --master host=<master_host>:port=<master_port>:key=<master_key>:secret=<master_secret>
```

## Send messages to a topic in NSQ
###### [Install](http://nsq.io/deployment/installing.html) the `nsq` package, at where we need to bring up the `nsq` server.
- Run the following commands to install `nsq`:
```
$ sudo apt-get install libsnappy-dev
$ wget https://s3.amazonaws.com/bitly-downloads/nsq/nsq-1.0.0-compat.linux-amd64.go1.8.tar.gz
$ tar zxvf nsq-1.0.0-compat.linux-amd64.go1.8.tar.gz
$ sudo cp nsq-1.0.0-compat.linux-amd64.go1.8/bin/* /usr/local/bin
```

###### Bring up the `nsq` instances at the required server with following commands:
- **NOTE:** Run each command in a seperate Terminal window
- nsqlookupd
```
$ nsqlookupd
```
- nsqd -lookupd-tcp-address *<ip-addr or DNS\>*:4160
```
$ nsqd -lookupd-tcp-address localhost:4160
```
- nsqadmin -lookupd-http-address *<ip-addr or DNS\>*:4161
```
$ nsqadmin -lookupd-http-address localhost:4161
```

###### Sending messages to NSQ topic
```
$ apt install curl
$ for i in {1..500}; do curl -d 'This is message number: '$i 'http://localhost:4151/pub?topic=test'; sleep 1; done
OKOKOKOKOKOKOKOKOK...
```

###### Read logs from a NSQ topic using nsq-api
```
$ curl "http://localhost:4444/tail?nsqd_tcp_address=localhost:4150&topic=test&empty_lines=no"
...
This is message number: 10
This is message number: 11
This is message number: 12
This is message number: 13
...
...
```
