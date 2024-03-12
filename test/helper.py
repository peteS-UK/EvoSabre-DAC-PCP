
import telnetlib
import configparser
import socket
import netifaces
import sys
import os
from datetime import datetime

def get_default_gateway_inteface():
	return netifaces.gateways()['default'][netifaces.AF_INET][1]

def process_params(item):
	for params in sys.argv:
		key = params.split("=")[0]
		if key.upper() == item:
			return str(params.split("=")[1])
	return ""

def get_pcp_config(value):
	for line in open('/usr/local/etc/pcp/pcp.cfg'):
		if (line.split("=")[0] == value):
			return(line.split("=")[1].replace('"','').rstrip())
	return ""

from PIL import Image, ImageDraw, ImageFont

from luma.core.render import canvas
import requests

# importing module
import logging
 
Log_Format = "%(levelname)s %(asctime)s - %(message)s"

# Creating an object
logger = logging.getLogger("oled")
 
# Setting the threshold of logger
#logger.setLevel(logging.INFO)

# ignore REQUESTS debug messages
logging.getLogger('REQUESTS').setLevel(logging.ERROR)


def get_lat_lng():
	try:
		url = "https://ipecho.io/my"
		response = requests.get(url).json()
		return float(response['latitude']), float(response['longitude'])
	except:
		return 0.0,0.0


def get_sunrise_data(lat, lng):

	try:
		try:
			url = "https://api.sunrise-sunset.org/json?lat=" + str(lat) + "&lng=" + str(lng) + "&formatted=0"
			response = requests.get(url).json()
		except:
			url = "http://api.sunrise-sunset.org/json?lat=" + str(lat) + "&lng=" + str(lng) + "&formatted=0"
			response = requests.get(url).json()
	except:
		return "unknown","unknown"

	status = response['status']
	if status != "OK":
		return "unknown","unknown"

	return datetime.fromisoformat(response['results']['sunrise']), datetime.fromisoformat(response['results']['sunset'])

def daynight(date, lat, lng):

	global sunrise
	global sunset

	if lat == 0 or lng == 0 :
		return "unknown"

	try:
		if sunrise.strftime("%d") != date.strftime("%d") :			
			# date is from a different day to the last sunrise data, so refresh
			logger.debug("Getting new dusk/dawn data for new day")
			sunrise, sunset = get_sunrise_data(lat, lng)
			logger.debug("Sunrise: %s, Sunset: %s",sunrise, sunset)
	except:
		# No sunrise data currently
		logger.debug("Dusk/Dawn data not set.  Getting new data")
		sunrise, sunset = get_sunrise_data(lat, lng)
		logger.debug("Sunrise: %s, Sunset: %s",sunrise, sunset)


	if sunrise == "unknown":
		return "unknown"

	if date < sunrise:
		return "night"
	elif date > sunrise and date < sunset :
		return "day"
	else:
		return "night"

def set_contrast(daynight, contrast_day, contrast_night, device):
	try:
		if contrast_day < 0 or contrast_day > 255 :
			logger.warn("Day Contrast must be between 0 & 255")
			contrast_day = 255

		if contrast_night < 0 or contrast_night > 255 :
			logger.warn("Night Contrast must be between 0 & 255")
			contrast_night = 255

		if  daynight == "day":
			logger.debug("Setting daytime contrast: %s",contrast_day)
			contrast = contrast_day

		elif daynight == "night":
			logger.debug("Setting nighttime contrast: %s",contrast_night)
			contrast = contrast_night

		else:
			logger.debug("Setting default contrast: %s",contrast_day)
			contrast = contrast_day
	
		device.contrast(contrast)
	except:
		logger.error("Unable to set device Contrast")

def lms_request(lms_ip, playermac,params,field=""):
	data = '{ "id": 1, "method": "slim.request", "params": ["' + playermac + '", [' + params + ']]}'
	#logger.debug("data is %s", data)
	if len(field) > 0 :
		response = requests.post("http://"+lms_ip+":9000/jsonrpc.js",data=data).json()['result'][field]
	else :
		response = requests.post("http://"+lms_ip+":9000/jsonrpc.js",data=data).json()['result']

	return response

def get_digit(number, n):
	return number // 10**n % 10

# Method to read config file settings
def read_config():
	config_path = os.path.abspath(os.path.join(os.path.dirname(__file__), 'oled4pcp.cfg'))
	config = configparser.ConfigParser()
	config.read(config_path)
	return config


def make_font(name, size):
	font_path = os.path.abspath(os.path.join(
	os.path.dirname(__file__), 'fonts', name))
	return ImageFont.truetype(font_path, size)

def parse_int_tuple(input):
	return tuple(int(k.strip()) for k in input[1:-1].split(','))

def parse_tuple(input):
	return tuple(k.strip() for k in input[1:-1].split(','))


class TextImage():
	def __init__(self, device, text, font):
		#with canvas(device) as draw:
		#	w, h = draw.textsize(text, font)

		# Change to getsize to try and workaround screen blink on canvas draw
#		w, h = font.getsize(text)
#		logger.info("Width %d, height %d", w, h)

#		with canvas(device) as draw:
#			left, top, right, bottom = draw.textbbox((0, 0), text, font)
#			logger.info("draw left %d, top %d, right %d, bottom %d", left, top, right, bottom)
#			w, h = right - left, bottom - top

		#left, top, right, bottom = font.getbbox(text)

		#logger.info("BBox left %d, top %d, right %d, bottom %d", left, top, right, bottom)

		# logger.info("getLength %d", font.getlength(text))



		tempimage = Image.new(device.mode, device.size)
		draw = ImageDraw.Draw(tempimage)
		left, top, right, bottom = draw.textbbox((0, 0), text, font)
		# logger.info("draw left %d, top %d, right %d, bottom %d", left, top, right, bottom)
		del draw
		del tempimage


		w = right
		h = bottom

		self.image = Image.new(device.mode, (w, h))
		draw = ImageDraw.Draw(self.image)
		#draw.rectangle((left,top,right,bottom),outline="white")
		draw.text((0, 0), text, font=font, fill="white")
		del draw
		self.width = w
		self.height = h

class Synchroniser():
	def __init__(self):
		self.synchronised = {}

	def busy(self, task):
		self.synchronised[id(task)] = False

	def ready(self, task):
		self.synchronised[id(task)] = True

	def is_synchronised(self):
		for task in self.synchronised.items():
			if task[1] is False:
				return False
		return True


import time

class Scroller():
	WAIT_SCROLL = 1
	SCROLLING = 2
	WAIT_REWIND = 3
	WAIT_SYNC = 4
	PRE_RENDER = 5

	def __init__(self, image_composition, rendered_image, scroll_delay, synchroniser, scroll_speed):
		self.image_composition = image_composition
		self.speed = scroll_speed
		self.image_x_pos = 0
		self.rendered_image = rendered_image
		self.image_composition.add_image(rendered_image)
		self.max_pos = rendered_image.width - image_composition().width
		self.delay = scroll_delay
		self.ticks = 0
		self.state = self.WAIT_SCROLL
		self.synchroniser = synchroniser
		self.render()
		self.synchroniser.busy(self)
		self.cycles = 0
		self.must_scroll = self.max_pos > 0

	def __del__(self):
		self.image_composition.remove_image(self.rendered_image)

	def tick(self, redraw = True):

		# Repeats the following sequence:
		#  wait - scroll - wait - rewind -> sync with other scrollers -> wait
		if self.state == self.WAIT_SCROLL:
			if not self.is_waiting():
				self.cycles += 1
				self.state = self.SCROLLING
				self.synchroniser.busy(self)

		elif self.state == self.WAIT_REWIND:
			if not self.is_waiting():
				self.synchroniser.ready(self)
				self.state = self.WAIT_SYNC

		elif self.state == self.PRE_RENDER:
			self.state = self.WAIT_SYNC

		elif self.state == self.WAIT_SYNC:
			if self.synchroniser.is_synchronised():
				if self.must_scroll:
					if redraw == True:
						self.image_x_pos = 0
						self.render()
				self.state = self.WAIT_SCROLL

		elif self.state == self.SCROLLING:
			if self.image_x_pos < self.max_pos:
				if self.must_scroll:
					self.render()
					self.image_x_pos += self.speed
			else:
				#scroll has.completed
				self.state = self.WAIT_REWIND
		return self.state

	def render(self):
		self.rendered_image.offset = (self.image_x_pos, 0)

	def is_waiting(self):
		self.ticks += 1
		if self.ticks > self.delay:
			self.ticks = 0
			return False
		return True

	def get_cycles(self):
		return self.cycles



def draw_text_centered(draw,y,text,myfont, display):
	text_width, text_height = draw.textsize(text,font=myfont)
	draw.text(((display.width-text_width)/2,y),text,font=myfont,fill="white")
	
def draw_multiline_text_centered(draw,text,myfont, display):
	# text_width, text_height = draw.multiline_textsize(text,font=myfont)
	
	char, char, text_width, text_height = draw.multiline_textbbox((0,0),text,font=myfont)

	draw.text(((display.width-text_width)/2,(display.height-text_height)/2),text,font=myfont,fill="white",align="center")



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

class Display:
	type=""
	serial_interface=""
	logo_xy = (0,0)
	vol_screen_icon_xy = (0,0)
	vol_screen_value_y = 0
	vol_screen_rect = (0,0,0,0)
	title_artist_line1_y = 0
	title_artist_line2_y = 0
	pause_xy = (0, 0)
	title_line3_time_xy = (0, 0)
	title_line3_volume_icon_xy = (0,0)
	title_line3_volume_val_xy = (0,0)
	title_timebar = (0,0,0,0)
	time_ip_logo_xy = (0,0)
	time_ip_val_xy = (0,0)
	time_xy = (0,0)
	time_vol_icon_xy = (0,0)
	time_vol_val_xy = (0, 0)
	scroll_unit = 0
	width = 0
	height = 0
	serial_params = ""
	screensaveS_timeout = 0
	banner_logo_font_size = 0
	banner_text = ""
	logo_file_name = ""
	connecting_font_size = 0
	vol_large_font_size = 0
	logo_font_size = 0
	logo_large_font_size = 0
	title_artist_line_1_font_size = 0
	title_artist_line_2_font_size = 0
	info_font_size = 0
	time_large_font_size = 0
	stopped_polling_interval = 0
	playing_polling_interval = 0
	font_metadata = ""
	font_volume = ""
	font_info = ""
	font_connecting = ""
	font_audiophonics = ""
	font_logo = ""
	font_time=""



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


def get_player_mac(default_gateway_interface):
	if len(process_params("MAC")) > 1 :
		logger.info ("Player MAC: %s", process_params("MAC"))
		return process_params("MAC")
	
	if get_pcp_config("MAC_ADDRESS") != "" :
		logger.info ("Player MAC: %s", get_pcp_config("MAC_ADDRESS"))
		return get_pcp_config("MAC_ADDRESS")
	
	mac = netifaces.ifaddresses(default_gateway_interface)[netifaces.AF_LINK][0]['addr']
	if mac != "":
		logger.info ("Player MAC: %s", mac)
		return mac
	else :
		logger.warning("MAC Discovery failed.  Using 00:11:22:33:44:55")
		return "00:11:22:33:44:55"

def get_player_ip(default_gateway_interface):
	get_ip = netifaces.ifaddresses(default_gateway_interface)[netifaces.AF_INET][0]['addr']
	if get_ip == "":
		get_ip = "127.0.0.1"
	logger.info ("Player IP: %s", get_ip)
	return get_ip



def get_lms_ip(player_ip):
	if len(process_params("LMSIP")) > 1 :
		return process_params("LMSIP"), ""
		
	if get_pcp_config("SERVER_IP") != "" :
		return get_pcp_config("SERVER_IP"), ""

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