import socket, sys, threading, json,time,os,ssl
import os.path
import glob
import json
import optparse


#Validate the IP address of the correct format
def validate_ip(s):
    """
    Arguments:
    s -- dot decimal IP address in string

    Returns:
    True if valid; False otherwise
    """

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

#Validate the port number is in range [0, 2^16-1]
def validate_port(x):
    """
    Arguments:
    x -- port number

    Returns:
    True if valid; False, otherwise
    """

    if not x.isdigit():
        return False
    i = int(x)
    if i < 0 or i > 65536:
            return False
    return True


#Get file info in the local directory (subdirectories are ignored)
#NOTE: Exclude files with .so, .py, .dll suffixes
def get_file_info():
    """
    Return: a JSON array of {"name":file,"mtime":mtime}
    """
    # YOUR CODE
    files = []
    fileInfo = os.listdir('.')
    for f in fileInfo:
        if not(f.endswith(".so") or f.endswith(".py") or f.endswith(".dll")):
            fileName = f
            mtime = os.path.getmtime(fileName)
            dictFile = {"name":fileName, "mtime":mtime}
            files += [dictFile]
    print("Files collected from local directory")
    return files
        
    

#Check if a port is available
def check_port_avaliable(check_port):
    """
    Arguments:
    check_port -- port number

    Returns:
    True if valid; False otherwise
    """
    if str(check_port) in os.popen("netstat -na").read():
        return False
    return True

#Get the next available port by searching from initial_port to 2^16 - 1
#Hint: use check_port_avaliable() function
def get_next_avaliable_port(initial_port):
    """
    Arguments:
    initial_port -- the first port to check

    Return:
    port found to be available; False if no port is available.
    """
    # YOUR CODE
    for currPort in range(initial_port,65536):
        if (check_port_avaliable(currPort)):
            print("Port available.")
            return currPort
    return False

class FileSynchronizer(threading.Thread):
    def __init__(self, trackerhost,trackerport,port, host='0.0.0.0'):

        threading.Thread.__init__(self)
        #Port for serving file requests
        self.port = port #YOUR CODE
        self.host = host #YOUR CODE

        #Tracker IP/hostname and port
        self.trackerhost = trackerhost #YOUR CODE
        self.trackerport = trackerport #YOUR CODE

        self.BUFFER_SIZE = 8192

        #Create a TCP socket to communicate with tracker
        self.client = socket.socket(socket.AF_INET, socket.SOCK_STREAM) #YOUR CODE
        self.client.settimeout(180)

        #Store the message to be sent to tracker. Initialize to Init message
        #that contains port number and local file info.
        self.msg = {'port':self.port, 'files': get_file_info()} #YOUR CODE
        print ("Message stored to be sent to tracker.")
        #Create a TCP socket to serve file requests
        self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM) #YOUR CODE
        print("TCP socket to serve file requests created.")
        try:
            self.server.bind((self.host, self.port))
        except socket.error:
            print('Bind failed %s' % (socket.error))
            sys.exit()
        self.server.listen(10)

    # Not currently used. Ensure sockets are closed on disconnect
    def exit(self):
        self.server.close()

    #Handle file request from a peer
    def process_message(self, conn,addr):
        """
        Arguments:
        self -- self object
        conn -- socket object for an accepted connection from a peer
        addr -- address bound to the socket of the accepted connection
        """
        #YOUR code
        #Step 1. read the file name contained in the request
        #receive data
        data = ''
        while True:
            part = conn.recv(self.BUFFER_SIZE)
            data = data + part
            print("Reading file name in the request.")
            if len(part) < self.BUFFER_SIZE:
                break
    
        #Step 2. read the file from local directory (assuming binary file < 4MB)
        fileRead = open(data,'r')
        fileData = fileRead.read()
        fileRead.close()
        print("read from local directory.")
        #Step 3. send the file to the requester
        conn.sendall(fileData)
        conn.close()

    def run(self):
        self.client.connect((self.trackerhost,self.trackerport))
        t = threading.Timer(2, self.sync)
        t.start()
        print('Waiting for connections on port %s' % (self.port))
        while True:
            conn, addr = self.server.accept()
            threading.Thread(target=self.process_message, args=(conn,addr)).start()

    #Send Init or KeepAlive message to tracker, handle directory response message
    #and call self.syncfile() to request files from peers
    def sync(self):
        print 'connect to:'+ self.trackerhost,self.trackerport
        #Step 1. send Init msg to tracker
        #YOUR CODE
        self.client.sendall(json.dumps(self.msg))
        print("Send Init msg to tracker.")
        #Step 2. receive a directory response message from tracker
        #YOUR CODE
        directory_response_message = ''
        while True:
            part = self.client.recv(self.BUFFER_SIZE)
            directory_response_message = directory_response_message + part
            if len(part) < self.BUFFER_SIZE:
                break
        print("Recieve a directory response message from tracker.")
        try:
            data_dic = json.loads(directory_response_message)
        except ValueError as error:
            print("invalid json: %s" % error)
                
        
        #Step 3. parse the directory response message. if it contains new or
        #more up-to-date files, request the files from the respective peers.
        #NOTE: compare the modified time of the files in the message and
        #that of local files of the same name.
        #YOUR CODE
        for f in data_dic:
            print("Parse directory response message.")
            ip = data_dic[f]['ip']
            port = data_dic[f]['port']
            mtime = data_dic[f]['mtime']
            if os.path.isfile(f):
                if mtime > os.path.getmtime(f):
                    newSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    newSocket.connect((ip,port))
                    newSocket.sendall(f)
                    message = ''
                    while True:
                        part = newSocket.recv(self.BUFFER_SIZE)
                        message = message + part
                        print("In sync message:", message)
                        if len(part) < self.BUFFER_SIZE:
                            break
                    newFile = open(f, 'w')
                    newFile.write(message)
                    newFile.close()
                    newSocket.close()
            else:
                newSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                newSocket.connect((ip,port))
                newSocket.sendall(f)
                message = ''
                while True:
                    part = newSocket.recv(self.BUFFER_SIZE)
                    message = message + part
                    print("In sync message:", message)
                    if len(part) < self.BUFFER_SIZE:
                        break
                newFile = open(f, 'w')
                newFile.write(message)
                newFile.close()
                newSocket.close()
                

        #Step 4. construct the KeepAlive message
        self.msg = {'port': 180} #YOUR CODE

        #Step 5. start a timer
        t = threading.Timer(5, self.sync)
        t.start()

if __name__ == '__main__':
    #parse commmand line arguments
    parser = optparse.OptionParser(usage="%prog ServerIP ServerPort")
    options, args = parser.parse_args()
    if len(args) < 1:
        parser.error("No ServerIP and ServerPort")
    elif len(args) < 2:
        parser.error("No ServerIP or ServerPort")
    else:
        if validate_ip(args[0]) and validate_port(args[1]):
            tracker_ip = args[0]
            tracker_port = int(args[1])

        else:
            parser.error("Invalid ServerIP or ServerPort")

    #get the next available port
    synchronizer_port = get_next_avaliable_port(8000)
    synchronizer_thread = FileSynchronizer(tracker_ip,tracker_port,synchronizer_port)
    synchronizer_thread.start()
