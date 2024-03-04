
echo ""
echo "Setup for OLED for PCP on Raspberry Pi"
echo ""

while true; do
    read -p "What OLED device are you configuring (e.g. SSD1322 for EvoSabre, SSD1306 for Mini) : " oleddevice
    if [ ${#oleddevice} = 0 ]; then
        echo "Please enter your device"
    else
        break
    fi
done

echo "Installing python3 and freetype extension"
tce-load -iw python3.8 freetype 1>>/dev/null 2>>/dev/null

if [ "$(uname -m)" = "aarch64" ]; then
    echo "Installing 64 bit extension"
    tczname="oled4pcp_4-py38-64-deps.tcz"

else
    echo "Installing 32 bit extension"
    tczname="oled4pcp_4-py38-deps.tcz"
fi

sudo wget -q https://raw.githubusercontent.com/peteS-UK/EvoSabre-DAC-PCP/main/tcz/$tczname -O /etc/sysconfig/tcedir/optional/$tczname

echo "$tczname" | sudo tee -a /etc/sysconfig/tcedir/onboot.lst 1>>/dev/null

mkdir ~/fonts 2>>/dev/null

echo "Moving Files to home"
wget -q https://raw.githubusercontent.com/peteS-UK/EvoSabre-DAC-PCP/main/home/oled4pcp_4.py -P ~
wget -q https://raw.githubusercontent.com/peteS-UK/EvoSabre-DAC-PCP/main/home/helper.py -P ~
wget -q https://raw.githubusercontent.com/peteS-UK/EvoSabre-DAC-PCP/main/home/oled4pcp.cfg -P ~
wget -q https://raw.githubusercontent.com/peteS-UK/EvoSabre-DAC-PCP/main/home/logo_256_64.bmp -P ~
wget -q https://raw.githubusercontent.com/peteS-UK/EvoSabre-DAC-PCP/main/home/logo_128_64.bmp -P ~
wget -q https://raw.githubusercontent.com/peteS-UK/EvoSabre-DAC-PCP/main/home/fonts/arial.ttf -P ~/fonts
wget -q https://raw.githubusercontent.com/peteS-UK/EvoSabre-DAC-PCP/main/home/fonts/fontawesome-webfont.ttf -P ~/fonts
#wget -q https://raw.githubusercontent.com/peteS-UK/EvoSabre-DAC-PCP/main/home/fonts/msyh.ttf -P ~/fonts


#Check if oled.cfg contains a section heading for the oled device
while read line; do
	echo $line | grep -q $oleddevice
        if [ $? -eq 0 ]; then
        	section=$(echo $line)
        fi
done < ~/oled4pcp.cfg

if [ ${#section} = 0 ]; then
    echo "oled4pcp.cfg file contains no section for $oleddevice"
    echo "Please edit oled4pcp.cfg to define your oled device, and backup and reboot after changes."
fi

#Check if USER_COMMAND_1 is set already
while read line; do
    echo $line | grep -q USER_COMMAND_1
        if [ $? -eq 0 ]; then
  	        UC1=$(echo $line)
        fi
done < /usr/local/etc/pcp/pcp.cfg

UC_LINE=$(echo $UC1 | awk -F'USER_COMMAND_1=' '{print $2}' | sed 's/"//g')

if [ "$UC_LINE" == "" ]; then
    # Command line is blank, so update it
    echo "Updating User Command"
    $(sed -i "s/USER_COMMAND_1=\"\"/USER_COMMAND_1=\"python3+%2Fhome%2Ftc%2Foled4pcp_4.py+OLED%3D$oleddevice\"/" /usr/local/etc/pcp/pcp.cfg)
fi

while true; do
    read -p "Is OLED interface SPI (S) or I2C (I)?" si
    case $si in
        [S]* ) break;;
        [I]* ) break;;
        * ) echo "Please answer S or I";;
    esac
done

if [ $si == "S" ]; then

    # SPI device.  No setup needed for I2C as it's already enabled in PCP

    while true; do
        read -p "Enlarge SPI Buffer to display logo bitmap on startup?" yn
        case $yn in
            [Y]* ) break;;
            [N]* ) break;;
            * ) echo "Please answer Y or N";;
        esac
    done

    mount /mnt/mmcblk0p1

    if [ $yn == "Y" ]; then

        read line < /mnt/mmcblk0p1/cmdline.txt
        newline=$line" spidev.bufsiz=8192"
        echo -n $newline > /mnt/mmcblk0p1/cmdline.txt
    fi

    # Does config.txt already contain spi
    while read line; do
        cleanline=$(echo $line  | sed 's/[[:space:]]*//g')
        echo $cleanline | grep -q spi=
            if [ $? -eq 0 ]; then
                echo $cleanline | grep -q dtparam
                if [ $? -eq 0 ]; then
                    spi=$(echo $line)
                fi
            fi
    done < /mnt/mmcblk0p1/config.txt

    if [ "$spi" == "" ]; then
    # no entry for SPI, so add one
        echo "Adding dtparam=spi=on to config.txt" 
        mv /mnt/mmcblk0p1/config.txt /mnt/mmcblk0p1/config.sav
        awk '/#---Begin-Custom-/ { print; print "dtparam=spi=on"; next }1' /mnt/mmcblk0p1/config.sav >> /mnt/mmcblk0p1/config.txt
    fi

    umount /mnt/mmcblk0p1

fi

echo "Backing up PCP"
pcp bu  1>>/dev/null

echo "Extension Installed.  Now reboot using ""pcp rb"""
