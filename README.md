# nsq-api
API to read logs from [NSQ](https://nsq.io/) topics.
Returns a streaming response off a randomly named channel which is deleted after the stream is closed.

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

## [Read full documentation](https://deep-compute.github.io/nsq-api/)
