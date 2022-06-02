
echo ""
echo "Setup for OLED with LMS on Raspberry Pi"
echo ""

while true; do
    read -p "Are you setting up EvoSabre or RASPDac Mini?" er
    case $er in
        [E]* ) echo "Setup for EvoSabre OLED extension (E)"; dac="E";break;;
        [R]* ) echo "Setup for RASPDac Mini OLED extension (R)"; dac="R";break;;
        * ) echo "Please answer E or R";;
    esac
done

#Check if LIRC is installed before proceeding
while read line; do
	echo $line | grep -q IR_LIRC
        if [ $? -eq 0 ]; then
        	IR_LIRC=$(echo $line)
        fi
done < /usr/local/etc/pcp/pcp.cfg

LIRC_installed=$(echo $IR_LIRC | awk -F'IR_LIRC=' '{print $2}' | sed 's/"//g')

if [ $LIRC_installed != "yes" ]; then
    echo ""
    echo "LIRC is not installed.  If you continue, IR config files won't be installed"
    while true; do
    read -p "Do you wish to exit this setup and install LIRC first?" yn
    case $yn in
        [Yy]* ) echo "Please install LIRC in PCP Tweaks and re-run this setup"; exit;;
        [Nn]* ) echo "Continue"; break;;
        * ) echo "Please answer yes or no.";;
    esac
done
fi

tmp=$(mktemp)
tmpdir=$(mktemp -d)

echo "Installing python3 and freetype extension"
tce-load -iw python3.8 freetype 1>>/dev/null 2>>/dev/null

echo "Downloading Extension from GitHub"
wget -q https://github.com/peteS-UK/EvoSabre-DAC-PCP/releases/download/EvoSabre/evosabre.tar.gz -O $tmp

echo "Unpacking Files"
tar -xzf $tmp -C $tmpdir

rm $tmp

echo "Moving Files to home"

if [ $dac == "E" ]; then
    mv -f $tmpdir/evosabre/home/lms_oled_4.py ~
else
    mv -f $tmpdir/evosabre/home/lms_oled_mini_4.py ~
fi

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


if [ $LIRC_installed = "yes" ]; then
    echo "Copying lirc setup files"
    if [ $dac == "E" ]; then
        sudo cp -p $tmpdir/evosabre/.lircrc ~
        sudo cp -p $tmpdir/evosabre/lircd.conf /usr/local/etc/lirc
    else
        sudo cp -p $tmpdir/evosabre/.lircrc.mini ~/.lircrc
        sudo cp -p $tmpdir/evosabre/lircd.conf.mini /usr/local/etc/lirc/lircd.conf
    fi
fi 

rm -rf $tmpdir

echo "Backing up PCP"
pcp bu  1>>/dev/null

echo "Extension Installed.  Now reboot using ""pcp rb"""
