
echo ""
echo "Setup for OLED with LMS on Raspberry Pi"
echo ""

#while true; do
#    read -p "Are you setting up EvoSabre or RASPDac Mini?" er
#    case $er in
#        [E]* ) echo "Setup for EvoSabre OLED extension (E)"; dac="E";break;;
#        [R]* ) echo "Setup for RASPDac Mini OLED extension (R)"; dac="R";break;;
#        * ) echo "Please answer E or R";;
#    esac
#done

while true; do
    read -p "What OLED device are you configuring (e.g. SSD1322 for EvoSabre, SSD1306 for Mini) : " oleddevice
    if [ ${#oleddevice} = 0 ]; then
        echo "Please enter your device"
    else
        break
    fi
done

echo $oleddevice

exit


tmp=$(mktemp)
tmpdir=$(mktemp -d)

echo "Installing python3 and freetype extension"
tce-load -iw python3.8 freetype 1>>/dev/null 2>>/dev/null

echo "Downloading Extension from GitHub"
wget -q https://github.com/peteS-UK/EvoSabre-DAC-PCP/releases/download/EvoSabreOLED/evosabre.tar.gz -O $tmp

echo "Unpacking Files"
tar -xzf $tmp -C $tmpdir

rm $tmp

echo "Moving Files to home"

#if [ $dac == "E" ]; then
#    mv -f $tmpdir/evosabre/home/lms_oled_4.py ~
#else
#    mv -f $tmpdir/evosabre/home/lms_oled_mini_4.py ~
#fi

mv -f $tmpdir/evosabre/home/logo.bmp ~

mkdir ~/fonts 2>>/dev/null
mv -f $tmpdir/evosabre/home/fonts/* ~/fonts


if [ "$(uname -m)" = "aarch64" ]; then
    echo "Installing 64 bit extension"
    tczname="evosabre4-py38-64-deps.tcz"
else
    echo "Installing 32 bit extension"
    tczname="evosabre4-py38-deps.tcz"
fi

sudo cp -p "$tmpdir/evosabre/$tczname" /etc/sysconfig/tcedir/optional 1>>/dev/null
echo "$tczname" | sudo tee -a /etc/sysconfig/tcedir/onboot.lst 1>>/dev/null

rm -rf $tmpdir

#Check if USER_COMMAND_1 is set already
while read line; do
	echo $line | grep -q USER_COMMAND_1
        if [ $? -eq 0 ]; then
        	UC1=$(echo $line)
        fi
done < /usr/local/etc/pcp/pcp.cfg

UC_LINE=$(echo $UC1 | awk -F'USER_COMMAND_2=' '{print $2}' | sed 's/"//g')

if [ "$UC_LINE" == "" ]; then
    # Command line is blank, so update it
    echo "Updating User Command"
    if [ $dac == "E" ]; then
        $(sed -i 's/USER_COMMAND_1=""/USER_COMMAND_1="python3+%2Fhome%2Ftc%2Flms_oled_4.py"/' /usr/local/etc/pcp/pcp.cfg)
    else
        $(sed -i 's/USER_COMMAND_1=""/USER_COMMAND_1="python3+%2Fhome%2Ftc%2Flms_oled_mini_4.py"/' /usr/local/etc/pcp/pcp.cfg)
    fi
fi

echo "Backing up PCP"
pcp bu  1>>/dev/null

echo "Extension Installed.  Now reboot using ""pcp rb"""
