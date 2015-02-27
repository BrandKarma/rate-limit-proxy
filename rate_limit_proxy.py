#!/usr/bin/env python

from __future__ import (print_function, absolute_import, unicode_literals, division)

from datetime import datetime
import tornado.httpserver
import tornado.gen
import tornado.log
import tornado.ioloop
import tornado.iostream
import tornado.options
import tornado.log
import tornado.web
import tornado.httpclient
import logging


class RateLimitProxy(tornado.web.Application):
    def __init__(self):
        current = datetime.now()

        self.data_store = {
            "per_x_seconds": 60.0,
            "leaky_bucket_rate_limit_info": { "graph.facebook.com": { "last_check": current,
                                                                      "allowance": 60.0,
                                                                      "rate": 60.0 },
                                              "api.twitter.com": { "last_check": current,
                                                                   "allowance": 50.0,
                                                                   "rate": 50.0 },
                                              "bsapi.vmaibo.com": { "last_check": current,
                                                                    "allowance": 20.0,
                                                                    "rate": 20.0 }
                                             }
        }

        handlers = [(r'.*', RateLimitHandler, dict(data_store=self.data_store))]
        tornado.web.Application.__init__(self, handlers)


class RateLimitHandler(tornado.web.RequestHandler):
    SUPPORTED_METHODS = ['GET', 'POST']

    def initialize(self, data_store):
        self.data_store = data_store


    def post(self):
        self.get()

    @tornado.gen.coroutine
    def get(self):
        def handle_response(response):
            if response.error and not isinstance(response.error, tornado.httpclient.HTTPError):
                self.set_status(500)
            elif response.code == 429:
                self.set_status(429, "Too Many Requests")
                self.write('Request cannot be served due to the application\'s rate limit having been exhausted for the resource')
            else:
                self.set_status(response.code)
                for header in ('Date', 'Cache-Control', 'Server', 'Content-Type', 'Location'):
                    v = response.headers.get(header)
                    if v:
                        self.set_header(header, v)

                if response.body:
                    self.write(response.body)

            self.finish()


        def check_rate_limit(host, leaky_bucket_rate_limit_info, per_x_seconds):
            if host in leaky_bucket_rate_limit_info:
                current = datetime.now()

                info = leaky_bucket_rate_limit_info[host]
                time_passed = current - info["last_check"]
                info["last_check"] = current
                info["allowance"] += time_passed.seconds * (info["rate"] / per_x_seconds)

                if (info["allowance"] > info["rate"]):
                    info["allowance"] = info["rate"]

                if (info["allowance"] < 1.0):
                    return False
                else:
                    info["allowance"] -= 1.0
                    return True
            else:
                return True


        if not check_rate_limit(self.request.host, self.data_store["leaky_bucket_rate_limit_info"], self.data_store["per_x_seconds"]):
            self.set_status(429, "Too Many Requests")
            self.write('Request cannot be served due to the application\'s rate limit having been exhausted for the resource')
            self.finish()
        else:
            if self.request.headers["X-Forwarded-Proto"] in ["http", "https"]:
                proto = self.request.headers["X-Forwarded-Proto"]
                url = '%s://%s%s' %(proto, self.request.host, self.request.uri)
            elif self.request.protocol in ["http", "https"]:
                proto = self.request.protocol
                url = '%s://%s%s' %(proto, self.request.host, self.request.uri)
            else:
                self.set_status(500)
                self.finish()


            req = tornado.httpclient.HTTPRequest(url=url,
                                                method=self.request.method,
                                                body=self.request.body,
                                                headers=self.request.headers,
                                                connect_timeout=60.0,
                                                request_timeout=60.0,
                                                follow_redirects=True,
                                                allow_nonstandard_methods=True)

            client = tornado.httpclient.AsyncHTTPClient()
            try:
                resp = yield client.fetch(req)
                handle_response(resp)
            except tornado.httpclient.HTTPError as e:
                if hasattr(e, 'response') and e.response:
                    handle_response(e.response)
                else:
                    self.set_status(500)
                    self.finish()



def run(port):
    try:
        app = RateLimitProxy()
        app.listen(port)
        ioloop = tornado.ioloop.IOLoop.instance()
        ioloop.start()
    except KeyboardInterrupt:
        print("Shutting Down..")



def main():
    tornado.options.define("port", default=8000, help="run on the given port", type=int)

    tornado.options.parse_command_line()
    tornado.log.enable_pretty_logging()

    print("Starting HTTP proxy on port %d" % (tornado.options.options.port))
    run(tornado.options.options.port)


if __name__ == "__main__":
    main()
