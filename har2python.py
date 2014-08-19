#! /usr/bin/env python
# -*- coding: utf-8 -*-

import sys
import os
import json
import urllib
from pprint import pprint
from time import sleep
from grab import Grab

__author__ = "Michal Cab <majklcab at gmail.com>"

exclude = [".js", ".bs", ".png", ".jpg", ".gif", ".css", ".inc", 
           ".css.xhtml", ".js.xhtml", ".png.xhtml", ".gif.xhtml", 
           ".woff", ".jpg.xhtml", ".ttf"
          ]

tab = "    "

todo_lenght = 10000

debug = [1 for v in sys.argv if v == "--debug"]

def decode_data(data):
    post_data = {}
    for param in data:
        value = urllib.unquote(param["value"]).decode('utf-8')
        name = urllib.unquote(param["name"]).decode('utf-8')
        post_data[name] = value
    return post_data

def get_data(har):
    res = []
    with open(har) as json_data:
        har = json.load(json_data)
        for h in har["log"]["entries"]:
            request = h["request"]
            url = request["url"].split("?")[0]
            if (url[-3:].lower() in exclude or url[-4:].lower() in exclude or 
                    url[-5:].lower() in exclude or url[-9:].lower() in exclude or
                    url[-10:].lower() in exclude or "google" in url or "facebook" in url or
                    "doubleclick" in url):
                continue
            get_data = decode_data(request["queryString"])
            post_data = decode_data(request["postData"]["params"]) if "postData" in request else {}
            res.append({"url":url, "get":get_data, "post":post_data, "get_vars":{}, "post_vars":{}})
    return res  

def compare(aa):
    bb = get_data(sys.argv[2])
    for i,_a in enumerate(aa):
        if i < len(bb):
            b = bb[i]
            a = _a

        #HTTPS vs HTTP
        if a["url"][5:] == b["url"][4:]:
            b["url"] = "https"+b["url"][4:]
        if a["url"][4:] == b["url"][5:]:
            a["url"] = "https"+a["url"][4:]

        #www. vs without www.
        if a["url"].replace("www.","") == b["url"]:
            b["url"] = a["url"]
        if a["url"] == b["url"].replace("www.",""):
            a["url"] = b["url"]
        
        if a["url"] == b["url"]:
            if debug:
                print "MATCH", a["url"], b["url"]
            get_done = []
            for key_a, val_a in a["get"].items():
                for key_b, val_b in b["get"].items():
                    if key_a == key_b and key_a not in get_done and val_a != val_b:
                        get_done.append(key_a)
                        a["get_vars"].update({key_a:[val_a[:todo_lenght], val_b[:todo_lenght]]})

            post_done = []
            for key_a, val_a in a["post"].items():
                for key_b, val_b in b["post"].items():
                    if key_a == key_b and key_a not in post_done and val_a != val_b:
                        post_done.append(key_a)
                        a["post_vars"].update({key_a:[val_a[:todo_lenght], val_b[:todo_lenght]]})
        else:
            if debug:
                print "NOT MATCH", a["url"], b["url"]
            continue

def print_dic(_dict, _vars):
    res = "{\n"
    for key, val in  _dict.items():
        if key in _vars:
            res += "%s'%s' : %s,\n" % (tab, key, "_"+key)
        else:
            res += "%s'%s' : '%s',\n" % (tab, key, val)
    res += "}"
    return res

if __name__ == "__main__":
    py = ("#! /usr/bin/env python\n# -*- coding: utf-8 -*-\n\n"
          "from time import sleep\n"
          "from grab import Grab\nimport urllib\n\ng = Grab()\n")
    aa = get_data(sys.argv[1])
    if len(sys.argv) >= 3:
        compare(aa)
    for a in aa:
        plus = ""
        if len(a["post"]) > 0:
            for key, val in a["post_vars"].items():
                py += '_%s = None #TODO values: \n#%s\n' % (key, "\n#VS\n#".join(val))
            py += 'post_data = %s\n' % print_dic(a["post"], a["post_vars"])
            py += 'g.setup(post=post_data)\n'
        if len(a["get"]) > 0:
            for key, val in a["get_vars"].items():
                py += '_%s = None #TODO values: \n#%s\n' % (key, "\n#VS\n#".join(val))
            py += 'get_data = %s\n' % print_dic(a["get"], a["get_vars"])
            plus = '+"?"+urllib.urlencode(get_data)'
        py += 'g.go("%s"%s)\n' % (a["url"], plus)
        py += 'print "from %s"%s\n' % (a["url"], plus)
        py += 'print ">>" + g.response.url\nprint g.response.code\nsleep(0.5)\n\n'
    if not debug:
        print py
