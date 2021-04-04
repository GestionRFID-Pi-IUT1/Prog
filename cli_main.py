# coding: utf-8
import os.path
import RPi.GPIO as GPIO
import lcddriver
import re

import json
import random

# SOCKET
import socket

# RFID
import signal
import time
import sys
from pirc522 import RFID
# END RFID

from datetime import datetime
from os import path

# THREADING
import threading
from queue import Queue
# END THREADING


# Variables système badgeuse cliente
run = True
prefix = "[Badgeuse] "
id = 1

# Mode 0: Normal | Mode 1: ViewUID
global MODE

# Déclarations des pins
BUZZPIN = 21
GREENPIN = 7
REDPIN = 19

def message(string):
	print(prefix+string)

class Personne:

	def __init__(self, uid, nom, access):
		self.uid = uid,
		self.nom = nom,
		self.access = access

	def get(self):
		return self.uid, self.nom, self.access

	def getUid(self):
		return self.uid

	def getNom(self):
		return self.nom

	def getAccess(self):
		return self.access

	def haveAccess(self):
		return (self.access == 1)    

def req_updateMode():
	## Création du paquet 
	packet_id = random.randint(10000, 99999)
	req = {
	  "object": "req_Mode",
	  "badgeuse_id": str(id),
	  "packet_id": packet_id
	}
	requestJson = json.dumps(req)

	## Connexion au serveur
	connexion_serveur = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
	connexion_serveur.connect(('10.0.7.55', 5010))

	## Envoi du paquet 
	connexion_serveur.send(str(requestJson).encode())
	connexion_serveur.settimeout(0.5)
	## Attente de la réponse du serveur
	reponse = connexion_serveur.recv(1024)

	global MODE

	## Traitement de la réponse du serveur
	if reponse != "":
		rep = json.loads(reponse)
		## Si le paquet reçu correspond à une réponse du paquet envoyé précédemment
		if(rep["object"] == "res_Mode" and rep["packet_id"] == packet_id):
			MODE = str(rep["mode"])

def req_setMode(mode):
	if mode == "0" or mode == "1":
		## Création du paquet 
		packet_id = random.randint(10000, 99999)
		req = {
		  "object": "req_setMode",
		  "mode": str(mode),
		  "badgeuse_id": str(id),
		  "packet_id": packet_id
		}
		requestJson = json.dumps(req)

		## Connexion au serveur
		connexion_serveur = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
		connexion_serveur.connect(('10.0.7.55', 5010))

		## Envoi du paquet 
		connexion_serveur.send(str(requestJson).encode())
		connexion_serveur.settimeout(0.5)


def thread_checkViewUid():
	while True:
		try:
			global MODE
			req_updateMode()
			if(MODE == "1"):
				GPIO.output(GREENPIN, GPIO.HIGH)
			else:
				GPIO.output(GREENPIN, GPIO.LOW)
			time.sleep(1)
		except:
			return False

def setupGPIO():
	GPIO.setmode(GPIO.BOARD)
	GPIO.setup(BUZZPIN, GPIO.OUT)
	GPIO.setup(GREENPIN, GPIO.OUT)
	GPIO.setup(REDPIN, GPIO.OUT)
	GPIO.setwarnings(False)

def buzz(authorized):
	if(authorized):
		GPIO.output(BUZZPIN, GPIO.HIGH)
		GPIO.output(GREENPIN, GPIO.HIGH)
		time.sleep(0.4)
		GPIO.output(BUZZPIN, GPIO.LOW)
		GPIO.output(GREENPIN, GPIO.LOW)
	else:
		GPIO.output(BUZZPIN, GPIO.HIGH)
		GPIO.output(REDPIN, GPIO.HIGH)
		time.sleep(0.3)
		GPIO.output(BUZZPIN, GPIO.LOW)
		GPIO.output(REDPIN, GPIO.LOW)
		time.sleep(0.2)
		GPIO.output(BUZZPIN, GPIO.HIGH)
		GPIO.output(REDPIN, GPIO.HIGH)
		time.sleep(0.3)
		GPIO.output(BUZZPIN, GPIO.LOW)
		GPIO.output(REDPIN, GPIO.LOW)

def cooldown(seconds, lcd):
	for x in range(seconds):
		lcd.lcd_display_string("{} secondes ...".format(str(seconds-x)), 4)
		time.sleep(1)

def end_read(signal,frame):
	global run
	print("\nCtrl+C captured, ending read.")
	run = False
	rdr.cleanup()
	sys.exit()

if __name__ == '__main__':
	setupGPIO()

	#setup LCD
	lcd = lcddriver.lcd()
	lcd.lcd_clear()

	#setup pirc522
	rdr = RFID()
	signal.signal(signal.SIGINT, end_read)
	GPIO.output(BUZZPIN, GPIO.LOW)

	t = threading.Thread(target=thread_checkViewUid, args=())
	t.start()

	message("Lancement du programme fait avec succès.")
	while run:
		now = datetime.now()
		lcd.lcd_clear()

		lcd.lcd_display_string("Scannez votre badge", 1)
		lcd.lcd_display_string("     <-------->", 3)
		lcd.lcd_display_string("Badgeuse #{}".format(str(id)), 4)	
		message("Attente d'un passage:")
		
		rdr.wait_for_tag() #attente d'un passage de tag rfid
		(error, data) = rdr.request()
		(error, uid) = rdr.anticoll()

		if not error: #si le passage du tag ne contient pas d'erreur
			uuid = str(uid[0])+str(uid[1])+str(uid[2])+str(uid[3]) #sauvegarde l'uid du tag
			print(prefix+"Carte détectée UID: "+str(uuid))
			
			global MODE
			if MODE == "1": #Si badgeuse en MODE view UID
				lcd.lcd_clear()
				now = datetime.now()
				date_time = now.strftime("%d/%m/%Y, %H:%M:%S")
				lcd.lcd_display_string("    MODE VIEWUID", 1)
				lcd.lcd_display_string("ID DU TAG:", 2)
				lcd.lcd_display_string(str(uuid), 3)
				buzz(True)
				cooldown(8, lcd)
				req_setMode("0")

			if MODE == "0":
				## Création du paquet 
				packet_id = random.randint(10000, 99999)
				req = {
				  "object": "req_UserAccess",
				  "packet_id": packet_id,
				  "uuid": str(uuid)
				}
				requestJson = json.dumps(req)

				## Connexion au serveur
				connexion_serveur = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
				connexion_serveur.connect(('10.0.7.55', 5010))

				## Envoi du paquet 
				connexion_serveur.send(str(requestJson).encode())

				## Attente de la réponse du serveur
				reponse = connexion_serveur.recv(1024)

				## Traitement de la réponse du serveur
				if reponse != "":
					rep = json.loads(reponse)
					## Si le paquet reçu correspond à une réponse du paquet envoyé précédemment
					if(rep["object"] == "res_UserAccess" and rep["packet_id"] == packet_id):
						## Si le paquet reçu contient un accès autorisé
						if(rep["access"] == "true"):
							lcd.lcd_clear()
							now = datetime.now()
							date_time = now.strftime("%d/%m/%Y, %H:%M:%S")

							## Obtention du nom de la personne [20 caractères max]
							nom = str(rep["nom"])[:20]

							## Affichage du nom, date et passage autorisé sur lcd
							lcd.lcd_display_string(nom, 1)
							lcd.lcd_display_string("  Passage autorise", 2)
							lcd.lcd_display_string(date_time, 4)	

							buzz(True)
							time.sleep(3)
							continue
						else:
							## Si le paquet reçu contient un accès refusé
							lcd.lcd_clear()
							now = datetime.now()            
							date_time = now.strftime("%d/%m/%Y, %H:%M:%S")
						

							## Affichage date et passage refusé sur lcd
							lcd.lcd_display_string("  Passage refuse", 2)
							lcd.lcd_display_string(date_time, 4)
							
							buzz(False)
							time.sleep(3)