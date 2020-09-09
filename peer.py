import csv
import math
from socket import *
import _thread as thread
import random
import time
import json
from threading import *

seeds = []
peers = []
peerList = set()
listener = socket(AF_INET, SOCK_STREAM)
ip = input("Enter ip: ")
listener.bind((ip, 0))
listener.listen(10)
selfAddr = list(listener.getsockname())
messageList = []
livenessTestCount = {}
print(selfAddr)
lock = Lock()


def broadcastMsg(msg):
	msg = (msg + '|').encode()
	for p in peers:
		p.send(msg)


def generateMsg():
	count = 0
	while count<10:
		toSend = str(time.strftime("%Y/%m/%d %H-%M-%S", time.gmtime())) + ':' + str(selfAddr[0]) + ',' + str(selfAddr[1]) + ':' + str(count+1)
		broadcastMsg(toSend)
		count += 1
		time.sleep(5)

def forwardMsg(msg, conn):
	lock.acquire()
	if hash(msg) in messageList:
		lock.release()
		return
	messageList.append(hash(msg))
	lock.release()
	senderAddr = conn.getsockname()
	print(msg + " local timestamp: " + str(time.strftime("%Y/%m/%d %H-%M-%S", time.gmtime())) + senderAddr[0] + ',' + str(senderAddr[1]))
	
	msg = (msg + '|').encode()
	for p in peers:
		if p != conn:
			p.send(msg)


def reportDead(Addr):
	toSend = 'Dead Node:'+str(Addr[0])+':' + str(Addr[1])+':' +str(time.strftime("%Y/%m/%d %H-%M-%S", time.gmtime())) + ':' + str(selfAddr[0]) +','+str(selfAddr[1])
	print(toSend)
	for seed in seeds:
		seed.send((toSend + '|').encode())


def testLiveness():
	while True:
		time.sleep(13)
		toSend = 'Liveness Request:'+str(time.strftime("%Y/%m/%d %H-%M-%S", time.gmtime()))+':'+str(selfAddr[0]) +','+str(selfAddr[1])
		toRemove = []
		for key,value in livenessTestCount.items():
			if value == 3:
				toRemove.append(key)
				reportDead(key)
				continue
			livenessTestCount[key] += 1
		for key in toRemove:
			livenessTestCount.pop(key)
		broadcastMsg(toSend)
	pass	

def confirmLiveness(msg, conn):
	toSend = 'Liveness Reply'+':'+msg[1]+':'+msg[2]+':'+str(selfAddr[0]) +','+str(selfAddr[1]) + '|'
	conn.send(toSend.encode())

def receiver(listener):
	while True:
		msg = listener.recv(1024)
		msg = msg.decode()
		if(msg == ''):
			listener.close()
			peers.remove(listener)
			break
			#if null string received means connection dead but we still need to send livenesss requests and wait for response but calling recv again gives error	

		msg = msg.split('|')
		msg.pop(-1)

		for item in msg:
			temp = item
			item = item.split(':')
			if(item == ''):
				continue
			if(item[0] == 'Liveness Request' ):
				confirmLiveness(item, listener)
			elif(item[0] == 'Liveness Reply'):
				ip, port = item[-1].split(',')
				livenessTestCount[(ip, int(port))] -= 1
			else:
				forwardMsg(temp, listener)

def main():
	# connect_seeds()
	with open('config.csv') as cfg:
		cfg = list(csv.reader(cfg, delimiter=':'))
		n = len((cfg))
		cfg = random.sample((cfg), (math.floor(n/2)+1))
		for entry in cfg:
			try: 
				s = socket(AF_INET, SOCK_STREAM)
			except error as err: 
				print("error creating socket ",err )
			s.connect((entry[0], int(entry[1])))
			seeds.append(s)

	
	#get PL
	peerList = []
	for s in seeds:
		data = json.dumps(selfAddr)
		s.send(data.encode())#listener port number
		msg = s.recv(1024)
		msg = msg.decode()
		msg = json.loads(msg)
		peerList.extend(msg)

	#connecting to peers 
	peerList = set(tuple(i) for i in peerList)
	print("List of Peer Nodes received: ", end='')
	print(peerList)
	noOfPeers = len(peerList)
	if noOfPeers>1:
		upperLimit = min(noOfPeers, 4)
		peerList = random.sample(peerList, random.randint(1,upperLimit))

	for peerAddr in peerList:
		try: 
			p = socket(AF_INET, SOCK_STREAM)
		except error as err: 
			print("error creating socket ",err )
		p.connect(peerAddr)
		peers.append(p)
		livenessTestCount[peerAddr] = 0
		data = json.dumps(tuple(selfAddr))
		p.send(data.encode())
		thread.start_new_thread(receiver, (p,))
		

	thread.start_new_thread( generateMsg, () )
	thread.start_new_thread( testLiveness, () )

	while True:
		c, addr = listener.accept()
		peers.append(c)
		peerAddr = c.recv(1024) #for_updating_seeds_upon_finding out dead node
		peerAddr = json.loads(peerAddr.decode())
		livenessTestCount[tuple(peerAddr)] = 0
		thread.start_new_thread(receiver,(c,))





if __name__ == '__main__':
	main()