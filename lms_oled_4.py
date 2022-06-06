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

import os
import time

import urllib.parse

# importing module
import logging
 
Log_Format = "%(levelname)s %(asctime)s - %(message)s"

# Creating an object
logger = logging.getLogger("oled")
 
# Setting the threshold of logger
logger.setLevel(logging.INFO)

# ignore REQUESTS debug messages
logging.getLogger('REQUESTS').setLevel(logging.ERROR)


# create console handler
stream_handler = logging.StreamHandler()
stream_handler.setFormatter(logging.Formatter(Log_Format))
logger.addHandler(stream_handler)

try :
	import requests
except :
	logger.critical("Required modules are not available.")
	logger.critical("Please check if oled extension is loaded.")
	exit("")

from PIL import Image


from luma.core.interface.serial import spi
from luma.core.render import canvas
from luma.core.image_composition import ImageComposition, ComposableImage

import helper


if helper.process_params("LOGFILE") == "Y" :
	# create log file handler
	logger.info("Outputting to log file")
	file_handler = logging.FileHandler('evosabre.log', mode='w')
	file_handler.setFormatter(logging.Formatter(Log_Format))
	logger.addHandler(file_handler)

display = helper.Display()

oled = "ssd1322"

#Load config values
config = helper.read_config()

display.type=config[oled]['type']
display.logo_xy = helper.parse_int_tuple(config[oled]['logo_xy'])
display.vol_screen_line1_xy = helper.parse_int_tuple(config[oled]['vol_screen_line1_xy'])
display.vol_screen_line2_y = int(config[oled]['vol_screen_line2_y'])
display.vol_bar_start = int(config[oled]['vol_bar_start'])
display.vol_screen_rect = helper.parse_int_tuple(config[oled]['vol_screen_rect'])
display.vol_screeen_factor = float(config[oled]['vol_screeen_factor'])
display.title_artist_line1_y = int(config[oled]['title_artist_line1_y'])
display.title_artist_line2_y = int(config[oled]['title_artist_line2_y'])
display.pause_xy = helper.parse_int_tuple(config[oled]['pause_xy'])
display.title_line3_time_xy = helper.parse_int_tuple(config[oled]['title_line3_time_xy'])
display.title_line3_duration_xy = helper.parse_int_tuple(config[oled]['title_line3_duration_xy'])
display.title_line3_volume_icon_xy = helper.parse_int_tuple(config[oled]['title_line3_volume_icon_xy'])
display.title_line3_volume_val_xy = helper.parse_int_tuple(config[oled]['title_line3_volume_val_xy'])
display.title_timebar = helper.parse_int_tuple(config[oled]['title_timebar'])
display.time_ip_logo_xy = helper.parse_int_tuple(config[oled]['time_ip_logo_xy'])
display.time_ip_val_xy = helper.parse_int_tuple(config[oled]['time_ip_val_xy'])
display.time_xy = helper.parse_int_tuple(config[oled]['time_xy'])
display.time_vol_icon_xy = helper.parse_int_tuple(config[oled]['time_vol_icon_xy'])
display.time_vol_val_xy = helper.parse_int_tuple(config[oled]['time_vol_val_xy'])
display.scroll_speed = int(config[oled]['scroll_speed'])
display.spi_params = config[oled]['spi_params']

song_data = helper.SongData()

if display.type == "ssd1322" :
	from luma.oled.device import ssd1322
	# OLED Device
	serial = spi(port=0, device=0, gpio_DC=27, gpio_RST=24)
	# serial = spi(display.spi_params.split(","))
	
	device = ssd1322(serial, rotate=0, mode="1")


elif display.type == "ssd1306" :
	from luma.oled.device import ssd1306
	# OLED Device
	serial = spi(port=0, device=0, gpio_DC=27, gpio_RST=24)
	device = ssd1306(serial, rotate=2)

logger.info("Device Dimensions : %s*%s", device.width, device.height)
display.height=device.height
display.width=device.width

#Set the contrast
if len(helper.process_params("CONTRAST")) > 1 :
	try:
		contrast = int(helper.process_params("CONTRAST"))
		if contrast < 0 or contrast > 255 :
			logger.warn("CONTRAST must be between 0 & 255")
			
			contrast = 255
		logger.info("Setting CONTRAST=%s",contrast)
		device.contrast(contrast)
	except:
		logger.error("Unable to set device CONTRAST")


font_info		= helper.make_font('msyh.ttf', 20)
font_vol		= helper.make_font('msyh.ttf', 55)
font_ip			= helper.make_font('msyh.ttf', 15)
font_time		= helper.make_font('msyh.ttf', 18)
font_logo		= helper.make_font('arial.ttf', 42)
font_32			= helper.make_font('arial.ttf', 50)
awesomefont		= helper.make_font("fontawesome-webfont.ttf", 16)
awesomefontbig	= helper.make_font("fontawesome-webfont.ttf", 42)
# font_debug			= make_font('msyh.ttf', 10)

wifi_logo			= "\uf1eb"
link_logo			= "\uf0e8"
volume_logo 		= "\uf028"
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
			status = helper.lms_request(lms_ip, player_mac,'"status", "-", 1, "tags:galdIrTNo"')
			#logger.debug("Metadata Status : %s", status)
			
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
				helper.draw_multiline_text_centered(draw,connecting_text,font_time, display)
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

title_offset	= 0
current_page = 0
vol_val_store = 0
screen_sleep = 0
timer_vol = 0

screensave_xy = (3,0)

info_title_store = ""
info_state_store = ""
info_artist = ""
info_album = ""
info_title = ""
info_name = ""
info_state = ""
screensave_chars = ("\\","|","/","-","\\","|","/","-","\\","|")
screensave_height = font_ip.getsize("".join(screensave_chars))[1]

info_duration = 0
time_val = time_min = time_sec = volume_val =  0
volume_val = 0

bitrate_val = ""

#Height difference between ip and info fonts to move bitrate line down
bitrate_line2_adjustment = font_info.getsize("A")[1]-font_ip.getsize("A")[1]

# Connect to the lms server and set sq handle
server_connect()

# Populdate Metadata once
get_metadata()

info_title = song_data.title
info_state = song_data.mode

logger.info("Player State: %s" , song_data.mode)

lastrun_time = 0



# Create the static screen compositions
ip_screen_composition = ImageComposition(device)
play_screen_composition = ImageComposition(device)


if is_wifi == False :
	# LAN IP Address
	network_logo = link_logo
else:
	# Wifi IP Address
	network_logo = wifi_logo

ip_screen_composition.add_image(
	ComposableImage(helper.TextImage(device, network_logo, font=awesomefont).image, 
	position=display.time_ip_logo_xy))
ip_screen_composition.add_image(
	ComposableImage(helper.TextImage(device, player_ip, font=font_ip).image, 
	position=display.time_ip_val_xy))
if song_data.fixed_volume == False :
	ip_screen_composition.add_image(
		ComposableImage(helper.TextImage(device, volume_logo, font=awesomefont).image, 
		position=display.time_vol_icon_xy))
	play_screen_composition.add_image(
		ComposableImage(helper.TextImage(device, volume_logo, font=awesomefont).image, 
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
		elif ((int(time.time() * 1000) - lastrun_time) > 375) and  song_data.mode != "stop": 	
			get_metadata()
			lastrun_time = int(time.time() * 1000)
		# Update song data every 10 secs 
		elif ((int(time.time() * 1000) - lastrun_time) > 10000) :
			logger.debug("10 second update")
			get_metadata()
			lastrun_time = int(time.time() * 1000)
		
		info_title = song_data.title
		info_state = song_data.mode

		synchroniser = helper.Synchroniser()

		# One time update		
		if info_title_store != info_title or info_state_store != info_state:

			# Current file or state is different to last loop

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

			try:
				del scroll_play_line_1

			except:
				logger.debug("Removal Failed")
			ci_play_line_1 = ComposableImage(helper.TextImage(device, info_title, font=font_info).image, 
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

			bitrate_width, char = font_ip.getsize(song_data.sample_rate + song_data.sample_size + bitrate_val + " " + song_data.file_type)
			
			x_bitrate_pos = int((display.width - bitrate_width) / 2)
			if x_bitrate_pos < 0 :
				x_bitrate_pos = 0
			
			try:
				del scroll_play_line_2
			except:
				logger.debug("No bitrate to remove")

			ci_play_line_2 = ComposableImage(helper.TextImage(device, song_data.sample_size + song_data.sample_rate + bitrate_val + " " + song_data.file_type, font=font_ip).image, 
					position=(x_bitrate_pos, display.title_artist_line2_y + bitrate_line2_adjustment))
			
			scroll_play_line_2 = helper.Scroller(play_screen_composition, ci_play_line_2, 20, synchroniser, display.scroll_speed)

			# Song duration
			if info_duration != 0 :
				dura_min = info_duration/60
				dura_sec = info_duration%60
				dura_min = "%2d" %dura_min
				dura_sec = "%02d" %dura_sec
				dura_val = "/ " + str(dura_min)+":"+str(dura_sec)
			else : 
				dura_val = ""

		info_title_store = info_title
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
			
		
		# Volume change screen.  Only show if it's not fixed volume.
		if volume_val != vol_val_store : timer_vol = 20
		if timer_vol > 0 :
			with canvas(device) as draw:
				vol_width, char = font_vol.getsize(volume_val)
				x_vol = ((display.width - vol_width) / 2)
				# Volume Display
				draw.text(display.vol_screen_line1_xy, volume_logo, font=awesomefontbig, fill="white")
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

			if info_duration != 0 :
				time_bar = time_bar / info_duration * display.width

			if time_bar < 5 :
				current_page = 0

			# Switch over the lines after 150 cycles

			if current_page == 150 :
				#Swap to artist & album
				try:
					del scroll_play_line_1
					del scroll_play_line_2
				except:
					logger.debug("No Image to remove")

				ci_play_line_1 = ComposableImage(helper.TextImage(device, info_artist
					, font=font_info).image, 
					position=(0, display.title_artist_line1_y))
				
				ci_play_line_2 = ComposableImage(helper.TextImage(device, info_album
					, font=font_info).image, 
					position=(0, display.title_artist_line2_y))	

				scroll_play_line_1 = helper.Scroller(play_screen_composition, ci_play_line_1, 20, synchroniser, display.scroll_speed)
				scroll_play_line_2 = helper.Scroller(play_screen_composition, ci_play_line_2, 20, synchroniser, display.scroll_speed)

			if current_page == 300 :
				#Swap to title & bitrate
				try:
					del scroll_play_line_1
					del scroll_play_line_2
				except:
					logger.debug("No Image to remove")

				ci_play_line_1 = ComposableImage(helper.TextImage(device, info_title
					, font=font_info).image, 
					position=(0, display.title_artist_line1_y))
					
				ci_play_line_2 = ComposableImage(helper.TextImage(device, 
					song_data.sample_size + song_data.sample_rate + bitrate_val + " " + song_data.file_type, 
					font=font_ip).image, 
					position=(x_bitrate_pos, display.title_artist_line2_y) + bitrate_line2_adjustment)
								
				scroll_play_line_1 = helper.Scroller(play_screen_composition, ci_play_line_1, 20, synchroniser, display.scroll_speed)
				scroll_play_line_2 = helper.Scroller(play_screen_composition, ci_play_line_2, 20, synchroniser, display.scroll_speed)

				current_page = 0

			scroll_play_line_1.tick()
			scroll_play_line_2.tick()
			current_page += 1

			with canvas(device, background=play_screen_composition()) as draw:

				play_screen_composition.refresh()

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
					draw.text(display.title_line3_volume_val_xy, volume_val, font=font_time, fill="white")

			time.sleep(0.05)

		else:
			# Time IP screen
			if screen_sleep < 5000 :
				with canvas(device, background=ip_screen_composition()) as draw:

					ip_screen_composition.refresh()

					draw.text(display.time_xy,time.strftime("%X"), font=font_32,fill="white")
					if song_data.fixed_volume == False :
						draw.text(display.time_vol_val_xy, volume_val, font=font_time, fill="white")
				screen_sleep = screen_sleep + 1
			else :
				with canvas(device) as draw:
					if screen_sleep == 5000:
						# Start screensave on a random char
						screensave_char_index = int(helper.get_digit(time.time(),0))
						try:
							if int(display.height/screensave_char_index) <= display.height - screensave_height:
								screensave_xy = (screensave_xy[0],int(display.height/screensave_char_index))
							else:
								screensave_xy = (screensave_xy[0],int(display.height - screensave_height))
						except:
								screensave_xy = (screensave_xy[0],0)
						screen_sleep += 1
					screensave_xy = (screensave_xy[0]+2,screensave_xy[1])
					if screensave_xy[0] >= display.width -1 : 
						screensave_xy = (3,screensave_xy[1]+1)
						
					if screensave_xy[1] >= display.height - screensave_height :
						screensave_xy = (screensave_xy[0],0)

					draw.text(screensave_xy, screensave_chars[screensave_char_index], font=font_ip, fill="white")
					screensave_char_index += 1
					if screensave_char_index >= 8:
						screensave_char_index =0
				time.sleep(1)							
			time.sleep(0.1)
except Exception as e:
	exc_type, exc_obj, exc_tb = sys.exc_info()
	fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
	logger.critical((exc_type, fname, exc_tb.tb_lineno))

