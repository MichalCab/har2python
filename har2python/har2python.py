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

template_path = "../"
header_file = "header.sab"
footer_file = "footer.sab"

debug = [1 for v in sys.argv if v == "--debug"]

def to_dict(data):
    """Convert json to dict data, if input is not json return None"""
    if isinstance(data, dict):
        return data
    try:
        value = json.loads(data)
        if not isinstance(value, dict):
            raise
        return value
    except:
        return None

def decode_data(data):
    """Load POST/GET http data to dict with python objects (json/strings)"""
    post_data = {}
    for param in data:
        _type = "text"
        value = to_dict(urllib.unquote(param["value"]).decode('utf-8'))
        if value:
            _type = "json"
        else:
            value = urllib.unquote(param["value"]).decode('utf-8')

        name = urllib.unquote(param["name"]).decode('utf-8')
        post_data[name] = {"type":_type, "value":value}
    return post_data

def parse_har(har):
    """parse_har file"""
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
                    #parse payload data
                    request["postData"]["text"]["value"] = json.loads(request["postData"]["text"])
                    payload_data = request["postData"]
                else:
                    #parse post data
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


#TODO rewrite this (too unclear)
def compare_data(a,b, first=False, path=""):
    """Compare two POST/GET data and save """
    diff = {}
    done = []
    for k_a, v_a in a.items():
        if first:
            v_a = v_a["value"]
        for k_b, v_b in b.items():
            if first:
                v_b = v_b["value"]
            if k_a == k_b and k_a not in done and v_a != v_b:
                done.append(k_a) #TODO i think here is problem (same key in json) (path + k_a ?)
                    
                # because '{"key":[1, 2]}'  (need to compare values in list)
                is_list = True
                if not isinstance(v_a, list):
                    v_a = [v_a]
                    v_b = [v_b]
                    is_list = False

                for index, a_item in enumerate(v_a):
                    index_string = ("[%s]" % index if is_list else "")
                    b_item = v_b[index]
                    if a_item != b_item:
                        dict_a = to_dict(a_item)
                        dict_b = to_dict(b_item)
                        if dict_a and dict_b:
                            path = "" if first else "%s[\"%s\"]%s" % (path, k_a, index_string)
                            diff.update(compare_data(dict_a, dict_b, path=path))
                        else:
                            key = k_a
                            if is_list:
                                key = "%s[\"%s\"]%s" % (path, k_a, index_string)
                            diff.update({
                                key:[
                                    {"type":"text","value":a_item}, 
                                    {"type":"text","value":b_item}
                                ]
                            })
    return diff

def compare(entry_a):
    entry_b = parse_har(sys.argv[2])
    for i,_a in enumerate(entry_a):
        if i < len(entry_b):
            b = entry_b[i]
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
            #if debug:
            #    print "MATCH", a["url"], b["url"]
            a["compare_result"]["get_vars"] = compare_data(a["request"]["get"], b["request"]["get"], True)
            a["compare_result"]["post_vars"] = compare_data(a["request"]["post"], b["request"]["post"], True)
            a["compare_result"]["payload_vars"] = compare_data(a["request"]["payload"], b["request"]["payload"], True)
        else:
            if debug:
                print "NOT MATCH", a["url"], b["url"]
            continue

def print_dic(_dict, _vars=[]):
    res = """{"""
    variables_in_json = []
    #variables in json data
    for k,v in _vars.items():
        if "[" in k:
            for key, val in  _dict.items():
                try:
                    var_name = '_'+re.sub(r'\W+', '', k)
                    exec "_dict['%s']['value']%s = '_'+re.sub(r'\W+', '', k)" % (key, k)
                    variables_in_json.append(var_name)
                except:
                    pass
    for key, val in  _dict.items():
        if key in _vars:
            var_name = "_"+re.sub("\W+", "", key)
            if val["type"] == "json":
                var_name = "ujson.dumps(%s)" % var_name
            res += """
            '%s' : %s,""" % (key, var_name)
        else:
            s = "'%s'" % val["value"]
            if val["type"] == "json":
                s = pformat(val["value"])
                for _var_in_json in variables_in_json:
                    s = s.replace("u'%s'" % _var_in_json, "%s" %_var_in_json)
            res += """
            '%s' : %s,""" % (key, s)
    res += """
        }"""
    return res

def print_vars(_vars):
    """Print variables (only if two files compare is used)"""
    res = "" 
    all_vars = []
    var_counter = 0
    for key, vals in _vars.items():
        #generate var name
        var_name = "_"+re.sub("\W+", "", key)
        while var_name in all_vars:
            var_name = "%s%s" % (var_name, var_counter)
            var_counter += 1
        all_vars.append(var_name)
 
        s = "'%s'" % vals[0]["value"]
        s2 = "'%s'" % vals[1]["value"]
        
        if vals[0]["type"] == "json":
            s = pformat(vals[0]["value"])
            s2 = pformat(vals[1]["value"])
        
        data = (var_name, s, s, s2)
        if len(s) < 80:
            res += """
        %s = %s
        #TODO values: %s #VS %s
        """ % data
        else:
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
    """create python code for grab http request"""
    py = ""
    #get
    if len(entry["request"]["get"]) > 0:
        data = (print_vars(entry["compare_result"]["get_vars"]),
                print_dic(entry["request"]["get"], entry["compare_result"]["get_vars"]),
                entry["url"]+"?",
                "+urllib.urlencode(get_data)")
        py += """%s
        get_data = %s
        g.go("%s"%s)
        """ % data
    #post
    if len(entry["request"]["post"]) > 0:
        data = (print_vars(entry["compare_result"]["post_vars"]),
                print_dic(entry["request"]["post"], entry["compare_result"]["post_vars"]),
                entry["url"])
        py += """%s
        post_data = %s
        g.setup(post=post_data)
        g.go("%s")
        """ % data

    #payload
    if len(entry["request"]["payload"]) > 0:
        data = (print_vars(entry["compare_result"]["payload_vars"]),
                entry["request"]["payload"]["mimeType"],
                print_dic(entry["request"]["payload"]["text"],entry["compare_result"]["payload_vars"]),
                entry["url"])
        py += """%s
        headers = {"Content-Type":"%s"}
        payload_data = %s
        g.setup(post=ujson.dumps(payload_data), headers=headers)
        g.go("%s")
        """ % data

    return py

if __name__ == "__main__":
    #get list of entries 
    #(1 entry = http req(data, header, GET/POST data)+response(html/json content)) 
    #loaded from har file
    entries = parse_har(sys.argv[1])

    #if two files (same HAR files just with different values) on input, compare them
    #is used for create variables in code
    if len(sys.argv) >= 3:
        compare(entries)

    #prepare script content...
    py = open("%s%s" % (template_path, header_file), "rb").read()
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
    py += open("%s%s" % (template_path, footer_file), 'rb').read()
    #...prepared

    if not debug:
        print py
