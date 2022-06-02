#!/usr/bin/env python
# -*- coding: utf-8 -*-
# AUDIOPHONICS RASPDAC MINI LMS OLED Script #
# 11 Decembre 2018 


# Peter Sketch June 2021
# Update to Python3
# Add two parameters : LMS IP Address and Player MAC
# Default to discover player mac from active interface using netifaces vs. hardcoded 
# Default LMS IP to 127.0.0.1 if not passed as param
# Removed redundent imports
# Manage fixed volume
# Discover song info more efficiently
# Display WiFI IP address instead of LAN IP when WiFi connected
# Dec 21
# Discover LMS IP address
# Enhance display track info
# Loop to reconnect to rebooting LMS server
# Apr 22
# Remove redundent SPDIF code and imports
# May 22
# Improve discovery handling with local LMS
# June 22
# Change to using jsonrpc for polling
# Restrict polling when LMS is off
# Switch to subscription for mode and power change vs. constant polling



import sys
import importlib
importlib.reload(sys)

import telnetlib
import os
import time
import socket
import urllib.parse


def process_params(item):
	for params in sys.argv:
		key = params.split("=")[0]
		if key.upper() == item:
			return str(params.split("=")[1])
	return ""


# importing module
import logging
 
Log_Format = "%(levelname)s %(asctime)s - %(message)s"

# Creating an object
logger = logging.getLogger()
 
# Setting the threshold of logger
logger.setLevel(logging.INFO)

# create console handler
stream_handler = logging.StreamHandler()
stream_handler.setFormatter(logging.Formatter(Log_Format))
logger.addHandler(stream_handler)

if process_params("LOGFILE") == "Y" :
	# create log file handler
	logger.info("Outputting to log file")
	file_handler = logging.FileHandler('evosabre.log', mode='w')
	file_handler.setFormatter(logging.Formatter(Log_Format))
	logger.addHandler(file_handler)


class LMSTelnetServer(object):

	"""
	Server
	"""

	def __init__(self, 
		hostname="localhost",
		port=9090,username="", 
		password="",
		charset="utf8"):

		"""
		Constructor
		"""
		self.debug = False
		self.logger = None
		self.telnet = None
		self.logged_in = False
		self.hostname = hostname
		self.port = port
		self.username = username
		self.password = password
		self.version = ""
		self.player_count = 0
		self.players = []
		self.charset = charset
	
	def connect(self, update=True):
		"""
		Connect
		"""
		self.telnet_connect()
		self.login()
		#self.get_players(update=update)
	
	def telnet_connect(self):
		"""
		Telnet Connect
		"""
		self.telnet = telnetlib.Telnet(self.hostname, self.port)

	def disconnect(self):
		self.telnet.close()
	
	def login(self):
		"""
		Login
		"""
		result = self.request("login %s %s" % (self.username, self.password))
		self.logged_in = (result == "******")
	
	def request(self, command_string, preserve_encoding=False):
		"""
		Request
		"""
		# self.logger.debug("Telnet: %s" % (command_string))
		self.telnet.write(self.__encode(command_string + "\n"))
		response = self.__decode(self.telnet.read_until(self.__encode("\n"))[:-1])
		if command_string == "subscribe mixer" :
			print(response)
		if not preserve_encoding:
			response = self.__unquote(response)
		else:
			command_string_quoted = command_string[0:command_string.find(':')] + command_string[command_string.find(':'):].replace(':',self.__quote(':'))
		if not preserve_encoding:
			if response[:9] != "subscribe" :
				result = response[len(command_string)-1:]
			else :
				result = response
		else:
			result = response[len(command_string_quoted)-1:]
				
		result = result.strip()
		return result

	def read(self, preserve_encoding=False):
		"""
		Read
		"""
		# self.logger.debug("Telnet: %s" % (command_string))
	
		response = self.__decode(self.telnet.read_until(b"\n",0.1))

		if not preserve_encoding:
			response = self.__unquote(response)

		result = response.strip()
		return result
	
	
	def __encode(self, text):
		return text.encode(self.charset)
	
	def __decode(self, bytes):
		return bytes.decode(self.charset)
	
	def __quote(self, text):
		try:
			import urllib.parse
			return urllib.parse.quote(text, encoding=self.charset)
		except ImportError:
			import urllib
			return urllib.quote(text)

	def __unquote(self, text):
		try:
			import urllib.parse
			return urllib.parse.unquote(text, encoding=self.charset)
		except ImportError:
			import urllib
			return urllib.unquote(text)


class Display:
	type=""
	logo_xy = (0,0)
	connecting_line1_xy = (0,0)
	connecting_line2_xy = (0,0)
	connecting_line3_xy = (0,0)
	vol_screen_line1_xy = (0,0)
	vol_screen_line1_y = 0
	vol_bar_start = 0
	vol_screen_rect = (0,0,0,0)
	vol_screeen_factor = 0.0
	title_line1_y = 0
	title_line2_y = 0
	artist_line1_y = 0
	artist_line2_y = 0
	pause_xy = (0, 0)
	title_line3_time_xy = (0, 0)
	title_line3_duration_xy = (0,0)
	title_line3_volume_icon_xy = (0,0)
	title_line3_volume_val_xy = (0,0)
	title_timebar = (0,0,0,0)
	time_ip_logo_xy = (0,0)
	time_ip_val_xy = (0,0)
	time_xy = (0,0)
	time_vol_icon_xy = (0,0)
	time_vol_val_xy = (0, 0)
	screensaver_y = 0
	scroll_unit = 0
	oled_width = 0
	oled_height = 0

display = Display()

oled = "ssd1322"

if oled == "ssd1322":
	display.type="ssd1322"
	display.logo_xy = (6, 0)
	display.connecting_line1_xy = (15, 0)
	display.connecting_line2_xy = (20, 17)
	display.connecting_line3_xy = (20, 34)
	display.vol_screen_line1_xy = (5, 5)
	display.vol_screen_line1_y = 5
	display.vol_bar_start = 0
	display.vol_screen_rect = (0,53,255,60)
	display.vol_screeen_factor = 2.52
	display.title_line1_y = -7
	display.title_line2_y = 20
	display.artist_line1_y = -7
	display.artist_line2_y = 14
	display.pause_xy = (0, 43)
	display.title_line3_time_xy = (0, 41)
	display.title_line3_duration_xy = (55, 41)
	display.title_line3_volume_icon_xy = (200, 44)
	display.title_line3_volume_val_xy = (220, 41)
	display.title_timebar = (0,40,0,44)
	display.time_ip_logo_xy = (120, 45)
	display.time_ip_val_xy = (140, 45)
	display.time_xy = (28,-10)
	display.time_vol_icon_xy = (1, 43)
	display.time_vol_val_xy = (20, 40)
	display.screensaver_y = 45
	display.scroll_unit = 2
	display.oled_width = 256
	display.oled_height = 64

if oled == "ssd1306":
	display.type="ssd1306"
	display.logo_xy = (6, 0)
	display.connecting_line1_xy = (15, 0)
	display.connecting_line2_xy = (20, 22)
	display.connecting_line3_xy = (20, 44)
	display.vol_screen_line1_xy = (0, 25)
	display.vol_screen_line1_y = -10
	display.vol_screen_rect = (120,0,127,62)
	display.vol_bar_start = 58
	display.vol_screeen_factor = 0.5602
	display.title_line1_y = 0
	display.title_line2_y = 25
	display.artist_line1_y = 0
	display.artist_line2_y = 20
	display.pause_xy = (0, 52)
	display.title_line3_time_xy = (1, 48)
	display.title_line3_duration_xy = (55, 48)
	display.title_line3_volume_icon_xy = (85, 51)
	display.title_line3_volume_val_xy = (101, 48)
	display.title_timebar = (0,45,0,47)
	display.time_ip_logo_xy = (1, 32)
	display.time_ip_val_xy = (18, 29)
	display.time_xy = (2, -6)
	display.time_vol_icon_xy = (2, 51)
	display.time_vol_val_xy = (19, 48)
	display.screensaver_y = 45
	display.scroll_unit = 2
	display.oled_width = 128
	display.oled_height = 64

class SongData:
	file_type=""
	fixed_volume=False
	sample_size = ""
	sample_rate = ""
	bitrate = ""
	duration = 0
	elapsed_time = 0
	volume = ""
	artist = ""
	title = ""
	mode = ""
	album = ""
	remote_title = ""

song_data = SongData()

try :
	import netifaces
	import requests
except :
	logger.critical("Required modules are not available.")
	logger.critical("Please check if evosabre-py38-deps.tcz or evosabre-py38-64-deps.tcz extension is loaded.")
	exit("")

from PIL import Image
from PIL import ImageFont

from luma.core.interface.serial import spi
from luma.core.render import canvas

if display.type == "ssd1322" :
	from luma.oled.device import ssd1322
	# OLED Device
	serial = spi(port=0, device=0, gpio_DC=27, gpio_RST=24)
	device = ssd1322(serial, rotate=0, mode="1")

elif display.type == "ssd1306" :
	from luma.oled.device import ssd1306
	# OLED Device
	serial = spi(port=0, device=0, gpio_DC=27, gpio_RST=24)
	device = ssd1306(serial, rotate=2)


#Set the contrast
if len(process_params("CONTRAST")) > 1 :
	try:
		contrast = int(process_params("CONTRAST"))
		if contrast < 0 or contrast > 255 :
			logger.warn("CONTRAST must be between 0 & 255")
			
			contrast = 255
		logger.info("Setting CONTRAST=%s",contrast)
		device.contrast(contrast)
	except:
		logger.error("Unable to set device CONTRAST")


def make_font(name, size):
	font_path = os.path.abspath(os.path.join(
	os.path.dirname(__file__), 'fonts', name))
	return ImageFont.truetype(font_path, size)

# font_title		= make_font('msyh.ttf', 26)
font_info		= make_font('msyh.ttf', 20)
font_vol		= make_font('msyh.ttf', 55)
font_ip			= make_font('msyh.ttf', 15)
font_time		= make_font('msyh.ttf', 18)
# font_20			= make_font('msyh.ttf', 18)
# font_date		= make_font('arial.ttf', 25)
font_logo		= make_font('arial.ttf', 42)
font_32			= make_font('arial.ttf', 50)
awesomefont		= make_font("fontawesome-webfont.ttf", 16)
awesomefontbig	= make_font("fontawesome-webfont.ttf", 42)

# debug
font_debug			= make_font('msyh.ttf', 10)

# speaker			= "\uf028"
wifi			= "\uf1eb"
link			= "\uf0e8"
#clock			= "\uf017"



default_gateway_interface = netifaces.gateways()['default'][netifaces.AF_INET][1]

logger.info ("Default Gateway Interface: %s" , default_gateway_interface)

if default_gateway_interface[0:2] == "wl" :
	logger.info ("WiFi Network Detected")
	is_wifi = True
else :
	logger.info ("Non WiFi WiFi Network Detected")
	is_wifi = False


def get_player_mac():
	if len(process_params("MAC")) > 1 :
		return process_params("MAC")
	else :
		mac = netifaces.ifaddresses(default_gateway_interface)[netifaces.AF_LINK][0]['addr']
		if mac != "":
			logger.info ("Player MAC: %s", mac)
			return mac
		else :
			logger.warning("MAC Discovery failed.  Using 00:11:22:33:44:55")
			return "00:11:22:33:44:55"

def get_player_ip():
	get_ip = netifaces.ifaddresses(default_gateway_interface)[netifaces.AF_INET][0]['addr']
	if get_ip == "":
		get_ip = "127.0.0.1"
	logger.info ("Player IP: %s", get_ip)
	return get_ip

def get_lms_ip():
	if len(process_params("LMSIP")) > 1 :
		lms_ip = process_params("LMSIP")
		lms_name = ""
	else :
		#Discover the LMS IP Address
		logger.info("Discovering LMS IP")
		sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
		sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)

		try:
			sock.bind((player_ip,3483))
		except (socket.error, socket.timeout):
			logger.info ("	Local LMS Detected")
			lms_ip = "127.0.0.1"
			logger.info ("	LMS IP: %s",lms_ip)
			lms_name = ""
		else:
			try:
				sock.settimeout(2.0)
				sock.sendto(b"eNAME\0", ('255.255.255.255', 3483))
				data, addr = sock.recvfrom(1024) # buffer size is 1024 bytes

			except (socket.error, socket.timeout):
				logger.warning ("	Discovery Failure.  Assuming Local LMS")
				lms_ip = "127.0.0.1"
				logger.warning ("	LMS IP: %s",lms_ip)
				lms_name = ""
			else:
				logger.debug("	Broadcast Response: %s", data)
				lms_name = data.decode('UTF-8')[len("eName")+1:]
				lms_ip = str(addr[0])
				logger.info ("	Discovered Server: %s", lms_name)
				logger.info ("	Discovered Server IP: %s",lms_ip)
			finally:
				sock.close()

	return lms_ip,lms_name

def decode_metadata(json):
	
	if json['digital_volume_control'] == 0:
		song_data.fixed_volume = True
	else :
		song_data.fixed_volume = False

	if json['time'] != "":
		song_data.elapsed_time = float(json['time'])
	else :
		song_data.elapsed_time = 0

	if json['mixer volume'] != "":
		song_data.volume = str(json['mixer volume'])
	else :
		song_data.volume = ""

	song_data.file_type = json['playlist_loop'][0]['type']

	try:
		if json['playlist_loop'][0]['samplesize']  == "16":
			song_data.sample_size = "16 Bit / "
		elif json['playlist_loop'][0]['samplesize']  == "24":
			song_data.sample_size = "24 Bit / "
		elif json['playlist_loop'][0]['samplesize']  == "32":
			song_data.sample_size = "32 Bit / "
		else:
			song_data.sample_size = json['playlist_loop'][0]['samplesize']
	except:
		song_data.sample_size = ""

	if json['playlist_loop'][0]['bitrate'] != "":
		song_data.bitrate = str(json['playlist_loop'][0]['bitrate'])
	else :
		song_data.bitrate = ""

	if json['playlist_loop'][0]['duration'] != "":
		song_data.duration = float(json['playlist_loop'][0]['duration'])
	else :
		song_data.duration = 0



	song_data.mode = json['mode']
	song_data.artist = json['playlist_loop'][0]['artist']
	song_data.title = json['playlist_loop'][0]['title']
	song_data.album = json['playlist_loop'][0]['album']
	song_data.remote_title = json['remoteMeta']['title']	

def get_metadata():
	while True:
		try:
			status = lms_request(player_mac,'"status", "-", 1, "tags:galdIrTNo"')
			#logger.debug("Metadata Status : %s", status)
			
		except:
			server_connect()
		else:
			break
	decode_metadata(status)

def lms_request(playermac,params,field=""):
	data = '{ "id": 1, "method": "slim.request", "params": ["' + playermac + '", [' + params + ']]}'
	logging.debug("data is %s", data)
	if len(field) > 0 :
		response = requests.post("http://"+lms_ip+":9000/jsonrpc.js",data=data).json()['result'][field]
	else :
		response = requests.post("http://"+lms_ip+":9000/jsonrpc.js",data=data).json()['result']

	return response


def server_connect():
	while True :
		try :

			global player_ip 
			global player_mac
			global lms_ip

			player_ip = get_player_ip()

			lms_ip, lms_name = get_lms_ip()
			player_mac = str(get_player_mac())
			
			with canvas(device) as draw:
				draw.text(display.connecting_line1_xy,"Connecting to LMS", font=font_time,fill="white")
				if len(lms_name) > 0 :
					draw.text(display.connecting_line2_xy,"LMS Name: " + lms_name, font=font_time,fill="white")
				draw.text(display.connecting_line3_xy,"LMS IP:  " + lms_ip, font=font_time,fill="white")
			time.sleep(1)

			# Handle for subscription
			global subscription_server_handle
			subscription_server_handle = LMSTelnetServer(hostname=lms_ip, port=9090, username="user", password="password", charset='utf8')
			subscription_server_handle.connect()
			subscription_server_handle.request("subscribe power,pause,play,mode")

			logger.info("Subscription Connection Created")

			logger.info("LMS Version: %s" , lms_request("",'"version", "?"',"_version"))
			logger.info("Player Name: %s" , lms_request(player_mac,'"name", "?"',"_value"))
		
		except Exception as e:
			logger.info("Player %s not connected to LMS : %s",player_mac,lms_ip)
			logger.error (e)
			# traceback.print_exc()


			with canvas(device) as draw:
#debug
#				draw.text((5, 20),"E :" + str(e), font=font_debug,fill="white")
				draw.text(display.connecting_line1_xy,"Player Not Connected", font=font_time,fill="white")
				draw.text(display.connecting_line2_xy,"MAC: " + player_mac, font=font_time,fill="white")
				draw.text(display.connecting_line3_xy,"LMS: " + lms_ip, font=font_time,fill="white")
			time.sleep(1)
		else :
			break


# Display logo if we have enough spi buffer size via spidev.bufsiz=8192

bufsizefile = open("/sys/module/spidev/parameters/bufsiz","r")
bufsize = int(bufsizefile.read().strip())
bufsizefile.close()

if bufsize >= 8192:

	logo_path = os.path.abspath(os.path.join(
	os.path.dirname(__file__), "logo.bmp"))
	
	with Image.open(logo_path).convert("1") as logo:
		with canvas(device) as draw:
			draw.bitmap((0, 0),logo,255)

else:
	with canvas(device) as draw:
		draw.text(display.logo_xy,"Audiophonics", font=font_logo,fill="white")

time.sleep(2)

music_file	=""

title_offset	= 0
current_page = 0
vol_val_store = 0
screen_sleep = 0
timer_vol = 0
screensave = 3

info_file = ""
info_file_store = ""
info_state_store = ""
info_artist = ""
info_album = ""
info_title = ""
info_name = ""
info_state = ""

info_duration = 0
time_val = time_min = time_sec = volume_val =  0
volume_val = 0

timer_rates = 10
timer_input = 10

sample_size_val = ""
sample_rate_val = ""
bitrate_val = ""


# Connect to the lms server and set sq handle
server_connect()

# Populdate Metadata once
get_metadata()

info_file = song_data.title
info_state = song_data.mode

logger.info("Player State: %s" , song_data.mode)

lastrun_time = 0

try:
	while True:

		# Check to see if the state has changed
		try:
			subscription_event = urllib.parse.unquote(subscription_server_handle.read(preserve_encoding=True))
		except:
			try:
				subscription_server_handle.disconnect()
				logging.info("Subscription Failed, reconnecting")
			except:
				# Subscription has failed - reconnect
				logging.info("Subscription Failed, reconnecting")
			server_connect()

		if len(subscription_event) > 0 and subscription_event[0:len(player_mac)] == player_mac:
			logger.debug("Subscription Event : %s", subscription_event[len(player_mac)+1:])
			get_metadata()
			lastrun_time = int(time.time() * 1000)
		# Update song data no more than once per 375 milliseconds when not stopped
		elif ((int(time.time() * 1000) - lastrun_time) > 375) and  song_data.mode != "stop": 	
			get_metadata()
			lastrun_time = int(time.time() * 1000)
		# Update song data every 10 secs 
		elif ((int(time.time() * 1000) - lastrun_time) > 10000) :
			logger.debug("10 second update")
			get_metadata()
			lastrun_time = int(time.time() * 1000)
		
		info_file = song_data.title
		info_state = song_data.mode


		# One time update		
		if info_file_store != info_file or info_state_store != info_state:
			timer_rates = 10
			info_artist	 = song_data.artist
			if info_artist == "" :
				info_artist	 = "No Artist"
			info_album	  = song_data.album
			# If there's no Album, is it an internet radio stream
			# remote_title = song_data.album
			if info_album == "" :
				# If there's no Album, is it an internet radio stream
				remote_title = song_data.remote_title
				if remote_title != "" :
					info_album = remote_title
				else :
					info_album	 = "No Album"

			info_title	  = song_data.title

			try :
				info_duration   = song_data.duration 
			except :
				info_duration   = 0

		if timer_rates > 0 :
			info_state = song_data.mode
			sample_size_val = str(song_data.sample_size)
			sample_rate_val = str(song_data.sample_rate)
			filetype_val = str(song_data.file_type)

			if sample_rate_val == "176.4k" :
				sample_rate_val = "DSD64"
			elif sample_rate_val == "352.8k" :
				sample_rate_val = "DSD128"
			elif sample_rate_val == "705.6k" :
				sample_rate_val = "DSD256"
			
			if sample_rate_val != "" :
				bitrate_val = " / " + str(song_data.bitrate)
			else :
				bitrate_val = str(song_data.bitrate)

			timer_rates -= 1

		info_file_store = info_title
		info_state_store = info_state
		
# Continuous update			
		try :
			time_val = song_data.elapsed_time
			time_bar = time_val
			time_min = time_val/60
			time_sec = time_val%60
			time_min = "%2d" %time_min
			time_sec = "%02d" %time_sec
			time_val = str(time_min)+":"+str(time_sec)
		except :
			time_val = 0

		if song_data.fixed_volume == False :
			volume_val = song_data.volume
		else:
			volume_val = str(100)
			vol_val_store = volume_val
		
		timer_input -= 1
		if timer_input == 0 :
			timer_input = 10
		
		
		# Volume change screen.  Only show if it's not fixed volume.
		if volume_val != vol_val_store : timer_vol = 20
		if timer_vol > 0 :
			with canvas(device) as draw:
				vol_width, char = font_vol.getsize(volume_val)
				x_vol = ((display.oled_width - vol_width) / 2)
				# Volume Display
				draw.text(display.vol_screen_line1_xy, text="\uf028", font=awesomefontbig, fill="white")
				draw.text((x_vol, display.vol_screen_line2_y), volume_val, font=font_vol, fill="white")
				# Volume Bar
				draw.rectangle(display.vol_screen_rect, outline=1, fill=0)
				Volume_bar = (display.vol_bar_start - (int(float(volume_val)) * display.vol_screeen_factor)+2)
				draw.rectangle((display.vol_screen_rect[0],
						display.vol_screen_rect[1],
						Volume_bar,
						display.vol_screen_rect[3]), outline=0, fill=1)
			vol_val_store = volume_val
			timer_vol = timer_vol - 1
			screen_sleep = 0
			time.sleep(0.1)	
			
		# Play screen
		elif info_state != "stop":
			
			#reset screen saver counter
			screen_sleep = 0

			if info_title == "" :
				name	= info_file.split('/')
				name.reverse()
				info_title  = name[0]
				try:
					info_album  = name[1]
				except:
					info_album  = ""
				try:
					info_artist = name[2]
				except:
					info_artist = ""
			#if info_name != "" : info_artist = info_name

			if info_duration != 0 :
				time_bar = time_bar / info_duration * display.oled_width

			if info_file != music_file or time_bar < 5 :
				#Called one time / file
				music_file  = info_file
				# Generate title image
	
				#if title_width < artist_width:
				#	title_width = artist_width
				if info_duration != 0 :
					dura_min = info_duration/60
					dura_sec = info_duration%60
					dura_min = "%2d" %dura_min
					dura_sec = "%02d" %dura_sec
					dura_val = "/ " + str(dura_min)+":"+str(dura_sec)
				else : 
					dura_val = ""
				
				artist_offset	= 10
				album_offset	= 10
				title_offset	 = 10
				title_width, char  = font_info.getsize(info_title)
				artist_width, char  = font_info.getsize(info_artist)
				album_width, char  = font_info.getsize(info_album)
				bitrate_width, char = font_ip.getsize(sample_rate_val + sample_size_val + bitrate_val + " " + filetype_val)

				current_page = 0

			# OFFSETS*****************************************************
			x_artist   = 0
			if display.oled_width < artist_width :
				if artist_width < -(artist_offset + 20) :
					artist_offset	= 0
				if artist_offset < 0 :
					x_artist   = artist_offset
				artist_offset	= artist_offset - display.scroll_unit

			x_album   = 0
			if display.oled_width < album_width :
				if album_width < -(album_offset + 20) :
					album_offset	= 0
				if album_offset < 0 :
					x_album   = album_offset
				album_offset	= album_offset - display.scroll_unit	

			x_title   = 0
			if display.oled_width < title_width :
				if title_width < -(title_offset + 20) :
					title_offset	= 0
				if title_offset < 0 :
					x_title   = title_offset
				title_offset	= title_offset - display.scroll_unit	

			x_bitrate = (display.oled_width - bitrate_width) / 2

			if x_bitrate < 0 :
				x_bitrate = 0
						
			with canvas(device) as draw:
				# Title text
				if current_page < 150 :	
					draw.text((x_title, display.title_line1_y), info_title, font=font_info, fill="white")
					if title_width < -(title_offset - display.oled_width) and title_width > display.oled_width :
						draw.text((x_title + title_width + 10, display.title_line1_y), "- " + info_title, font=font_info, fill="white")					
					draw.text((x_bitrate, display.title_line2_y), (sample_size_val + sample_rate_val + bitrate_val + " " + filetype_val), font=font_ip, fill="white")					
				
					current_page = current_page + 1
					artist_offset = 10
					album_offset = 10						
		
				elif current_page < 300	:
					# artist name
					draw.text((x_artist,display.artist_line1_y), info_artist, font=font_info, fill="white")
					if artist_width < -(artist_offset - display.oled_width) and artist_width > display.oled_width :
						draw.text((x_artist + artist_width + 10,display.artist_line1_y), "- " + info_artist, font=font_info, fill="white")
					# album name
					draw.text((x_album, display.artist_line2_y), info_album, font=font_info, fill="white")
					if album_width < -(album_offset - display.oled_width) and album_width > display.oled_width :
						draw.text((x_album + album_width + 10,display.artist_line2_y), "- " + info_album, font=font_info, fill="white")

					current_page = current_page + 1
					
					if current_page == 300 :
						current_page = 0
						title_offset = 10

				# Bottom line
				if info_state == "pause": 
					draw.text(display.pause_xy, text="\uf04c", font=awesomefont, fill="white")
				else:
					draw.text(display.title_line3_time_xy, time_val, font=font_time, fill="white")
					draw.text(display.title_line3_duration_xy, dura_val, font=font_time, fill="white")
				
				draw.rectangle((display.title_timebar[0],
					display.title_timebar[1],
					time_bar,
					display.title_timebar[3]), outline=0, fill=1)

				if song_data.fixed_volume == False :
					draw.text(display.title_line3_volume_icon_xy, text="\uf028", font=awesomefont, fill="white")
					draw.text(display.title_line3_volume_val_xy, volume_val, font=font_time, fill="white")

			time.sleep(0.05)

		else:
			# Time IP screen
			if screen_sleep < 20000 :
				with canvas(device) as draw:
					if is_wifi == False :
						# LAN IP Address
						network_logo = link
					else:
						# Wifi IP Address
						network_logo = wifi

					draw.text(display.time_ip_logo_xy, network_logo, font=awesomefont, fill="white")
					draw.text(display.time_ip_val_xy, player_ip, font=font_ip, fill="white")

					draw.text(display.time_xy,time.strftime("%X"), font=font_32,fill="white")
					if song_data.fixed_volume == False :
						draw.text(display.time_vol_val_xy, volume_val, font=font_time, fill="white")
						draw.text(display.time_vol_icon_xy, text="\uf028", font=awesomefont, fill="white")
				screen_sleep = screen_sleep + 1
			else :
				with canvas(device) as draw:
					screensave += 2
					if screensave > 120 : 
						screensave = 3
					draw.text((screensave, display.screensaver_y), ".", font=font_time, fill="white")
				time.sleep(1)							
			time.sleep(0.1)
except Exception as e:
	exc_type, exc_obj, exc_tb = sys.exc_info()
	fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
	logger.critical((exc_type, fname, exc_tb.tb_lineno))

