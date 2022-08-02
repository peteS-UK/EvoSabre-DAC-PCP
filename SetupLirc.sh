
echo ""
echo "Setup for lirc for EvoSabre & RaspDAC Mini on PCP"
echo ""

while true; do
    read -p "Are you setting up EvoSabre (E) or RASPDac Mini (R)?" er
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
    echo "LIRC is not installed."
    echo "Please install LIRC in PCP Tweaks and re-run this setup"
    exit
fi

echo "Downloading lirc file from GitHub"
if [ $dac == "E" ]; then
    wget -q https://raw.githubusercontent.com/peteS-UK/EvoSabre-DAC-PCP/main/lirc/evosabre/.lircrc -O ~/.lircrc
    wget -q https://raw.githubusercontent.com/peteS-UK/EvoSabre-DAC-PCP/main/lirc/evosabre/lircd.conf -O /usr/local/etc/lirc/lircd.conf
else
    wget -q https://raw.githubusercontent.com/peteS-UK/EvoSabre-DAC-PCP/main/lirc/mini/.lircrc -O ~/.lircrc
    wget -q https://raw.githubusercontent.com/peteS-UK/EvoSabre-DAC-PCP/main/lirc/mini/lircd.conf -O /usr/local/etc/lirc/lircd.conf
fi


echo "Backing up PCP"
pcp bu  1>>/dev/null

echo "LIRC Installed.  Now reboot using ""pcp rb"""
