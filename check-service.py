#!/usr/bin/python
import requests
import socket
import sys
import os
from jinja2 import Template
import logging


logger = logging.getLogger('haproxy-check')
hdlr = logging.FileHandler('/var/tmp/haproxy-check.log')
formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
hdlr.setFormatter(formatter)
logger.addHandler(hdlr) 
logger.setLevel(logging.WARNING)


ServicePort=""
Haproxy_servers=["/var/run/hapee-lb.sock"]
Backend_name="be_template"
#The following are only used for building the configuration from template
Haproxy_template_file="/usr/local/etc/haproxy/haproxy.tmpl"
Haproxy_config_file="/usr/local/etc/haproxy/haproxy.cfg"
Haproxy_spare_slots=0       
Backend_base_name="SRV0"
def send_haproxy_command(server, command):
   if haproxy_server[0] == "/":
      haproxy_sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
   else:
      haproxy_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
   haproxy_sock.settimeout(10)
   try:
      haproxy_sock.connect(haproxy_server)
      haproxy_sock.send(command)
      retval = ""
      while True:
         buf = haproxy_sock.recv(16)
         if buf:
            retval += buf
         else:
            break
      haproxy_sock.close()
   except:
      retval = ""
   finally:
      haproxy_sock.close()
   return retval            
   
def build_config_from_template(backends):
   backend_block=""
   i=0
   for backend in backends:
      i+=1
      backend_block += "   server %s%d %s:%s check port %s\n" % (Backend_base_name, i,backend[0], backend[1],backend[1])
   try:                     
      haproxy_template_fh = open(Haproxy_template_file, 'r')
      haproxy_template = Template(haproxy_template_fh.read())
      haproxy_template_fh.close()
   except:
      logger.error("Failed to read HAProxy config template")
   template_values = {}
   template_values["backends_%s"%(Backend_name)] = backend_block
   try:
      haproxy_config_fh = open(Haproxy_config_file,'w')
      haproxy_config_fh.write(haproxy_template.render(template_values))
      haproxy_config_fh.close()
   except:
      logger.error("Failed to write HAProxy config file")
                            
def read_cfg():
   global Service_name
   global Service_port
   with open('/my-config', 'r') as f:
      reader = f.readlines()
      for row in reader:
         Service_name, Service_port = row.strip().split(':')                            
          
          
if __name__ == "__main__":
   #First, get the servers we need to add
   read_cfg()
   try:
      backend_ip=os.popen('dig %(Service_name)s|grep IN|grep A| grep -v ";"| awk  \'{print $5}\'' % locals()).read()
   except:
      logger.error("Failed to get backend list by dig.")
      sys.exit(1)
   backend_servers=[]
   for server in backend_ip.splitlines():
      backend_servers.append([server, Service_port])
   if len(backend_servers) < 1:
      logger.error("Dig didn't return any servers.")
      sys.exit(2)
   #Now update each HAProxy server with the backends in question
   for haproxy_server in Haproxy_servers:
      haproxy_slots = send_haproxy_command(haproxy_server,"show stat\n")
      if not haproxy_slots:
         logger.error("Failed to get current backend list from HAProxy socket.")
         sys.exit(3)
      haproxy_slots = haproxy_slots.split('\n')
      haproxy_active_backends = {}
      haproxy_inactive_backends = []
      for backend in haproxy_slots:
         backend_values = backend.split(",")
         if len(backend_values) > 80 and backend_values[0] == Backend_name:
            server_name = backend_values[1]
            if server_name == "BACKEND":
               continue
            server_state = backend_values[17]
            server_addr = backend_values[73]
            if server_state == "MAINT":
               #Any server in MAINT is assumed to be unconfigured and free to use (to stop a server for your own wor)                            to just skip it--More-- (83% of 4765 bytes)
               haproxy_inactive_backends.append(server_name)
            else:
               haproxy_active_backends[server_addr] = server_name
                #haproxy_active_backends.append(server_addr)
      len_haproxy_active_backend = len(haproxy_active_backends)
      for backend in backend_servers:
         if "%s:%s" % (backend[0],backend[1]) in haproxy_active_backends:
            del haproxy_active_backends["%s:%s" % (backend[0],backend[1])] #Ignore backends already set
            logger.info(backend[0],backend[1])
   #Finally, rebuild the HAProxy configuration for restarts/reloads
   build_config_from_template(backend_servers)
   if (len(haproxy_active_backends) > 0) or (len_haproxy_active_backend != len(backend_servers)):
         os.popen('pkill -HUP haproxy')
         logger.warning('pkill -HUP haproxy')    
   sys.exit(0)
