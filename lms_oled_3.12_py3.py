#!/usr/bin/env python
# -*- coding: utf-8 -*-
# AUDIOPHONICS RASPDAC MINI LMS OLED Script #
# 11 Decembre 2018 
from __future__ import unicode_literals
import sys
reload(sys)
sys.setdefaultencoding('utf-8')

import os
import time
import socket
#import smbus
#bus = smbus.SMBus(1)
import re
import subprocess
#import json
import urllib2
from subprocess import Popen, PIPE

from PIL import Image
from PIL import ImageFont
from PIL import ImageDraw

from pylms.server import Server
from pylms.player import Player

from luma.core.interface.serial import spi
from luma.core.render import canvas
from luma.oled.device import ssd1322
#import RPi.GPIO as GPIO
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

font_title              = make_font('msyh.ttf', 26)
font_info		= make_font('msyh.ttf', 20)
font_vol		= make_font('msyh.ttf', 55)
font_ip			= make_font('msyh.ttf', 15)
font_time		= make_font('msyh.ttf', 18)
font_20			= make_font('msyh.ttf', 18)
font_date		= make_font('arial.ttf', 25)
#font_logo		= make_font('msyh.ttf', 24)
font_logo		= make_font('arial.ttf', 42)
font_32			= make_font('arial.ttf', 50)
awesomefont		= make_font("fontawesome-webfont.ttf", 16)
awesomefontbig		= make_font("fontawesome-webfont.ttf", 42)

speaker			= "\uf028"
wifi			= "\uf1eb"
link			= "\uf0e8"
clock			= "\uf017"

# PyLms Connection
while True :
	try :
		with canvas(device) as draw:
			draw.text((27, 0),"Try to connect", font=font_time,fill="white")
			draw.text((25, 34),"to LMS", font=font_time,fill="white")
		time.sleep(1)
		sc = Server(hostname="192.168.3.20", port=9090, username="user", password="password", charset='utf8')
		sc.connect()
		print "Version: %s" % sc.get_version()
		print "Try connect player"
		sq = sc.get_player("00:11:22:33:44:55")
		print sq.get_name()
		
	except : 
		print("No player connected to LMS")
		with canvas(device) as draw:
			draw.text((15, 0),"Player not connected", font=font_time,fill="white")
			draw.text((25, 34),"to LMS", font=font_time,fill="white")
		time.sleep(2)
	else :
		break

print sq.get_mode()

def getWanIP():
    #can be any routable address,
    fakeDest = ("223.5.5.5", 53)
    wanIP = ""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(fakeDest)
        wanIP = s.getsockname()[0]
        s.close()
    except Exception, e:
        pass
    return wanIP

def GetLANIP():
   cmd = "ip addr show eth0 | grep inet  | grep -v inet6 | awk '{print $2}' | cut -d '/' -f 1"
   p = Popen(cmd, shell=True, stdout=PIPE)
   output = p.communicate()[0]
   return output[:-1]
   
def GetInput():
	cmd = "amixer sget -c 0 'I2S/SPDIF Select' | grep Item0: | awk '{print $2}' "
	p = Popen(cmd, shell=True, stdout=PIPE)
	output = p.communicate()[0]
	return output[:-1]

def GetBitrate():
	cmd = "cat /proc/asound/card0/pcm0p/sub0/hw_params | awk '{print $2}' | sed -n 2p | cut -d '_' -f 1"
	p = Popen(cmd, shell=True, stdout=PIPE)
	output = p.communicate()[0]
	output = output[:-1]
	if output == "S16" :
		return "16 Bit / "
	elif output == "S24" :
		return "24 Bit / "
	elif output == "S32" :
		return "32 Bit / "
	else :
		return output

def GetSamplerate():
	cmd = "cat /proc/asound/card0/pcm0p/sub0/hw_params | awk '{print $2}' | sed -n 5p"
	p = Popen(cmd, shell=True, stdout=PIPE)
	output = p.communicate()[0]
	output = output[:-1]
	if output != "" :
		output = str(float(output)/1000)+"k"
		return output

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

# GPIO.setmode(GPIO.BCM)
# GPIO.setwarnings(False)
# GPIO.setup(22, GPIO.IN,pull_up_down=GPIO.PUD_UP)
# spdif=False;

# def InputSelect():
    # global spdif
    # if(spdif==False):
	# spdif=True
	# os.system("amixer sset -c 1 'I2S/SPDIF Select' SPDIF")
    # elif(spdif==True):
	# spdif=False
	# os.system("amixer sset -c 1 'I2S/SPDIF Select' I2S")


# def optionButPress(value):
    # global startt,endt
    # if GPIO.input(22) == 1:
        # startt = time.time()
    # if GPIO.input(22) == 0:
        # endt = time.time()
	# InputSelect()

#GPIO.add_event_detect(22, GPIO.BOTH, callback=optionButPress, bouncetime=200)
#os.system("amixer sset -c 1 'I2S/SPDIF Select' I2S")

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
time_val = time_min = time_sec = vol_val =  0
vol_val = 0

timer_rates = 10
timer_input = 10
bit_val = ""
samp_val = ""

try:
	while True:

		info_file = sq.request("title ?",1)
		info_state = sq.get_mode()

# One time update		
		if info_file_store != info_file or info_state_store != info_state:
			timer_rates = 10
			info_artist     = urllib2.unquote(sq.request("artist ?",1).encode('utf-8'))+""
			if info_artist == "" :
				info_artist     = "No Artist"
			info_album      = urllib2.unquote(sq.request("album ?",1).encode('utf-8'))+""
			if info_album == "" :
				info_album     = "No Album"
			info_title      = urllib2.unquote(sq.request("title ?",1).encode('utf-8'))+""
			#info_name      = 
			try :
				info_duration   = sq.get_track_duration()
			except :
				info_duration   = 0
		if timer_rates > 0 :
			info_state = sq.get_mode()
			bit_val = "" #str(GetBitrate()) Tjs 32 sous LMS
			samp_val = str(GetSamplerate())
			if samp_val == "176.4k" :
				samp_val = "DSD64"
			elif samp_val == "352.8k" :
				samp_val = "DSD128"
			elif samp_val == "705.6k" :
				samp_val = "DSD256"
			timer_rates -= 1

		info_file_store = info_title
		info_state_store = info_state
		
# Continuous update			
		try :
			time_val = sq.get_time_elapsed()
			time_bar = time_val
			time_min = time_val/60
			time_sec = time_val%60
			time_min = "%2d" %time_min
			time_sec = "%02d" %time_sec
			time_val = str(time_min)+":"+str(time_sec)
		except :
			time_val = 0

		vol_val = str(sq.get_volume())
		
		timer_input -= 1
		if timer_input == 0 :
			dac_input = str(GetInput())
			timer_input = 10
		
		
		# Volume change screen
		if vol_val != vol_val_store : timer_vol = 20
		if timer_vol > 0 :
			with canvas(device) as draw:
				vol_width, char = font_vol.getsize(vol_val)
				x_vol = ((oled_width - vol_width) / 2)
				# Volume Display
				draw.text((5, 5), text="\uf028", font=awesomefontbig, fill="white")
				draw.text((x_vol, -15), vol_val, font=font_vol, fill="white")
				# Volume Bar
				draw.rectangle((0,53,255,60), outline=1, fill=0)
				Volume_bar = ((int(float(vol_val)) * 2.52)+2)
				draw.rectangle((2,55,Volume_bar,58), outline=0, fill=1)
			vol_val_store = vol_val
			timer_vol = timer_vol - 1
			screen_sleep = 0
			time.sleep(0.1)
	

		# SPDIF screen
		elif(dac_input == "'SPDIF'"):
			if screen_sleep < 600 :
				with canvas(device) as draw:
					draw.text((20, -4),"SPDIF", font=font_title,fill="white")
					draw.text((45, 33), vol_val, font=font_title, fill="white")
					draw.text((15, 41), text="\uf028", font=awesomefont, fill="white")
					# Volume Bar
					draw.rectangle((120,0,127,62), outline=1, fill=0)
					Volume_bar = (58 - (int(float(vol_val)) / 1.785))
					draw.rectangle((122,Volume_bar,125,60), outline=0, fill=1)				
				time.sleep(0.5)	
				screen_sleep = screen_sleep + 1
			else : 
				with canvas(device) as draw:
					screensave += 2
					if screensave > 120 : 
						screensave = 3
					draw.text((screensave, 45), ".", font=font_time, fill="white")
				time.sleep(1)
			
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
				bit_val = bytes(bit_val)	#2018.1.5
				samp_val = bytes(samp_val)	#2018.1.7				
				artist_offset    = 10;
				album_offset    = 10;
				title_offset     = 10;
				title_width, char  = font_info.getsize(info_title)
				artist_width, char  = font_info.getsize(info_artist)
				album_width, char  = font_info.getsize(info_album)
				bitrate_width, char = font_time.getsize(samp_val + bit_val)
				
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


			with canvas(device) as draw:
				if current_page < 150 :	
					draw.text((x_title, -7), info_title, font=font_info, fill="white")
					if title_width < -(title_offset - oled_width) and title_width > oled_width :
						draw.text((x_title + title_width + 10,-7), "- " + info_title, font=font_info, fill="white")					
					draw.text((x_bitrate, 20), (bit_val + samp_val), font=font_ip, fill="white")					
					if info_state == "pause": 
						draw.text((0, 43), text="\uf04c", font=awesomefont, fill="white")
					else:
						draw.text((0, 41), time_val, font=font_time, fill="white")
						draw.text((55, 41), dura_val, font=font_time, fill="white")
					#draw.text((58, 48), text="\uf001", font=awesomefont, fill="white")	
					draw.rectangle((0,40,time_bar,44), outline=0, fill=1)
					draw.text((200, 44), text="\uf028", font=awesomefont, fill="white")	
					draw.text((220, 41), vol_val, font=font_time, fill="white")
				
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
					draw.text((200, 44), text="\uf028", font=awesomefont, fill="white")
					draw.text((220, 41), vol_val, font=font_time, fill="white")
					current_page = current_page + 1
					
					if current_page == 300 :
						current_page = 0
						title_offset = 10

			time.sleep(0.05)

		else:
			# Time IP screen
			#ip = getWanIP()
			ip = str(GetLANIP())
			if screen_sleep < 20000 :
				with canvas(device) as draw:
					if ip != "":
						draw.text((140, 45), ip, font=font_ip, fill="white")
						draw.text((120, 45), link, font=awesomefont, fill="white")
					else:
						draw.text((140, 45),time.strftime("No LAN IP"), font=font_ip, fill="white")
						draw.text((120, 45), wifi, font=awesomefont, fill="white")

					draw.text((28,-10),time.strftime("%X"), font=font_32,fill="white")
					draw.text((20, 40), vol_val, font=font_time, fill="white")
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
    print(exc_type, fname, exc_tb.tb_lineno)



