#! /usr/bin/env python
# -*- coding: utf-8 -*-

import sys
import os
import json
import urllib
import re
from pprint import pprint, pformat
from time import sleep
from grab import Grab

__author__ = "Michal Cab <majklcab at gmail.com>"

exclude = [".js", ".bs", ".png", ".jpg", ".gif", ".css", ".inc", 
           ".css.xhtml", ".js.xhtml", ".png.xhtml", ".gif.xhtml", 
           ".woff", ".jpg.xhtml", ".ttf",".jpeg"
          ]

todo_lenght = 10000

debug = [1 for v in sys.argv if v == "--debug"]

def decode_data(data):
    post_data = {}
    for param in data:
        _type = "text"
        value = urllib.unquote(param["value"]).decode('utf-8')
        try:
            value = json.loads(urllib.unquote(param["value"]).decode('utf-8'))
            _type = "json"
        except:
            pass
        name = urllib.unquote(param["name"]).decode('utf-8')
        post_data[name] = {"type":_type, "value":value}
    return post_data

def get_data(har):
    res = []
    with open(har) as json_data:
        har = json.load(json_data)
        for h in har["log"]["entries"]:
            request = h["request"]
            url = request["url"].split("?")[0]
            #filter entries
            if (url[-3:].lower() in exclude or url[-4:].lower() in exclude or 
                    url[-5:].lower() in exclude or url[-9:].lower() in exclude or
                    url[-10:].lower() in exclude or "google" in url or "facebook" in url or
                    "doubleclick" in url):
                continue
            #parse GET data
            get_data = decode_data(request["queryString"])
            payload_data = {}
            post_data = {}
            if "postData" in request:
                if ("mimeType" in request["postData"] and 
                        "text" in request["postData"] and 
                        "params" not in request["postData"]):
                    #payload
                    request["postData"]["text"]["value"] = json.loads(request["postData"]["text"])
                    payload_data = request["postData"]
                else:
                    #post
                    post_data = decode_data(request["postData"]["params"])
            request = {
                "get":get_data,
                "post":post_data,
                "payload":payload_data,
            }
            compare_result = {
                "get_vars":{},
                "post_vars":{},
                "payload_vars":{},
            }
            response = {
                "cookies": h["response"]["cookies"],
                "status": str(h["response"]["status"])
            }
            res.append({
                "url":url,
                "request":request,
                "compare_result":compare_result,
                "response":response
            })
    return res  

def compare_data(a, b):
    get_done = []
    res = {}
    for key_a, val_a in a.items():
        for key_b, val_b in b.items():
            if key_a == key_b and key_a not in get_done and val_a != val_b:
                get_done.append(key_a)
                res.update({key_a:[val_a, val_b]})
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
        
        #when url match
        if a["url"] == b["url"]:
            if debug:
                print "MATCH", a["url"], b["url"]
            a["compare_result"]["get_vars"] = compare_data(a["request"]["get"], b["request"]["get"])
            a["compare_result"]["post_vars"] = compare_data(a["request"]["post"], b["request"]["post"])
            a["compare_result"]["payload_vars"] = compare_data(a["request"]["payload"], b["request"]["payload"])
        else:
            if debug:
                print "NOT MATCH", a["url"], b["url"]
            continue

def print_dic(_dict, _vars=[]):
    res = """{"""
    for key, val in  _dict.items():
        if key in _vars:
            var_name = "_"+re.sub("\W+", "", key)
            res += """
            '%s' : %s,""" % (key, var_name)
        else:
            s = "'%s'" % val["value"]
            if val["type"] == "json":
                s = pformat(val["value"])
            res += """
            '%s' : %s,""" % (key, s)
    res += """
        }"""
    return res

def print_vars(_vars):
    res = "" 
    all_vars = []
    var_counter = 0
    for key, vals in _vars.items():
        var_name = "_"+re.sub("\W+", "", key)

        #check if var exists
        while var_name in all_vars:
            var_name = "%s%s" % (var_name, var_counter)
            var_counter += 1
        all_vars.append(var_name)

        s = "'%s'"%vals[0]["value"]
        s2 = "'%s'"%vals[1]["value"]
        if vals[0]["type"] == "json":
            s = pformat(vals[0]["value"])
            s2 = pformat(vals[1]["value"])
        data = (var_name, s, s, s2)
        res += """
        %s = %s
        #TODO values:
        \"\"\"
        %s
        \"\"\"
        #VS
        \"\"\"
        %s
        \"\"\"
        """ % data
    return res

def make_request(entry):
    py = ""
    #post
    if len(entry["request"]["post"]) > 0:
        data = (print_vars(entry["compare_result"]["post_vars"]),
                print_dic(entry["request"]["post"], entry["compare_result"]["post_vars"]),
                entry["url"])
        py += """%s
        post_data = %s
        g.setup(post=post_data)
        g.go("%s")""" % data

    #payload
    if len(entry["request"]["payload"]) > 0:
        data = (entry["request"]["payload"]["mimeType"],
                print_dic(entry["request"]["payload"]["text"],entry["compare_result"]["payload_vars"]),
                entry["url"])
        py += """
        headers = {"Content-Type":"%s"}
        payload_data = %s
        g.setup(post=ujson.dumps(payload_data), headers=headers)
        g.go("%s")""" % data

    #get
    if len(entry["request"]["get"]) > 0:
        data = (print_vars(entry["compare_result"]["get_vars"]),
                print_dic(entry["request"]["get"],
                entry["compare_result"]["get_vars"]),
                entry["url"]+"?",
                "+urllib.urlencode(get_data)")
        py += """%s
        get_data = %s
        g.go("%s"%s)""" % data
    return py

if __name__ == "__main__":
    entries = get_data(sys.argv[1])

    #if two files on input, compare them
    if len(sys.argv) >= 3:
        compare(entries)

    #prepare script content...
    py = open("header.sab","rb").read()
    make_req = True
    for entry in entries:
        #build request code
        if make_req:
            py += make_request(entry)
        else: make_req = True

        #redirection
        if entry["response"]["status"][0] == "3":
            make_req = False

        #cookie info
        if len(entry["response"]["cookies"]) > 0:
            py += """
        #SETTING COOKIES"""

        #response status
        data = (entry["url"])
        py += """
        print "from %s"
        print "to " + g.response.url
        print g.response.code
""" % data
    py += open("footer.sab",'rb').read()
    #...prepared

    if not debug:
        print py
