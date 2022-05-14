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



import sys
import importlib
importlib.reload(sys)


import os
import time
import socket

import urllib.parse

try :
	import netifaces
except :
	print("Required modules are not available.")
	print("Please check if evosabre-py38-deps.tcz or evosabre-py38-64-deps.tcz extension is loaded.")
	exit("")

from PIL import Image
from PIL import ImageFont
from PIL import ImageDraw

from pylms.server import Server

from luma.core.interface.serial import spi
from luma.core.render import canvas
from luma.oled.device import ssd1322



serial = spi(port=0, device=0, gpio_DC=27, gpio_RST=24)
device = ssd1322(serial, rotate=0, mode="1")

mpd_music_dir		= "/var/lib/mpd/music/"
title_height		= 40
scroll_unit		= 2
oled_width		= 256
oled_height		= 64

def make_font(name, size):
    font_path = os.path.abspath(os.path.join(
        os.path.dirname(__file__), 'fonts', name))
    return ImageFont.truetype(font_path, size)

font_title		= make_font('msyh.ttf', 26)
font_info		= make_font('msyh.ttf', 20)
font_vol		= make_font('msyh.ttf', 55)
font_ip			= make_font('msyh.ttf', 15)
font_time		= make_font('msyh.ttf', 18)
font_20			= make_font('msyh.ttf', 18)
font_date		= make_font('arial.ttf', 25)
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

print ("Default Gateway Interface: " + default_gateway_interface)

if default_gateway_interface[0:2] == "wl" :
	print ("WiFi Network Detected")
	is_wifi = True
else :
	print ("Non WiFi WiFi Network Detected")
	is_wifi = False

def process_params(item):
	for params in sys.argv:
		key = params.split("=")[0]
		if key.upper() == item:
			return str(params.split("=")[1])
	return ""

def get_player_mac():
	if len(process_params("MAC")) > 1 :
		return process_params("MAC")
	else :
		mac = netifaces.ifaddresses(default_gateway_interface)[netifaces.AF_LINK][0]['addr']
		if mac != "":
			print ("Player MAC: " + mac)
			return mac
		else :
			print("MAC Discovery failed.  Using 00:11:22:33:44:55")
			return "00:11:22:33:44:55"

def get_player_ip():
	get_ip = netifaces.ifaddresses(default_gateway_interface)[netifaces.AF_INET][0]['addr']
	if get_ip == "":
		get_ip = "127.0.0.1"
	print ("Player IP: "+ get_ip)
	return get_ip

def get_lms_ip():
	if len(process_params("LMSIP")) > 1 :
		lms_ip = process_params("LMSIP")
	else :
		#Discover the LMS IP Address
		print("Discovering LMS IP")
		sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
		sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)

		try:
			sock.bind((player_ip,3483))
		except (socket.error, socket.timeout):
			print ("	Local LMS Detected")
			lms_ip = "127.0.0.1"
			print ("	LMS IP: " + lms_ip)
			lms_name = ""
		else:
			try:
				sock.settimeout(2.0)
				sock.sendto(b"eNAME\0", ('255.255.255.255', 3483))
				data, addr = sock.recvfrom(1024) # buffer size is 1024 bytes

			except (socket.error, socket.timeout):
				print ("	Discovery Failure.  Assuming Local LMS")
				lms_ip = "127.0.0.1"
				print ("	LMS IP: " + lms_ip)
				lms_name = ""
			else:
				#print ("	Broadcast Response: ", data)
				lms_name = data.decode('UTF-8')[len("eName")+1:]
				lms_ip = str(addr[0])
				print ("	Discovered Server: ", lms_name)
				print ("	Discovered Server IP: ",lms_ip)
			finally:
				sock.close()

	return lms_ip,lms_name
	
def get_song_info():
	while True:
		try:
			status = player_handle.request("status - 1 tags:galdIrTNo",1)
		except:
			server_connect()
		else:
			break
		
	results = status.split(" ")
	idx = 0
	for values in results:
		results[idx] = urllib.parse.unquote(values)
		idx = idx+1
	return results

def get_song_item(item):
    for values in song_info:
        key = values.split(":")[0]
        if key == item:
            return values.split(":")[1]
    return ""

def get_fixed_volume():
	output = get_song_item("digital_volume_control")
	if output == "0" :
		return True
	else :
		return False	

def get_file_type():
	output = get_song_item("type") 
	if output != "" :
		return output
	else :
		return ""


def get_sample_size():
	output = get_song_item("samplesize") 
	if output == "16" :
		return "16 Bit / "
	elif output == "24" :
		return "24 Bit / "
	elif output == "32" :
		return "32 Bit / "
	else :
		return output

def get_sample_rate():
	output = get_song_item("samplerate") 
	if output != "" :
		return str(float(output)/1000)+"k"
	else :
		return output

def get_bitrate():
	output = get_song_item("bitrate") 

	if output != "" :
		return str(output)
	else :
		return ""

def get_duration():
	output = get_song_item("duration") 
	if output != "" :
		output = float(output)
		return output
	else :
		return 0

def get_elapsed_time():
	output = get_song_item("time") 
	if output != "" :
		output = float(output)
		return output
	else :
		return 0


def get_volume():
	output = get_song_item("mixer volume") 
	if output != "" :
		output = str(output)
	return output

# PyLms Connection

def server_connect():
	while True :
		try :

			global player_ip 
			player_ip = get_player_ip()

			lms_ip, lms_name = get_lms_ip()
			player_mac = str(get_player_mac())
			
			with canvas(device) as draw:
				draw.text((15, 0),"Connecting to LMS", font=font_time,fill="white")
				if len(lms_name) > 0 :
					draw.text((20, 17),"LMS Name: " + lms_name, font=font_time,fill="white")
				draw.text((20, 34),"LMS IP:  " + lms_ip, font=font_time,fill="white")
			time.sleep(1)
			server_handle = Server(hostname=lms_ip, port=9090, username="user", password="password", charset='utf8')
			server_handle.connect()
			print("LMS Version: %s" % server_handle.get_version())

			global player_handle
			player_handle = server_handle.get_player(player_mac)
			print("Player Name: %s" % player_handle.get_name())
			
		
		except Exception as e:
			print("Player " + player_mac + " not connected to LMS : " + lms_ip)

			with canvas(device) as draw:
#debug
#				draw.text((5, 20),"E :" + str(e), font=font_debug,fill="white")
				draw.text((15, 0),"Player Not Connected", font=font_time,fill="white")
				draw.text((20, 17),"MAC: " + player_mac, font=font_time,fill="white")
				draw.text((20, 34),"LMS: " + lms_ip, font=font_time,fill="white")
			time.sleep(1)
		else :
			break


# OLED images
image		= Image.new('1', (oled_width, oled_height))
draw		= ImageDraw.Draw(image)
music_file	=""
shift		= 0
title_image     = Image.new('L', (oled_width, title_height))
title_offset    = 0
current_page = 0
vol_val_store = 0
screen_sleep = 0
timer_vol = 0
screensave = 3


shift		= 1

with canvas(device) as draw:
	draw.text((6, 0),"Audiophonics", font=font_logo,fill="white")
time.sleep(2)

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

print("Player State: %s" % player_handle.get_mode())


try:
	while True:
		# Get the current song info
		global song_info
		song_info = get_song_info()

		info_file = get_song_item("title") #sq.request("title ?",1)
		info_state = get_song_item("mode") #sq.get_mode()

# One time update		
		if info_file_store != info_file or info_state_store != info_state:
			timer_rates = 10
			info_artist     = get_song_item("artist")
			if info_artist == "" :
				info_artist     = "No Artist"
			info_album      = get_song_item("album")
			# If there's no Album, is it an internet radio stream
			remote_title = get_song_item("album")
			if info_album == "" :
				# If there's no Album, is it an internet radio stream
				remote_title = get_song_item("remote_title")
				if remote_title != "" :
					info_album = remote_title
				else :
					info_album     = "No Album"

			info_title      = get_song_item("title")
			#info_name      = 
			try :
				info_duration   = get_duration() #sq.get_track_duration()
			except :
				info_duration   = 0
		if timer_rates > 0 :
			info_state = get_song_item("mode") #sq.get_mode()
			sample_size_val = str(get_sample_size())
			sample_rate_val = str(get_sample_rate())
			filetype_val = str(get_file_type())
			if sample_rate_val == "176.4k" :
				sample_rate_val = "DSD64"
			elif sample_rate_val == "352.8k" :
				sample_rate_val = "DSD128"
			elif sample_rate_val == "705.6k" :
				sample_rate_val = "DSD256"
			
			if sample_rate_val != "" :
				bitrate_val = " / " + str(get_bitrate())
			else :
				bitrate_val = str(get_bitrate())
			timer_rates -= 1

		info_file_store = info_title
		info_state_store = info_state
		
# Continuous update			
		try :
			time_val = get_elapsed_time()
			time_bar = time_val
			time_min = time_val/60
			time_sec = time_val%60
			time_min = "%2d" %time_min
			time_sec = "%02d" %time_sec
			time_val = str(time_min)+":"+str(time_sec)
		except :
			time_val = 0

		if get_fixed_volume() == False :
			volume_val = get_volume()
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
				x_vol = ((oled_width - vol_width) / 2)
				# Volume Display
				draw.text((5, 5), text="\uf028", font=awesomefontbig, fill="white")
				draw.text((x_vol, -15), volume_val, font=font_vol, fill="white")
				# Volume Bar
				draw.rectangle((0,53,255,60), outline=1, fill=0)
				Volume_bar = ((int(float(volume_val)) * 2.52)+2)
				draw.rectangle((2,55,Volume_bar,58), outline=0, fill=1)
			vol_val_store = volume_val
			timer_vol = timer_vol - 1
			screen_sleep = 0
			time.sleep(0.1)	
			
		# Play screen
		elif info_state != "stop":
			if info_title == "" :
				name    = info_file.split('/')
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
				time_bar = time_bar / info_duration * 256

			if info_file != music_file or time_bar < 5 :
				#Called one time / file
				music_file  = info_file;
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
				
				artist_offset    = 10;
				album_offset    = 10;
				title_offset     = 10;
				title_width, char  = font_info.getsize(info_title)
				artist_width, char  = font_info.getsize(info_artist)
				album_width, char  = font_info.getsize(info_album)
				bitrate_width, char = font_ip.getsize(sample_rate_val + sample_size_val + bitrate_val + " " + filetype_val)

				current_page = 0

			# OFFSETS*****************************************************
			x_artist   = 0
			if oled_width < artist_width :
				if artist_width < -(artist_offset + 20) :
					artist_offset    = 0
				if artist_offset < 0 :
					x_artist   = artist_offset
				artist_offset    = artist_offset - scroll_unit

			x_album   = 0
			if oled_width < album_width :
				if album_width < -(album_offset + 20) :
					album_offset    = 0
				if album_offset < 0 :
					x_album   = album_offset
				album_offset    = album_offset - scroll_unit	

			x_title   = 0
			if oled_width < title_width :
				if title_width < -(title_offset + 20) :
					title_offset    = 0
				if title_offset < 0 :
					x_title   = title_offset
				title_offset    = title_offset - scroll_unit	

			x_bitrate = (oled_width - bitrate_width) / 2

			if x_bitrate < 0 :
				x_bitrate = 0
						
			with canvas(device) as draw:
				if current_page < 150 :	
					draw.text((x_title, -7), info_title, font=font_info, fill="white")
					if title_width < -(title_offset - oled_width) and title_width > oled_width :
						draw.text((x_title + title_width + 10,-7), "- " + info_title, font=font_info, fill="white")					
					draw.text((x_bitrate, 20), (sample_size_val + sample_rate_val + bitrate_val + " " + filetype_val), font=font_ip, fill="white")					
					if info_state == "pause": 
						draw.text((0, 43), text="\uf04c", font=awesomefont, fill="white")
					else:
						draw.text((0, 41), time_val, font=font_time, fill="white")
						draw.text((55, 41), dura_val, font=font_time, fill="white")
					#draw.text((58, 48), text="\uf001", font=awesomefont, fill="white")	
					draw.rectangle((0,40,time_bar,44), outline=0, fill=1)

					if get_fixed_volume() == False :
						draw.text((200, 44), text="\uf028", font=awesomefont, fill="white")	
						draw.text((220, 41), volume_val, font=font_time, fill="white")
				
					current_page = current_page + 1
					artist_offset = 10
					album_offset = 10						
		
				elif current_page < 300	:
					# artist name
					draw.text((x_artist,-7), info_artist, font=font_info, fill="white")
					if artist_width < -(artist_offset - oled_width) and artist_width > oled_width :
						draw.text((x_artist + artist_width + 10,-7), "- " + info_artist, font=font_info, fill="white")
					# album name
					draw.text((x_album, 14), info_album, font=font_info, fill="white")
					if album_width < -(album_offset - oled_width) and album_width > oled_width :
						draw.text((x_album + album_width + 10,14), "- " + info_album, font=font_info, fill="white")
					# Bottom line
					if info_state == "pause": 
						draw.text((0, 43), text="\uf04c", font=awesomefont, fill="white")
					else:
						draw.text((0, 41), time_val, font=font_time, fill="white")
						draw.text((55, 41), dura_val, font=font_time, fill="white")
					draw.rectangle((0,40,time_bar,44), outline=0, fill=1)

					if get_fixed_volume() == False :
						draw.text((200, 44), text="\uf028", font=awesomefont, fill="white")
						draw.text((220, 41), volume_val, font=font_time, fill="white")
					current_page = current_page + 1
					
					if current_page == 300 :
						current_page = 0
						title_offset = 10

			time.sleep(0.05)

		else:
			# Time IP screen
			if screen_sleep < 20000 :
				with canvas(device) as draw:
					if is_wifi == False :
						# Wifi IP Address
						draw.text((140, 45), player_ip, font=font_ip, fill="white")
						draw.text((120, 45), link, font=awesomefont, fill="white")
					else:
						# LAN IP Address
						draw.text((140, 45), player_ip, font=font_ip, fill="white")
						draw.text((120, 45), wifi, font=awesomefont, fill="white")

					draw.text((28,-10),time.strftime("%X"), font=font_32,fill="white")
					if get_fixed_volume() == False :
						draw.text((20, 40), volume_val, font=font_time, fill="white")
						draw.text((1, 43), text="\uf028", font=awesomefont, fill="white")
				screen_sleep = screen_sleep + 1
			else :
				with canvas(device) as draw:
					screensave += 2
					if screensave > 120 : 
						screensave = 3
					draw.text((screensave, 45), ".", font=font_time, fill="white")
				time.sleep(1)							
			time.sleep(0.1)
except Exception as e:
    exc_type, exc_obj, exc_tb = sys.exc_info()
    fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
    print((exc_type, fname, exc_tb.tb_lineno))

