import socket, sys, threading, json,time,optparse,os

def validate_ip(s):
    a = s.split('.')
    if len(a) != 4:
        return False
    for x in a:
        if not x.isdigit():
            return False
        i = int(x)
        if i < 0 or i > 255:
            return False
    return True

def validate_port(x):
    if not x.isdigit():
        return False
    i = int(x)
    if i < 0 or i > 65535:
            return False
    return True

class Tracker(threading.Thread):
    def __init__(self, port, host='0.0.0.0'):
        threading.Thread.__init__(self)
        self.port = port
        self.host = host
        self.BUFFER_SIZE = 8192
        self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.users = {} # current connections  self.users[(ip,port)] = {'exptime':}
        self.files = {} #{'ip':,'port':,'mtime':}
        self.lock = threading.Lock()
        try:
            #YOUR CODE
            #Bind to address and port
            self.server.bind((self.host, self.port))
            
        except socket.error:
            print('Bind failed %s' % (socket.error))
            sys.exit()
        #YOUR CODE
        #listen for connections
        self.server.listen(5)
        print('The server is ready to recieve')

    def check_user(self):
        #YOUR CODE
        #checking users are alive
        ##check if exp time < current time
        for key, value in self.users.items():
            ip = key[0]
            port = key[1]
            exptime = value
            if (value < 0):
                self.lock.acquire()
                # delete the user
                del self.users[key]
                self.lock.release()
                for key1, value1 in self.files.items():
                    if (key1[1] == port):
                        self.lock.acquire()
                        #delete teh files associated to the user
                        del self.files[key]
                        self.lock.release()
            else:
                self.users[key] = exptime - 5
            
                
        timer = threading.Timer(5,self.check_user)
        timer.start()
            
        
    #Ensure sockets are closed on disconnect
    def exit(self):
        self.server.close()

    def run(self):
        timer = threading.Timer(5,self.check_user)
        timer.start()
        print('Waiting for connections on port %s' % (self.port))
        while True:
            #YOUR CODE
            #accept incoming connection and create a thread for receiving messages from FileSynchronizer
            conn,addr = self.server.accept()
            self.users[addr] = 180.0
            # current connections  self.users[(ip,port)] = {'exptime':}
            #self.users[(addr[0],filePort)] = {'exptime': (time.time()+180)}
            threading.Thread(target=self.proces_messages, args=(conn, addr)).start()

    def proces_messages(self, conn, addr):
        conn.settimeout(180.0)
        
        print 'Client connected with ' + addr[0] + ':' + str(addr[1])
        while True:
            #recive data
            data = ''
            while True:
                part = conn.recv(self.BUFFER_SIZE)
                data =data+ part
                if len(part) < self.BUFFER_SIZE:
                    break
            #YOUR CODE
            # check if the received data is a json string and load the json string
            try:
                data_dic = json.loads(data)
                print(data_dic)
            except ValueError as error:
                print("invalid json: %s" % error)
            
            # sync and send files json data
            #sync json data with files dictionary
            filePort = data_dic['port']
            if 'files' in data_dic:
                
                for fil in data_dic['files']:
                    fileName = fil['name']
                    fileTime = fil['mtime']
                    #acquire the lock
                    self.lock.acquire()
                    ##{'ip':,'port':,'mtime':}
                    self.files[fileName] = {'ip':addr[0],'port':filePort,'mtime':fileTime}
                    #release lock
                    self.lock.release()
            #send json data
            conn.sendall(json.dumps(self.files))
        #self.check_user()
        conn.close() # Close
        
if __name__ == '__main__':
    parser = optparse.OptionParser(usage="%prog ServerIP ServerPort")
    options, args = parser.parse_args()
    if len(args) < 1:
        parser.error("No ServerIP and ServerPort")
    elif len(args) < 2:
        parser.error("No  ServerIP or ServerPort")
    else:
        if validate_ip(args[0]) and validate_port(args[1]):
            server_ip = args[0]
            server_port = int(args[1])
        else:
            parser.error("Invalid ServerIP or ServerPort")
    tracker = Tracker(server_port,server_ip)
    tracker.start()
