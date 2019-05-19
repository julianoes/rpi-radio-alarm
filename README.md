# RPi Radio Alarm

This is a simple internet radio alarm for the Raspberry Pi.
It is basically a tiny REST interface using [Gunicorn](http://gunicorn.org/) and [Falcon](https://falconframework.org) playing radio using [mplayer](http://www.mplayerhq.hu).

## Installation

### Dependencies

```
sudo apt install python git mplayer python-falcon gunicorn
```

### Get it

```
cd ~
mkdir src
cd src
git clone https://github.com/julianoes/rpi-radio-alarm
```

### Autostart

Edit the [gunicorn.service](gunicorn.service) file and make sure the `WorkingDirectory` matches where this repository is cloned into.

Copy the systemd service file to /etc/systemd/system, enable and start it.

```
sudo cp gunicorn.service /etc/systemd/system/
sudo systemctl start gunicorn
sudo systemctl enable gunicorn
```

# License

This is published under the [3-Clause BSD License](LICENSE.md).
