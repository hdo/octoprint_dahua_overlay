# -*- coding: utf-8 -*-
#!/usr/bin/env python
import os
import sys
import configparser
import subprocess
import json
import datetime
import time
from subprocess import Popen
from urllib.parse import quote

class Config:

    def __init__(self):
        self.mock = ""
        self.octo_api_key = ""
        self.octo_host = "" 
        self.octo_port = ""
        self.cam_host = ""
        self.cam_port = ""
        self.cam_user = ""
        self.cam_password = ""
        self.interval = ""

    def get_is_mock(self):
        if self.mock == '1':
            return True
        return False

    def get_interval_seconds(self):
        if self.interval and len(self.interval) > 0:
            return int(self.interval)
        #default
        return 30 

class PrinterStatus:

    def __init__(self):
        self.state = "N/A"
        self.completion = 0.0
        self.printTime = 0
        self.printTimeText = ""
        self.bed_actual = 0.0
        self.bed_target = 0.0
        self.tool_actual = 0.0
        self.tool_target = 0.0
        self.date = 0
        self.dateText = ""

    def update_times(self):
        if self.printTime > 0:
            hours = self.printTime / 3600
            minutes = (self.printTime / 60) % 60
            seconds = self.printTime % 60
            self.printTimeText = "%.2d:%.2d:%.2d" % (hours, minutes, seconds)
        if self.date > 0:
            self.dateText = datetime.datetime.fromtimestamp(self.date)

    def parse_job(self, json_o):
        if 'state' in json_o:
            self.state = json_o['state']
        if 'progress' in json_o:
            self.printTime = json_o['progress']['printTime']
            self.completion = json_o['progress']['completion']
        if 'job' in json_o:
            self.date = json_o['job']['file']['date']
        return

    def parse_printer(self, json_o):
        self.bed_actual = json_o['temperature']['bed']['actual']
        self.bed_target = json_o['temperature']['bed']['target']
        self.tool_actual = json_o['temperature']['tool0']['actual']
        self.tool_target = json_o['temperature']['tool0']['target']
        return

    def parse(self, jsonstring):
        if jsonstring and len(jsonstring) > 0:
            json_o = json.loads(jsonstring)
            if 'job' in json_o:
                self.parse_job(json_o)
            if 'temperature' in json_o:
                self.parse_printer(json_o)
        self.update_times()
        return

    def get_dahua_format(self):
        line1 = 'State: %s' % self.state
        line2 = 'Progress: %.2f %%' % self.completion
        line3 = 'Bed: %.1f \u00b0C (%.1f \u00b0C)' % (self.bed_actual, self.bed_target)
        line4 = 'Tool: %.1f \u00b0C (%.1f \u00b0C)' % (self.tool_actual, self.tool_target)
        line5 = 'Print Time: %s' % (self.printTimeText)
        rettext = '%s|%s|%s|%s|%s' % (quote(line1), quote(line2), quote(line3), quote(line4), quote(line5))
        return rettext

    def printout(self):
        print(self.state)
        print(self.printTime)
        print(self.printTimeText)
        print(self.bed_target)
        print(self.bed_actual)
        print(self.tool_target)
        print(self.tool_actual)
        print(self.date)
        print(self.dateText)


def set_check_option(config, conf, key):
    if config.has_option('main',key):
        setattr(conf, key, config.get('main', key))
        return True
    else:
        print("Missing option %s" % key)
        return False


def check_config(conf):
    if not os.path.exists('config.ini'):
        print('Missing configuration!')
        return False
    else:
        print("Reading config.ini")
        config = configparser.ConfigParser()
        config.read("config.ini")
        if not set_check_option(config, conf, 'mock'):
            return False
        if not set_check_option(config, conf, 'octo_host'):
            return False
        if not set_check_option(config, conf, 'octo_port'):
            return False
        if not set_check_option(config, conf, 'octo_api_key'):
            return False
        if not set_check_option(config, conf, 'cam_host'):
            return False
        if not set_check_option(config, conf, 'cam_port'):
            return False
        if not set_check_option(config, conf, 'cam_user'):
            return False
        if not set_check_option(config, conf, 'cam_password'):
            return False
        if not set_check_option(config, conf, 'interval'):
            return False

    return True




def get_octo_command_job(conf):
    url = "http://%s:%s/api/job?apikey=%s" % (conf.octo_host, conf.octo_port, conf.octo_api_key)
    #print(url)
    params = ["curl", "-s", "-m", "5", url]
    return Popen(params, stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)

def get_octo_command_printer(conf):
    url = "http://%s:%s/api/printer?apikey=%s" % (conf.octo_host, conf.octo_port, conf.octo_api_key)
    #print(url)
    params = ["curl", "-s", "-m", "5", url]
    return Popen(params, stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)

def get_cam_command_settext(conf, text):
    url = "http://%s:%s/cgi-bin/configManager.cgi?action=setConfig&VideoWidget[0].CustomTitle[1].Text=%s" % (conf.cam_host, conf.cam_port, text)
    #print(url)
    userpass = "%s:%s" % (conf.cam_user, conf.cam_password)
    params = ["curl", "-s", "-m", "5", "--anyauth", "-u", userpass, "-g", url]
    return Popen(params, stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)


def get_stdout_from_po(po):
    (stdout, stderr) = po.communicate()
    return stdout

def process(conf, pStatus):
    if conf.get_is_mock():
        json_job = open('mock/job.json').read()
        pStatus.parse(json_job)
        json_printer = open('mock/printer.json').read()
        pStatus.parse(json_printer)
        pStatus.printout()
        print(pStatus.get_dahua_format())
    else:
        jsondata = get_stdout_from_po(get_octo_command_job(conf))
        pStatus.parse(jsondata)
        jsondata = get_stdout_from_po(get_octo_command_printer(conf))
        pStatus.parse(jsondata)
        #pStatus.printout()
        #print(pStatus.get_dahua_format())
        retcode = get_stdout_from_po(get_cam_command_settext(conf, pStatus.get_dahua_format()))
        print(retcode)



def test_connect(conf):
    #(stdout, stderr) = get_octo_command_job(conf).communicate()
    #print(stdout)
    #(stdout, stderr) = get_octo_command_printer(conf).communicate()
    #print(stdout)
    (stdout, stderr) = get_cam_command_settext(conf, "lorem|ipsum").communicate()
    print(stdout)
    return    

def main(argv):
    conf = Config()
    if check_config(conf):
        print('Starting ...') 
        print(conf.octo_host)
        print(conf.octo_port)
        #test_connect(conf)
        pStatus = PrinterStatus()
        process(conf, pStatus)
        #pStatus.printout()
        counter = 0
        interval = conf.get_interval_seconds()
        print("Inteval: %d" % interval)
        while True:
            counter = counter + 1
            if counter > interval:
                counter = 0
                try:
                    process(conf, pStatus)                
                except:
                    print('Error!')
            time.sleep(1)
    else:
        print('Done')
        return

if __name__ == "__main__":
    main(sys.argv[1:])
