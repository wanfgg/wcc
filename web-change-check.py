#!/usr/bin/env python
# -*- encoding: utf-8 -*-
#

import sys; reload(sys)
sys.setdefaultencoding('utf-8') # we always need failsafe utf-8, in some way

import os
import re
import time
import hashlib
import urllib
import difflib
import smtplib
import htmlentitydefs

from email.mime.text import MIMEText


# tag used in output
TAG = "web change checker2"

# config file path
CONF = "conf"

# persistent directory prefix
PER_DIR = "/var/tmp/wcc"

# make verbose output - cron will spam you :p
DEBUG = True

# assume a local mail server without authentiction at port 25
SERVER = "localhost"
PORT = 25
FROM = "user@localhost"

class Site:
    def __init__(self, url, striphtml, emails):
        self.url = url
        self.striphtml = striphtml
        self.emails = emails



def sendMail(msg, subject, to):
    text = MIMEText(msg)
    text['Subject'] = subject
    text['From'] = FROM
    text['To'] = to
    
    s = smtplib.SMTP(SERVER, PORT)
    s.starttls()
    s.sendmail(FROM, [to], text.as_string())
    s.quit()

def stripHTML(orig):
    new = re.sub('<[^>]*>', ' ', orig)
    
    def conv(m):
        text = m.group(0)
        try:
            text = unichr(htmlentitydefs.name2codepoint[text[1:-1]])
        except KeyError:
            pass
        return text
    
    # replace named html entities like &amp;
    return re.sub("&\w+;", conv, new)

def main():
    # read all lines
    for line in open(CONF, 'r'):
        line = line.strip()
        if not re.match(r'^[^#]', line):
            continue
        
        #print line
        
        args = [arg for arg in line.split(';')]
        
        url, striphtml = args[0:2]
        if DEBUG: print "site: %s" % url
        if DEBUG: print "  striphtml: %s" % striphtml
        
        emails = args[2:]
        
        tname = hashlib.md5(url).hexdigest()[0:8]
        if DEBUG: print "  tname: %s" % tname
        
        tsite = re.sub(r'[^/]*//([^@]*@)?([^:/]*).*', r'\2', url)
        if DEBUG: print "  tsite: %s" % tsite
        
        # persistent files
        MD5_FILE = os.path.join(PER_DIR, tname+'.md5')
        SITE_FILE = os.path.join(PER_DIR, tname+'.site')
        
        # retrieve site
        new_data = urllib.urlopen(url).read()
        # hash before converting charset
        new_md5 = hashlib.md5(new_data).hexdigest()
        
        # detect encoding of site - assume UTF-8 as default
        enc = "utf-8"
        for line in new_data.splitlines(True):
            if re.search(r'<meta.*?content-type.*?>', line, re.IGNORECASE):
                # found line with meta tag containing content-type information
                # now filter out the charset information:
                match = re.search(r'<meta.*charset=([a-zA-Z0-9-]*).*', line)
                if match.group(1) != "": enc = match.group(1).lower()
                break
                
        if DEBUG: print "  encoding: %s" % enc
        
        # new_data is available in utf-8 (system default encoding)
        new_data = new_data.decode(enc)
        
        if not os.path.exists(MD5_FILE):
            outmd5 = open(MD5_FILE, 'w')
            outmd5.write(new_md5+'\n')
            outmd5.close()
            
            outdata = open(SITE_FILE, 'w')
            outdata.write(new_data+'\n')
            outdata.close()
            continue
            
        inmd5 = open(MD5_FILE, 'r')
        old_md5 = inmd5.readline().strip()
        inmd5.close()
        
        indata = open(SITE_FILE, 'r')
        old_data = indata.readlines()
        indata.close()
        
        if old_md5 != new_md5:
            if DEBUG:
                print "  Change detected:"
                print "    old md5: %s, new md5: %s" % (old_md5, new_md5)
            
            # content of email
            content = "Change at %s - diff follows:\n\n" % url
            
            diffGen = difflib.unified_diff(
                old_data,
                new_data.splitlines(True),
                "OLD",
                "NEW",
                '(%s)' % time.strftime('%Y-%m-%d %H:%M:%S',
                                time.gmtime(os.path.getmtime(MD5_FILE))),
                '(%s)' % time.strftime('%Y-%m-%d %H:%M:%S', time.localtime()),
                1)
            
            diff = ''.join([line for line in diffGen])
            
            if striphtml == "yes":
                diff = stripHTML(diff)
            
            content += diff
                        
            for addr in emails:
                if DEBUG: print "    addr: %s" % addr
                sendMail(content, "[%s] %s changed" % (TAG, tsite), addr)
                
            # syslog connection
            #logger -t "$TAG" "Change at $site (tag $tname) detected"
            
            # do update
            outmd5 = open(MD5_FILE, 'w')
            outmd5.write(new_md5+'\n')
            outmd5.close()
            
            outdata = open(SITE_FILE, 'w')
            outdata.write(new_data+'\n')
            outdata.close()

if __name__ == '__main__':
    from optparse import OptionParser
    parser = OptionParser()
    parser.add_option("-v", "--verbose", action="store_true",
                dest="verbose", default=True, help="prints all debug messages")
                
    (options, args) = parser.parse_args()
    DEBUG = options.verbose
    
    main()
