

tmp=$(mktemp)
tmpdir=$(mktemp -d)

echo "Downloading Extension from GitHub"
wget -q https://github.com/peteS-UK/EvoSabre-DAC-PCP/releases/download/EvoSabre/evosabre.tar.gz -O $tmp

echo "Unpacking Files"
tar -xzf $tmp -C $tmpdir

rm $tmp

echo "Moving Files to home"
mv -f $tmpdir/evosabre/home/lms_oled_3.12_py3.py ~

mkdir ~/fonts 2>>/dev/null
mv -f $tmpdir/evosabre/home/fonts/* ~/fonts


if [ "$(uname -m)" = "aarch64" ]; then
    echo "Installing 64 bit extension"
    tczname="evosabre-py38-64-deps.tcz"
else
    echo "Installing 32 bit extension"
    tczname="evosabre-py38-deps.tcz"
fi

sudo cp -p "$tmpdir/evosabre/$tczname" /etc/sysconfig/tcedir/optional 1>>/dev/null
echo "$tczname" | sudo tee -a /etc/sysconfig/tcedir/onboot.lst 1>>/dev/null

rm -rf $tmpdir

echo "Backing up PCP"
#pcp bu  1>>/dev/null

echo "${RED}Extension Installed.  Now reboot using ""pcp rb""${NORMAL}"
