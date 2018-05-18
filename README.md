This haproxy has the functionality to balance dynamically the http traffic to set of containers associated to a swarm docker service.

The microservices should be stateless, and it should permit to scale up and down the swarm services without any service impact.

Unfortunately this is not always true. Often it's necessary to enable the sticky session for assigning a particular user to a backend server.

The swarm load balancing doesn't have this functionality and for that reason I released this haproxy that implements it by the dns swarm service.

This idea has been inspired by this blog, https://www.haproxy.com/blog/dynamic-scaling-for-microservices-with-runtime-api/, changing different things in the approach suggested.

The only thing to do is create a configuration file in docker swarm setting the name of the backend service to balance and its internal port by the following command:

echo "tasks.backend:80" | docker config create my-config -

Build the image:

docker build -f ./Dockerfile -t haproxy-swarm:1.0 .

docker tag haproxy-swarm:1.0 haproxy-swarm:latest
 
Start a stack. This is an example:

docker stack deploy --prune --compose-file ./stack_haproxy.yml  stack-haproxy --with-registry-auth

Where stack_haproxy.yml is composed by the haproxy and the backend server to balance. My example:


--------------------stack_haproxy.yml ---------------------------------------------
version: '3.3'

services:

  haproxy:
  
    image: haproxy-swarm:latest
	
    configs:
      - my-config
	  
    ports:
	
      - 8888:8888
	  
      - 8099:8099  

  backend:
  
    image: nginx
	
    deploy:
	
      replicas: 1
	  
      update_config:
	  
        delay: 60s
		
    ports:
	
      - 80
--------------------stack_haproxy.yml ---------------------------------------------
	  
The 8099 is the external haproxy exposed port (put what you want changing the haproxy.tmpl file); the 8088 port is the management haproxy port. 

Now you can scale up and down and verify that the containers are added in the load balancer pool after a time out (Default is 10 second) present in haproxy.tmpl file.

In the GUI of haproxy you will see two front end:

fe_main: this is the balanced service to backend containers.
fe_fake: this is a fake service that runs periodically a python script that has the goal to change the haproxy configuration if some scale up or down happened and force the haproxy to reload the configuration.

Good luck.

