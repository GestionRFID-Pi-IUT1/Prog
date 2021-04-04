# coding: utf-8
import mysql.connector
import os.path

# SOCKET
import socket

import json

# RFID
import time
import sys
# END RFID

from datetime import datetime
from os import path

# MYSQL DATABASE CONNECTOR
from mysql.connector import Error
# END MYSQL DATABASE CONNECTOR

# THREADING
import threading
from queue import Queue
# END THREADING


prefix = "[Badgeuse Serveur] "
BUZZPIN = 21
GREENPIN = 7
run = True

def create_connection(host_name, user_name, user_password, user_database):
	connection = None
	try:
		connection = mysql.connector.connect(
			host=host_name,
			user=user_name,
			passwd=user_password,
			database=user_database
		)
		print("Connection to MySQL DB successful")
	except Error as e:
		print("The error '{e}' occurred")
	return connection

def message(string):
	print(prefix+string)

class Badgeuse:
	"""Classe badgeuse caractérisée par :
	- id de la badgeuse
	"""
	"""Constructeur de notre classe badgeuse"""
	def __init__(self, id_badgeuse):
		self.id = id_badgeuse
		self.connection = create_connection("localhost", "root", "toor", "serveur_rfid")
		self.cursor = self.connection.cursor()

	"""Relatif aux demandes d'accès des données"""
	def requestCursor(self):
		self.cursor = self.connection.cursor()

	def commitChange(self):
		self.connection.commit()
		self.cursor.close()
	""" Fin de gestion demande d'accès données"""

	def ajoutPassage(self, uid, nom, access):
		self.requestCursor()

		self.cursor.execute("""INSERT INTO passages (uid, nom, access) VALUES(%s, %s, %s)""", (uid[0], nom[0], access[0]))

		self.commitChange()

	def ajoutPassageInconnu(self, uid, nom, access):
		self.requestCursor()

		self.cursor.execute("""INSERT INTO passages (uid, nom, access) VALUES(%s, %s, %s)""", (uid, nom, access))

		self.commitChange()
	def verifAutorisation(self, uid):
		personne = self.getPersonneFromUID(uid)
		if(personne != False):
			if(str(personne.getAccess()) == "1"):
				return True
			else: 
				return False
		else:
			return False

	def getPersonneFromUID(self, uid):
		self.requestCursor()
		try:
			self.cursor.execute("""SELECT uid, nom, access FROM utilisateurs WHERE uid = %s""", (uid, ))
			row = self.cursor.fetchone()
			return Personne(str(row[0]), str(row[1]), str(row[2]))
		except:
			return False

	def getMode(self, badgeuse_id):
		self.requestCursor()
		try:
			self.cursor.execute("""SELECT mode FROM systeme WHERE id = %s""", (str(badgeuse_id), ))
			row = self.cursor.fetchone()
			self.commitChange()
			return row[0]
		except:
			return 0

	def setMode(self, badgeuse_id, mode):
		self.requestCursor()
		try:
			self.cursor.execute("""UPDATE systeme SET mode = %s WHERE id = %s""", (str(mode), str(badgeuse_id), ))
			row = self.cursor.fetchone()
			self.commitChange()
			return True
		except:
			return False

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

	def parse(self, packet_id):
		return json.dumps({"object": "res_UserAccess", "packet_id": packet_id, "access": "true","uuid": self.getUid()[0], "nom": self.getNom()[0]})

if __name__ == '__main__':
	badgeuse = Badgeuse(id)

	message("Lancement du programme serveur fait avec succès.")
	while run:
		now = datetime.now()
		try:
			socket_ecoute = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
			socket_ecoute.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
			socket_ecoute.bind(('10.0.7.55', 5010))
			socket_ecoute.listen()
			connexion_client, adresse_client = socket_ecoute.accept()

			reponse = connexion_client.recv(1024)
			if reponse != "":
				req = json.loads(reponse)
				if(req["object"] == "req_UserAccess"):
					if(badgeuse.verifAutorisation(req["uuid"]) == True):
						personne = badgeuse.getPersonneFromUID(req["uuid"])
						badgeuse.ajoutPassage(personne.getUid(), personne.getNom(), personne.getAccess())
						connexion_client.send(personne.parse(req["packet_id"]).encode())
					else:
						personne = badgeuse.getPersonneFromUID(req["uuid"])
						if(personne != False):
							badgeuse.ajoutPassage(personne.getUid(), personne.getNom(), personne.getAccess())
						else:
							badgeuse.ajoutPassageInconnu(req["uuid"], "Inconnu au bataillon", 0)
						connexion_client.send((json.dumps({"object": "res_UserAccess", "packet_id": req["packet_id"], "access": "false"})).encode())
				if(req["object"] == "req_Mode"):
					MODE = badgeuse.getMode(str(req["badgeuse_id"]))
					connexion_client.send((json.dumps({"object": "res_Mode", "packet_id": req["packet_id"], "mode": str(MODE)})).encode())
				if(req["object"] == "req_setMode"):
					badgeuse.setMode(req["badgeuse_id"], req["mode"])
		finally: 
		    socket_ecoute.close()

connexion_client.close()
socket_ecoute.close()
