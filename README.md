# Rate limiter proxy

## Introduction 
This is a proof-of-concept prototype. Before deploying to the production environemt, it must be tested with apache bench or weighttp. if the benchmark doesn't show good figures, the proxy server would be better  re-implemented in other programming languages with a better runtime concurrent connection supports, like golang or ghc.

The idea is coming from [slowweb](https://github.com/benbjohnson/slowweb). Unlike slowweb hacking into the lower level of ruby network libraries, this rate limiter proxy is to spinned off into a separate instance. The crawler machines or API calling machines can set their targeted sites' location in their /etc/hosts, so that any of the HTTP call would be routed through transparent proxies. The rate limiter would load predetermined rate limit. If the limit is reached, this proxy would return 503 service unavailable once request timeout. The clients then could delay their calling and retry again later. This prevents any of the HTTP client being banned by the API providers. Even if the proxies' IP are banned, deploy another AWS EC2 instance and renew the proxy setting on the API callers then we are good. In the case that one proxy cannot handle the heavy traffic from clients, we can shard the traffic by domain name. This solution is transparent and no existing codes need to be modified to conform to the good behavior.

## Why not nginx?
Nginx has a [HTTP limit module](http://wiki.nginx.org/HttpLimitReqModule), but the remote address has to be in binary IP format.

## Why not rate limiter in the Celery itself?
The rate limit's unit is by tasks, but not by either the HTTP request numbers or the volume of the byte counts.
