#!/usr/bin/env fish

pip install -r requirements.txt
cp cron.d/* /etc/cron.d/
git crypt unlock ~/.config/git/keys/crawlers
