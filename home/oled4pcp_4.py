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
# Restrict polling when player is off
# Switch to subscription for mode and power change vs. constant polling
# Read from config file for oled setup
# Change to composed images and updating scrolling design
# Auto switch contrast at dawn and dusk, using data from https://sunrise-sunset.org/api
# Add I2C support



import sys
import importlib
importlib.reload(sys)

import os
import time
from datetime import datetime, timezone

import urllib.parse
import json

import logging


 
File_Log_Format = "%(levelname)s %(asctime)s - %(message)s"
Log_Format = "%(levelname)s	%(message)s"
# Creating an object
logger = logging.getLogger("oled")
 
# Setting the threshold of logger
logger.setLevel(logging.DEBUG)

# ignore REQUESTS debug messages
logging.getLogger('REQUESTS').setLevel(logging.ERROR)

# create console handler
stream_handler = logging.StreamHandler()
stream_handler.setFormatter(logging.Formatter(Log_Format))
stream_handler.setLevel(logging.INFO)
logger.addHandler(stream_handler)

logger.info("PCP OLED Starting")
logger.debug("debug 1")

try :
	import requests
except :
	logger.critical("Required modules are not available.")
	logger.critical("Please check if oled extension is loaded.")
	exit("")

from PIL import Image

from luma.core.interface.serial import spi, i2c
from luma.core.render import canvas
from luma.core.image_composition import ImageComposition, ComposableImage

import helper

if (helper.process_params("LOGFILE") == "Y" or helper.process_params("LOGFILE") == "INFO" or helper.process_params("LOGFILE") == "DEBUG" ):
	# create log file handler
	logger.info("Outputting to log file")
	#file_handler = logging.FileHandler(os.path.abspath(os.path.join(os.path.dirname(__file__), 'pcpoled.log')), mode='a')
	file_handler = logging.FileHandler('/var/log/oled4pcp.log', mode='a')
	file_handler.setFormatter(logging.Formatter(File_Log_Format))
	if helper.process_params("LOGFILE") == "DEBUG":
		logger.info("Setting File Logging to DEBUG")
		file_handler.setLevel(logging.DEBUG)
	logger.addHandler(file_handler)

logger.debug("debug 2")

#Load config values
config = helper.read_config()

# Find the section headings
sections = config.sections()

oled = helper.process_params("OLED").upper()

if len(helper.process_params("OLED")) == 0 :
	oled = config['CONFIG']['oled_section'].upper()

# Has the OLED device been specified 
if oled == 0 :
	logger.critical("OLED Type must be specified with OLED= parameter or in oled4pcp.cfg")
	exit()

display = helper.Display()

# Does the ini contain settings for the specified OLED
if oled not in sections :
	logger.critical("OLED device not defined in oled4pcp.cfg")
	exit()

display.type=config[oled]['type']
display.serial_interface=config[oled]['serial_interface']
display.vol_screen_icon_xy = helper.parse_int_tuple(config[oled]['vol_screen_icon_xy'])
display.vol_screen_value_y = int(config[oled]['vol_screen_value_y'])
display.vol_screen_rect = helper.parse_int_tuple(config[oled]['vol_screen_rect'])
display.title_artist_line1_y = int(config[oled]['title_artist_line1_y'])
display.title_artist_line2_y = int(config[oled]['title_artist_line2_y'])
display.pause_xy = helper.parse_int_tuple(config[oled]['pause_xy'])
display.title_line3_time_xy = helper.parse_int_tuple(config[oled]['title_line3_time_xy'])
display.title_line3_volume_icon_xy = helper.parse_int_tuple(config[oled]['title_line3_volume_icon_xy'])
display.title_line3_volume_val_xy = helper.parse_int_tuple(config[oled]['title_line3_volume_val_xy'])
display.title_timebar = helper.parse_int_tuple(config[oled]['title_timebar'])
display.time_ip_logo_xy = helper.parse_int_tuple(config[oled]['time_ip_logo_xy'])
display.time_ip_val_xy = helper.parse_int_tuple(config[oled]['time_ip_val_xy'])
display.time_xy = helper.parse_int_tuple(config[oled]['time_xy'])
display.time_vol_icon_xy = helper.parse_int_tuple(config[oled]['time_vol_icon_xy'])
display.time_vol_val_xy = helper.parse_int_tuple(config[oled]['time_vol_val_xy'])
display.scroll_speed = int(config[oled]['scroll_speed'])
display.serial_params = config[oled]['serial_params']
display.device_params = config[oled]['device_params']
display.screensave_timeout = int(config['CONFIG']['screensave_timeout'])
display.banner_logo_font_size = int(config[oled]['banner_logo_font_size'])
display.banner_text = config['CONFIG']['banner_text']
display.logo_file_name = config['CONFIG']['logo_file_name']
display.connecting_font_size = int(config[oled]['connecting_font_size'])
display.vol_large_font_size = int(config[oled]['vol_large_font_size'])
display.logo_font_size = int(config[oled]['logo_font_size'])
display.logo_large_font_size = int(config[oled]['logo_large_font_size'])
display.title_artist_line_1_font_size = int(config[oled]['title_artist_line_1_font_size'])
display.title_artist_line_2_font_size = int(config[oled]['title_artist_line_2_font_size'])
display.info_font_size = int(config[oled]['info_font_size'])
display.time_large_font_size = int(config[oled]['time_large_font_size'])
display.playing_polling_interval = int(config['CONFIG']['playing_polling_interval'])
display.stopped_polling_interval = int(config['CONFIG']['stopped_polling_interval'])
display.font_metadata=config[oled]['font_metadata']
display.font_volume=config[oled]['font_volume']
display.font_info=config[oled]['font_info']
display.font_connecting=config[oled]['font_connecting']
display.font_audiophonics=config[oled]['font_audiophonics']
display.font_logo=config[oled]['font_logo']
display.font_time=config[oled]['font_time']

song_data = helper.SongData()

oled_module = importlib.import_module("luma.oled.device")
oled_device = getattr(oled_module,display.type)

if display.serial_interface == "spi":
	serial = spi(**json.loads(display.serial_params))
elif display.serial_interface == "i2c": 
	serial = i2c(**json.loads(display.serial_params))
else:
	logger.critical("Unknown serial_interface in oled4pcp.cfg")
	exit()

device = oled_device(serial, **json.loads(display.device_params))

del oled_module

logger.info("Device Dimensions : %s*%s", device.width, device.height)
logger.info("Device Mode : %s", device.mode)

if device.mode == "RGB" :
	lightfill = "grey"
else :
	lightfill = "white"

display.height=device.height
display.width=device.width

lat = 0
lng = 0

location = helper.process_params("LOCATION")

if location != "":
	logger.info("Location set from argument")
	lat = float(location.split(",")[0])
	lng = float(location.split(",")[1])

elif float(config['CONFIG']['longitude']) != 0 and float(config['CONFIG']['longitude']) != 0:
	logger.info("Location set from config")
	lat = float(config['CONFIG']['latitude'])
	lng = float(config['CONFIG']['longitude'])

else: 
	lat, lng = helper.get_lat_lng()
	if lat != 0 and lng != 0 :
		logger.info("Location %f, %f set by IP discovery", lat, lng)

if lat != 0 and lng != 0 :
	daynight = helper.daynight(datetime.now(tz=timezone.utc), lat, lng)
	logger.info("Current sun location is %s", daynight)
else:
	daynight = "unknown"

daynight_store = daynight

contrast_day = int(config['CONFIG']['contrast_day'])
contrast_night = int(config['CONFIG']['contrast_night'])

#Set the contrasts
helper.set_contrast(daynight, contrast_day, contrast_night, device)

try:
	contrast_screensave = int(config['CONFIG']['contrast_screensave'])
	if contrast_screensave < 0 or contrast_screensave > 255 :
		logger.warn("ScreenSave CONTRAST must be between 0 & 255")	
		contrast_screensave = 255
except:
	logger.error("Unable to get ScreenSave CONTRAST")


font_title_artist_line_1	= helper.make_font(display.font_metadata, display.title_artist_line_1_font_size)
font_title_artist_line_2	= helper.make_font(display.font_metadata, display.title_artist_line_2_font_size)
font_vol_large			= helper.make_font(display.font_volume, display.vol_large_font_size)
font_info				= helper.make_font(display.font_info, display.info_font_size)
font_connecting			= helper.make_font(display.font_connecting, display.connecting_font_size)

font_banner_logo		= helper.make_font(display.font_audiophonics, display.banner_logo_font_size)
font_time_large			= helper.make_font(display.font_time, display.time_large_font_size)
font_logo				= helper.make_font(display.font_logo, display.logo_font_size)
font_logo_large			= helper.make_font(display.font_logo, display.logo_large_font_size)

wifi_logo			= "\uf1eb"
link_logo			= "\uf0e8"
volume_logo 		= "\uf028"
pause_logo			= "\uf04c"
#clock			= "\uf017"


default_gateway_interface = helper.get_default_gateway_inteface()

logger.info ("Default Gateway Interface: %s" , default_gateway_interface)

if default_gateway_interface[0:2] == "wl" :
	logger.info ("WiFi Network Detected")
	is_wifi = True
else :
	logger.info ("Non WiFi WiFi Network Detected")
	is_wifi = False



def decode_metadata(json):
	
	try:
		if json['digital_volume_control'] == 0:
			song_data.fixed_volume = True
			# Fix the volume 100
			song_data.volume = str(100)
		else :
			song_data.fixed_volume = False
			if json['mixer volume'] != "":
				song_data.volume = str(json['mixer volume'])
	except:
		song_data.fixed_volume = False
		song_data.volume = 0

	try:
		if json['time'] != "":
			song_data.elapsed_time = float(json['time'])
		else :
			song_data.elapsed_time = 0
	except:
		song_data.elapsed_time = 0

	try:
		song_data.file_type = json['playlist_loop'][0]['type']
	except:
		song_data.file_type = ""

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

	try:
		sample_rate = json['playlist_loop'][0]['samplerate']
		if sample_rate != "":
			sample_rate = str(float(sample_rate)/1000)+"k"
		if sample_rate == "176.4k" :
			sample_rate = "DSD64"
		elif sample_rate == "352.8k" :
			sample_rate = "DSD128"
		elif sample_rate == "705.6k" :
			sample_rate = "DSD256"
	except:
		sample_rate = ""
	song_data.sample_rate = sample_rate

	try:
		if json['playlist_loop'][0]['bitrate'] != "":
			song_data.bitrate = str(json['playlist_loop'][0]['bitrate'])
		else :
			song_data.bitrate = ""
	except:
		song_data.bitrate = ""

	try:
		if json['playlist_loop'][0]['duration'] != "":
			song_data.duration = float(json['playlist_loop'][0]['duration'])
		else :
			song_data.duration = 0
	except:
		song_data.duration = 0

	try:
		song_data.mode = json['mode']
	except:
		song_data.mode = 'stop'

	try:
		song_data.artist = json['playlist_loop'][0]['artist']
	except:
		song_data.artist = ""
	if song_data.artist == "" :
		song_data.artist = "No Artist"

	try:
		song_data.remote_title = json['remoteMeta']['title']
	except:
		song_data.remote_title = ""

	try:
		song_data.title = json['playlist_loop'][0]['title']
	except:
		song_data.title = ""
	
	try:
		song_data.album = json['playlist_loop'][0]['album']
	except:
		song_data.album = ""

	if song_data.album == "":
		if song_data.remote_title != "" :
			song_data.album = song_data.remote_title
		else :
			song_data.album = "No Album"

def get_metadata():
	while True:
		try:
			status = helper.lms_request(lms_ip, player_mac,'"status", "-", 1, "tags:galdIrTNo"')
			logger.debug("Metadata Response : %s", status)
			
		except:
			server_connect()
		else:
			break
	decode_metadata(status)

	
def server_connect():
	while True :
		try :

			global player_ip 
			global player_mac
			global lms_ip

			player_ip = helper.get_player_ip(default_gateway_interface)

			lms_ip, lms_name = helper.get_lms_ip(player_ip)

			player_mac = str(helper.get_player_mac(default_gateway_interface))
			
			with canvas(device) as draw:
				connecting_text = "Connecting to LMS\n"
				if len(lms_name) > 0 :
					connecting_text += "LMS Name:" + lms_name + "\n"				
				connecting_text += "LMS IP:" + lms_ip
				helper.draw_multiline_text_centered(draw,connecting_text,font_connecting, display)
			time.sleep(1)

			# Handle for subscription
			global subscription_server_handle

			subscription_server_handle = helper.LMSTelnetServer(hostname=lms_ip, port=9090, username="user", password="password", charset='utf8')
			subscription_server_handle.connect()
			subscription_server_handle.request("subscribe power,pause,play,mode")

			logger.info("Subscription Connection Created")

			logger.info("LMS Version: %s" , helper.lms_request(lms_ip,"",'"version", "?"',"_version"))
			logger.info("Player Name: %s" , helper.lms_request(lms_ip, player_mac,'"name", "?"',"_value"))
		
		except Exception as e:
			logger.info("Player %s not connected to LMS : %s",player_mac,lms_ip)
			logger.error (e)

			with canvas(device) as draw:
				connecting_text = "Player Not Connected\n"
				connecting_text += "MAC: " + player_mac +"\n"
				connecting_text += "LMS: " + lms_ip
				helper.draw_multiline_text_centered(draw,connecting_text,font_connecting, display)

			time.sleep(1)
		else :
			break


# Display logo if we have enough spi buffer size via spidev.bufsiz=8192

try:
	bufsizefile = open("/sys/module/spidev/parameters/bufsiz","r")
	bufsize = int(bufsizefile.read().strip())
	bufsizefile.close()
except:
	bufsize = 0

if bufsize >= 8192:

	logo_name = display.logo_file_name
	logo_path = os.path.abspath(os.path.join(
	os.path.dirname(__file__), logo_name))
	
	with Image.open(logo_path).convert("1") as logo:
		with canvas(device) as draw:
			draw.bitmap((0, 0),logo,255)

else:
	with canvas(device) as draw:
		helper.draw_multiline_text_centered(draw,display.banner_text,font_banner_logo, display)

time.sleep(2)

cycle_count = 0
volume_store = 0
screen_sleep = 0
timer_vol = 0

screensave_xy = (3,0)

song_title_store = ""
mode_store = ""
file_info_store = ""

screensave_chars = ("\\","|","/","-","\\","|","/","-","\\","|")
# screensave_height = font_info.getsize("".join(screensave_chars))[1]

screensave_height = font_info.getbbox("".join(screensave_chars))[3]

scroll_states = ("","WAIT_SCROLL","SCROLLING","WAIT_REWIND","WAIT_SYNC","PRE_RENDER")


info_duration = 0
time_val = time_min = time_sec =  0

bitrate_val = ""

# Connect to the lms server and set sq handle
server_connect()

# Populdate Metadata once
get_metadata()

logger.info("Player State: %s" , song_data.mode)

lastrun_time = 0


# Create the static screen compositions
ip_screen_composition = ImageComposition(device)
play_screen_composition = ImageComposition(device)
volume_screen_composition = ImageComposition(device)

if is_wifi == False :
	# LAN IP Address
	network_logo = link_logo
else:
	# Wifi IP Address
	network_logo = wifi_logo

ip_screen_composition.add_image(
	ComposableImage(helper.TextImage(device, network_logo, font=font_logo, fill = lightfill).image, 
	position=display.time_ip_logo_xy))
ip_screen_composition.add_image(
	ComposableImage(helper.TextImage(device, player_ip, font=font_info, fill= lightfill).image, 
	position=display.time_ip_val_xy))
if song_data.fixed_volume == False :
	ip_screen_composition.add_image(
		ComposableImage(helper.TextImage(device, volume_logo, font=font_logo, fill= lightfill).image, 
		position=display.time_vol_icon_xy))
	play_screen_composition.add_image(
		ComposableImage(helper.TextImage(device, volume_logo, font=font_logo, fill= lightfill).image, 
		position=display.title_line3_volume_icon_xy))

try:
	while True:

		# Check to see if the state has changed
		try:
			subscription_event = urllib.parse.unquote(subscription_server_handle.read(preserve_encoding=True))
		except:
			try:
				subscription_server_handle.disconnect()
				logger.info("Subscription Failed, reconnecting")
			except:
				# Subscription has failed - reconnect
				logger.info("Subscription Failed, reconnecting")
			server_connect()

		if len(subscription_event) > 0 and subscription_event[0:len(player_mac)] == player_mac:
			logger.debug("Subscription Event : %s", subscription_event[len(player_mac)+1:])
			get_metadata()
			lastrun_time = int(time.time() * 1000)
		# Update song data no more than once per 375 milliseconds when not stopped
		elif ((int(time.time() * 1000) - lastrun_time) > display.playing_polling_interval) and  song_data.mode != "stop": 	
			try:
				get_metadata()
			except Exception as e:
				logger.info("e : %s",e)
			lastrun_time = int(time.time() * 1000)
		# Update song data every 10 secs 
		elif ((int(time.time() * 1000) - lastrun_time) > display.stopped_polling_interval) :
			logger.debug("10 second update")
			get_metadata()
			lastrun_time = int(time.time() * 1000)

		synchroniser = helper.Synchroniser()

		# One time update		
		if song_title_store != song_data.title or mode_store != song_data.mode or (song_data.sample_size + song_data.sample_rate + str(song_data.bitrate) + song_data.file_type) != file_info_store:

			# Current file or state is different to last loop

			current_TA_page = "title"
			permit_screen_change = True
			cycle_count = 0

			try:
				del scroll_play_line_1
			except:
				logger.debug("Removal Failed")

			ci_play_line_1 = ComposableImage(helper.TextImage(device, song_data.title, font=font_title_artist_line_1).image, 
					position=(0,display.title_artist_line1_y))
			scroll_play_line_1 = helper.Scroller(play_screen_composition, ci_play_line_1, 20, synchroniser, display.scroll_speed)

			try :
				info_duration   = song_data.duration 
			except :
				info_duration   = 0
			
			if song_data.sample_rate != "" :
				bitrate_val = " / " + str(song_data.bitrate)
			else :
				bitrate_val = str(song_data.bitrate)

#			bitrate_width, char = font_title_artist_line_2.getsize(song_data.sample_rate + song_data.sample_size + bitrate_val + " " + song_data.file_type)
			
#			x_bitrate_pos = int((display.width - bitrate_width) / 2)
#			if x_bitrate_pos < 0 :
#				x_bitrate_pos = 0
			
			try:
				del scroll_play_line_2
			except:
				logger.debug("No bitrate to remove")

			ci_play_line_2 = ComposableImage(helper.TextImage(device, song_data.sample_size + song_data.sample_rate + bitrate_val + " " + song_data.file_type, font=font_title_artist_line_2, fill = lightfill).image, 
					position=(0, display.title_artist_line2_y))
			
			scroll_play_line_2 = helper.Scroller(play_screen_composition, ci_play_line_2, 20, synchroniser, display.scroll_speed)

			# Song duration
			if info_duration != 0 :
				dura_min = info_duration/60
				dura_sec = info_duration%60
				dura_min = "%d" %dura_min
				dura_sec = "%02d" %dura_sec
				dura_val = " / " + str(dura_min)+":"+str(dura_sec)
			else : 
				dura_val = ""

		song_title_store = song_data.title
		mode_store = song_data.mode
		file_info_store = song_data.sample_size + song_data.sample_rate + str(song_data.bitrate) + song_data.file_type
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

		# Check to see if day night has changed and change the contrast accordingly
		if screen_sleep < display.screensave_timeout :
			daynight = helper.daynight(datetime.now(tz=timezone.utc), lat, lng)
			if daynight_store != daynight:
				# We've changed day to night or back
				logger.debug("Switching Day/night Contrast")
				daynight_store = daynight
				helper.set_contrast(daynight, contrast_day, contrast_night, device)

		# Volume change screen.  Will only show if it's not fixed volume.
		if song_data.volume != volume_store and song_data.fixed_volume == False : timer_vol = 20
		if timer_vol > 0 :
			
			if screen_sleep >= display.screensave_timeout:
				#The screensaver was showing
				#reset screen saver counter
				screen_sleep = 0
				helper.set_contrast(daynight, contrast_day, contrast_night, device)
			
			with canvas(device) as draw:
				# vol_width, char = font_vol_large.getsize(song_data.volume)
				vol_width = font_vol_large.getlength(song_data.volume)
				x_vol = ((display.width - vol_width) / 2)
				# Volume Display
				draw.text(display.vol_screen_icon_xy, volume_logo, font=font_logo_large, fill="white")
				draw.text((x_vol, display.vol_screen_value_y), song_data.volume, font=font_vol_large, fill="white")
				# Volume Bar
				Volume_bar_width = ((int(float(song_data.volume)) * (display.vol_screen_rect[2]-display.vol_screen_rect[0])/100))
				draw.rectangle((display.vol_screen_rect[0],
						display.vol_screen_rect[1],
						Volume_bar_width,
						display.vol_screen_rect[3]), outline=1, fill= lightfill)
			volume_store = song_data.volume
			timer_vol = timer_vol - 1
			
			screen_sleep = 0
			time.sleep(0.1)	
			
		# Play screen
		elif song_data.mode != "stop":
			
			if screen_sleep >= display.screensave_timeout:
				#The screensaver was showing
				#reset screen saver counter
				screen_sleep = 0
				helper.set_contrast(daynight, contrast_day, contrast_night, device)

			if info_duration != 0 :
				time_bar = time_bar / info_duration * display.width

#			if time_bar < 5 :
#				cycle_count = 0

			# Switch over the lines after 150 cycles

			# if (cycle_count == 150 and scrolling == False) or title_scroll_completed == True:
			if (cycle_count == 150 and permit_screen_change == True):
				#Swap to artist & album
				logger.debug("Swapping to Artist")
				try:
					del scroll_play_line_1
					del scroll_play_line_2
				except:
					logger.debug("No Image to remove")

				ci_play_line_1 = ComposableImage(helper.TextImage(device, song_data.artist
					, font=font_title_artist_line_1).image, 
					position=(0, display.title_artist_line1_y))
				
				ci_play_line_2 = ComposableImage(helper.TextImage(device, song_data.album
					, font=font_title_artist_line_2).image, 
					position=(0, display.title_artist_line2_y))	

				scroll_play_line_1 = helper.Scroller(play_screen_composition, ci_play_line_1, 20, synchroniser, display.scroll_speed)
				scroll_play_line_2 = helper.Scroller(play_screen_composition, ci_play_line_2, 20, synchroniser, display.scroll_speed)

				title_scroll_completed = False
				current_TA_page = "artist"

			if cycle_count > 150 and permit_screen_change == True and current_TA_page == "title":
				# Scrolling is finished
				cycle_count=149

			if (cycle_count == 300 and permit_screen_change == True and current_TA_page == "artist"):
				#Swap to title & bitrate
				logger.debug("Swapping to title")
				try:
					del scroll_play_line_1
					del scroll_play_line_2
				except:
					logger.debug("No Image to remove")

				ci_play_line_1 = ComposableImage(helper.TextImage(device, song_data.title
					, font=font_title_artist_line_1).image, 
					position=(0, display.title_artist_line1_y))
					
				ci_play_line_2 = ComposableImage(helper.TextImage(device, 
					song_data.sample_size + song_data.sample_rate + bitrate_val + " " + song_data.file_type, 
					font=font_title_artist_line_2, fill= lightfill).image, 
					position=(0, display.title_artist_line2_y))
								
				scroll_play_line_1 = helper.Scroller(play_screen_composition, ci_play_line_1, 20, synchroniser, display.scroll_speed)
				scroll_play_line_2 = helper.Scroller(play_screen_composition, ci_play_line_2, 20, synchroniser, display.scroll_speed)

				cycle_count = 0

				current_TA_page = "title"

			if cycle_count > 300 and permit_screen_change == True and current_TA_page == "artist":
				# Scrolling is finished
				cycle_count=299


			if (cycle_count > 300 and current_TA_page == "artist") or (cycle_count > 150 and current_TA_page == "title") :
				#Waiting for a scroll to finish before changing display
				scroll_play_line_1_state = scroll_play_line_1.tick(redraw = False)
				scroll_play_line_2_state = scroll_play_line_2.tick(redraw = False)
			else:	
				scroll_play_line_1_state = scroll_play_line_1.tick()
				scroll_play_line_2_state = scroll_play_line_2.tick()

			if (scroll_states[scroll_play_line_1_state] == "WAIT_SCROLL") and (scroll_states[scroll_play_line_2_state] == "WAIT_SCROLL"):
			
				permit_screen_change = True
			
			else:
				permit_screen_change = False

			#logger.debug("Count %i	L1 %s	L2 %s,	TA %s",cycle_count, scroll_states[scroll_play_line_1_state],scroll_states[scroll_play_line_2_state],current_TA_page )

			cycle_count += 1

			with canvas(device, background=play_screen_composition()) as draw:

				play_screen_composition.refresh()

				# Bottom line
				if song_data.mode == "pause": 
					draw.text(display.pause_xy, text=pause_logo, font=font_logo, fill="white")
				else:
					draw.text(display.title_line3_time_xy, time_val+dura_val, font=font_info, fill= lightfill)
#				
				draw.rectangle((display.title_timebar[0],
					display.title_timebar[1],
					time_bar,
					display.title_timebar[3]), outline=0, fill= lightfill)

				if song_data.fixed_volume == False :
					draw.text(display.title_line3_volume_val_xy, song_data.volume, font=font_info, fill= lightfill)

			time.sleep(0.05)

		else:
			# Time IP screen
			if screen_sleep < display.screensave_timeout :
				with canvas(device, background=ip_screen_composition()) as draw:

					ip_screen_composition.refresh()

					draw.text(display.time_xy,time.strftime("%X"), font=font_time_large,fill="white")
					if song_data.fixed_volume == False :
						draw.text(display.time_vol_val_xy, song_data.volume, font=font_info, fill="white")
				screen_sleep = screen_sleep + 1
			else :
				# Show the screensaver
				with canvas(device) as draw:
					if screen_sleep == display.screensave_timeout:
						# Dim the display
						device.contrast(contrast_screensave)

						# Start screensave on a random char
						screensave_char_index = int(helper.get_digit(time.time(),0))
						try:
							if int(display.height/screensave_char_index) <= display.height - screensave_height:
								screensave_xy = (screensave_xy[0],int(display.height/screensave_char_index))
							else:
								screensave_xy = (screensave_xy[0],int(display.height - screensave_height))
						except:
								screensave_xy = (screensave_xy[0],0)
						screen_sleep = display.screensave_timeout + 1
					screensave_xy = (screensave_xy[0]+2,screensave_xy[1])
					if screensave_xy[0] >= display.width -1 : 
						screensave_xy = (3,screensave_xy[1]+1)
						
					if screensave_xy[1] >= display.height - screensave_height :
						screensave_xy = (screensave_xy[0],0)

					draw.text(screensave_xy, screensave_chars[screensave_char_index], font=font_info, fill="white")
					screensave_char_index += 1
					if screensave_char_index >= 8:
						screensave_char_index =0
				time.sleep(1)							
			time.sleep(0.1)

except Exception as e:
	exc_type, exc_obj, exc_tb = sys.exc_info()
	fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
	logger.critical((exc_type, fname, exc_tb.tb_lineno))
	logger.critical("Class : %s, Cause : %s, e: %s", e.__class__, e.__cause__, e)
	logger.critical("Traceback : %s", e.__traceback__)



