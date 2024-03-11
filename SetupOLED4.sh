
echo ""
echo "Setup for OLED for PCP on Raspberry Pi"
echo ""

mkdir ~/.oled4pcp 2>>/dev/null
wget -q https://raw.githubusercontent.com/peteS-UK/EvoSabre-DAC-PCP/main/home/oled4pcp.cfg -P ~/.oled4pcp  2>>/dev/null


echo "What OLED device are you configuring?  Currently defined sections in oled4pcp.cfg are:"$'\n'

while read line; do
	echo $line | grep -q "\["
        if [ $? -eq 0  ]; then
            if [ $line != "[CONFIG]" ]; then
        	    echo $line  | sed 's/[[]//g' | sed 's/[]]//g'
            fi
        fi
done < ~/.oled4pcp/oled4pcp.cfg

echo $'\n'  

while true; do
    read -p "Please choose your oled, or enter a new name if you want to create a new section : " oleddevice
    if [ ${#oleddevice} = 0 ]; then
        echo "Please enter your device"
    else
        break
    fi
done

#Check if oled.cfg contains a section heading for the oled device
while read line; do
	echo $line | grep -q $oleddevice
        if [ $? -eq 0 ]; then
        	section=$(echo $line)
        fi
done < ~/.oled4pcp/oled4pcp.cfg



if [ ${#section} = 0 ]; then
    echo $'\n'"oled4pcp.cfg file contains no section for $oleddevice"
    echo "Please edit oled4pcp.cfg to define your oled device, and backup and reboot after changes."
else
    LINENO=0
    # find the existing section heading
    while read line; do
        echo $line | grep -q $oleddevice
            if [ $? -eq 0 ]; then
                SECTIONLINE=$LINENO
            fi
        LINENO=$(( LINENO + 1 ))
    done < ~/.oled4pcp/oled4pcp.cfg

    # strip the lines before this section
    sed '1,'$SECTIONLINE'd' ~/.oled4pcp/oled4pcp.cfg > ~/tmp

    # find the serial_interface for the section
    while read line; do
        echo $line | grep -q "serial_interface"
            if [ $? -eq 0  ]; then
                si=$(echo $line | tr [:lower:] [:upper:] | awk -F'SERIAL_INTERFACE=' '{print $2}') 
                break
            fi
    done < ~/tmp
fi


# Update oled4pcp.cfg with new oled section name
while read line; do
    echo $line | grep -q oled_section
        if [ $? -eq 0 ]; then
  	        OS=$(echo $line)
            break
        fi
done < ~/.oled4pcp/oled4pcp.cfg

sed -i "s/$OS/oled_section=$oleddevice/" ~/.oled4pcp/oled4pcp.cfg

if [ "$si" == "" ]; then

    while true; do
        echo $'\n'
        read -p "Is the OLED interface SPI (SPI) or I2C (I2C)?" si
        case $si in
            [SPI]* ) break;;
            [I2C]* ) break;;
            * ) echo "Please answer SPI or I2C";;
        esac
    done

    echo "You must also check the ""serial_interface"" entry in the $oleddevice section of oled4pcp.cfg matches this"

fi

echo $'\n'

echo "Installing python3 and freetype extension"
tce-load -iw python3.8 freetype 1>>/dev/null 2>>/dev/null

echo $'\n'

if [ "$(uname -m)" = "aarch64" ]; then
    echo "Installing 64 bit extension"
    tczname="oled4pcp_4-py38-64-deps.tcz"

else
    echo "Installing 32 bit extension"
    tczname="oled4pcp_4-py38-deps.tcz"
fi

sudo wget -q https://raw.githubusercontent.com/peteS-UK/EvoSabre-DAC-PCP/main/tcz/$tczname -O /etc/sysconfig/tcedir/optional/$tczname

#Check if extension is set already
while read line; do
    echo $line | grep -q $tczname
        if [ $? -eq 0 ]; then
  	        EXTENSION="INSTALLED"
            break
        fi
done < /etc/sysconfig/tcedir/onboot.lst

if [ "$EXTENSION" != "INSTALLED" ]; then
    echo "$tczname" | sudo tee -a /etc/sysconfig/tcedir/onboot.lst 1>>/dev/null
fi

mkdir ~/.oled4pcp/fonts 2>>/dev/null

echo "Moving Files to home/.oled4pcp"
wget -q https://raw.githubusercontent.com/peteS-UK/EvoSabre-DAC-PCP/main/home/oled4pcp_4.py -P ~/.oled4pcp -O oled4pcp_4.py
wget -q https://raw.githubusercontent.com/peteS-UK/EvoSabre-DAC-PCP/main/home/helper.py -P ~/.oled4pcp -O helper.py
wget -q https://raw.githubusercontent.com/peteS-UK/EvoSabre-DAC-PCP/main/home/audiophonics_logo_256_64.bmp -P ~/.oled4pcp -O audiophonics_logo_256_64.bmp
wget -q https://raw.githubusercontent.com/peteS-UK/EvoSabre-DAC-PCP/main/home/pcp_logo_256_64.bmp -P ~/.oled4pcp -O pcp_logo_256_64.bmp
wget -q https://raw.githubusercontent.com/peteS-UK/EvoSabre-DAC-PCP/main/home/audiophonics_logo_128_64.bmp -P ~/.oled4pcp -O audiophonics_logo_128_64.bmp
wget -q https://raw.githubusercontent.com/peteS-UK/EvoSabre-DAC-PCP/main/home/pcp_logo_128_64.bmp -P ~/.oled4pcp -O pcp_logo_128_64.bmp
wget -q https://raw.githubusercontent.com/peteS-UK/EvoSabre-DAC-PCP/main/home/fonts/arial.ttf -P ~/.oled4pcp/fonts -O arial.ttf
wget -q https://raw.githubusercontent.com/peteS-UK/EvoSabre-DAC-PCP/main/home/fonts/fontawesome-webfont.ttf -P ~/.oled4pcp/fonts -O fontawesome-webfont.ttf


#Check if USER_COMMAND_1 is set already
while read line; do
    echo $line | grep -q USER_COMMAND_1
        if [ $? -eq 0 ]; then
  	        UC1=$(echo $line)
            break
        fi
done < /usr/local/etc/pcp/pcp.cfg

UC_LINE=$(echo $UC1 | awk -F'USER_COMMAND_1=' '{print $2}' | sed 's/"//g')

if [ "$UC_LINE" == "" ]; then
    # Command line is blank, so update it
    echo $'\n'
    echo "Updating User Command"
    $(sed -i "s/USER_COMMAND_1=\"\"/USER_COMMAND_1=\"python3+%2Fhome%2Ftc%2F.oled4pcp%2Foled4pcp_4.py\"/" /usr/local/etc/pcp/pcp.cfg)
else
    echo $'\n'
    echo "User Command 1 in PCP tweaks isn't blank.  Please modify to run the extension"
fi

if [ $si == "SPI" ]; then

    # SPI device.  No setup needed for I2C as it's already enabled in PCP

    while true; do
        echo $'\n'
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
echo "After install, please check or create the section in oled4pcp.cfg to match your oled"
echo "Make sure you backup any changes to the .cfg using ""pcp bu"" or through the UI"