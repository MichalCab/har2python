#! /usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function
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
           ".woff", ".jpg.xhtml", ".ttf",".jpeg",".swf"
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
    """
    Load POST/GET http data to dict with python objects (json/strings)
    Used in har parser

    return example
    type = ["text", "dict"]
    data = [str, dict]
    {
        "key": 
        {
            "type" : type,
            "value" : data
        }
    }
    """
    post_data = {}
    for param in data:
        try:
            name = urllib.unquote(param["name"]).decode('utf-8')
        except:
            name = "PROBLEM_HERE0"
        try:
            data = urllib.unquote(param["value"]).decode('utf-8')
        except:
            data = "PROBLEM HERE"

        _type = "text"
        value = to_dict(data)
        if value is not None:
            _type = "dict"
        else:
            value = data

        i = 0
        while name in post_data and post_data[name]["value"][:-1] == "PROBLEM_HERE":
            name += str(i)
            i += 1 
        
        post_data[name] = {"type":_type, "value":value}
    return post_data

def parse_har(har):
    """parse_har file"""
    res = []
    with open(har) as json_data:
        try:
            har = json.load(json_data)
        except:
            warning("file '%s' is not har file" % har)
            exit(1)
        for h in har["log"]["entries"]:
            request = h["request"]
            url = request["url"].split("?")[0]
            real_url = request["url"]
            #filter entries
            if (url[-3:].lower() in exclude or url[-4:].lower() in exclude or 
                    url[-5:].lower() in exclude or url[-9:].lower() in exclude or
                    url[-10:].lower() in exclude or "google" in url or "facebook" in url or
                    "doubleclick" in url
                    or "webvisor" in url or "yandex" in url or "monetate.net" in url
                    or "cloudfront.net" in url or "h4k5.com" in url or "ssl.hurra.com" in url or
                    "secure.adnxs.com/px" in url and "swa.demdex.net" in url or "h.online-metrix.net" in url
                    or "ssl.vizury.com" in url or "www.vizury.com/analyze" in url or "country_specific_menu_dropdown" in url
                    or "ib.adnxs.com" in url or "twitter" in url):
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
                    request["postData"]["text"] = json.loads(request["postData"]["text"])
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
                "get_miss":{},
                "post_miss":{},
                "payload_miss":{},
            }
            response = {
                "cookies": h["response"]["cookies"],
                "status": str(h["response"]["status"])
            }
            if (len(request["get"]) is 0 and
                len(request["post"]) is 0 and
                len(request["payload"]) is 0 and
                len(response["cookies"]) is 0):
                continue
            res.append({
                "url":url,
                "expected_url":"",
                "real_url":real_url,
                "request":request,
                "compare_result":compare_result,
                "response":response
            })
    return res  

#TODO rewrite this (too unclear)
def compare_data(a, b, first=False, path=""):
    """
    Compare two POST/GET data and save
    Is called form compare(entry_a)
    """
    diff = {}
    done = []
    for k_a, v_a in a.items():
        if first and "value" in v_a:
            v_a = v_a["value"]
        for k_b, v_b in b.items():
            if first and "value" in v_b:
                v_b = v_b["value"]
            if k_a == k_b and k_a not in done and v_a != v_b:
                done.append(path + k_a) #TODO check! I think, checked
                ### because '{"key":[1, 2]}'  (need to compare values in list)
                is_list = True
                if not isinstance(v_a, list):
                    v_a = [v_a]
                    v_b = [v_b]
                    is_list = False
                ###
                for index, a_item in enumerate(v_a):
                    index_string = ("[%s]" % index if is_list else "")
                    b_item = v_b[index] # TODO b have always same lenght ?
                    if a_item == b_item:
                        continue
                    dict_a = to_dict(a_item)
                    dict_b = to_dict(b_item)
                    if dict_a and dict_b:
                        #track path for later replace this place with variable
                        path = "" if first else "%s[\"%s\"]%s" % (path, k_a, index_string)
                        diff.update(compare_data(dict_a, dict_b, path=path))
                    else:
                        key = k_a
                        if path != "":
                            key = "%s[\"%s\"]%s" % (path, k_a, index_string)
                        diff.update({
                            key:[{"type":"text","value":a_item}, 
                                {"type":"text","value":b_item}]
                        })
    #print(diff)
    return diff

def find_missing_data(a, b):
    res = []
    for k in a.keys():
        if k not in b:
            res.append(k)
    return res

#TODO can be improved
def compare(entry_a):
    """
    Compare two har files 
    Comparing POST/PAYLOAD/GET data
    """
    entry_b = parse_har(sys.argv[2])
    for i,a in enumerate(entry_a):
        if i < len(entry_b):
            b = entry_b[i]

        #HTTPS vs HTTP
        if a["url"][5:] == b["url"][4:]:
            b["url"] = "https%s" % b["url"][4:]
        if a["url"][4:] == b["url"][5:]:
            a["url"] = "https%s" % a["url"][4:]

        #www. vs without www.
        if a["url"].replace("www.","") == b["url"]:
            b["url"] = a["url"]
        if a["url"] == b["url"].replace("www.",""):
            a["url"] = b["url"]
        
        #when url match
        #TODO what if random order of req with same order
        #IDEA what if xxx.php;var1=X;var2=Y
        if a["url"] == b["url"]:
            if debug:
                print("a)MATCH %s" % a["url"])
                print("b)MATCH %s" % b["url"])
            a["compare_result"]["get_vars"] = compare_data(a["request"]["get"], 
                                                           b["request"]["get"],
                                                           first=True)
            a["compare_result"]["post_vars"] = compare_data(a["request"]["post"], 
                                                            b["request"]["post"], 
                                                            first=True)
            a["compare_result"]["payload_vars"] = compare_data(a["request"]["payload"], 
                                                               b["request"]["payload"], 
                                                               first=True)

            a["compare_result"]["get_miss"] = find_missing_data(a["request"]["get"],
                                                           b["request"]["get"],
                                                           )
            a["compare_result"]["post_miss"] = find_missing_data(a["request"]["post"],
                                                            b["request"]["post"],
                                                            )
            a["compare_result"]["payload_miss"] = find_missing_data(a["request"]["payload"],
                                                               b["request"]["payload"],
                                                               )
        else:
            if debug:
                print("a)NOT MATCH %s" % a["url"])
                print("b)NOT MATCH %s" % b["url"])

def print_dic(_dict, _vars=[], miss=[]):
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
            s = "_%s" % re.sub("\W+", "", key)
            if val["type"] == "dict":
                s = "ujson.dumps(%s)" % s
        else:
            s = "'%s'" % val["value"]
            if val["type"] == "dict":
                s = "ujson.dumps(%s)" % pformat(val["value"])
                #create variables in json
                for _var_in_json in variables_in_json:
                    s = s.replace("u'%s'" % _var_in_json, "%s" % _var_in_json)
        comment = " # missing in B" if key in miss else ""
        res += """
            '%s' : %s, %s""" % (key, s, comment)
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
 
        a_val = "'%s'" % vals[0]["value"]
        b_val = "'%s'" % vals[1]["value"]
        if vals[0]["type"] == "dict":
            a_val = pformat(vals[0]["value"])
            b_val = pformat(vals[1]["value"])
        data = (var_name, a_val, a_val, b_val)

        if len(a_val) < 80:
            res += """
        %s = %s
        #values: %s #VS %s
        """ % data
        else:
            res += """
        %s = %s
        #values:
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
    url = entry["url"]
    url_option = ""
    py = ""
    #get
    if len(entry["request"]["get"]) > 0:
        data = (print_vars(entry["compare_result"]["get_vars"]),
                print_dic(entry["request"]["get"], entry["compare_result"]["get_vars"], 
                          entry["compare_result"]["get_miss"]))
        py += """%s
        get_data = %s
        """ % data
        url_option = "+'?'+urllib.urlencode(get_data)"
    #post
    if len(entry["request"]["post"]) > 0:
        data = (print_vars(entry["compare_result"]["post_vars"]),
                print_dic(entry["request"]["post"], entry["compare_result"]["post_vars"],
                          entry["compare_result"]["post_miss"]))
        py += """%s
        post_data = %s
        g.setup(post=post_data)
        """ % data
    #payload
    if len(entry["request"]["payload"]) > 0:
        data = (print_vars(entry["compare_result"]["payload_vars"]),
                entry["request"]["payload"]["mimeType"],
                entry["request"]["payload"]["text"])#, entry["compare_result"]["payload_vars"]))
        py += """%s
        headers = {"Content-Type":"%s"}
        payload_data = %s
        g.setup(post=ujson.dumps(payload_data), headers=headers)
        """ % data
    py += """
        g.go('%s'%s)
        #self.save_file(filename="airline.html",path = "./", body=g.response.body)""" % (url, url_option)
    return py

"""
def diff_final_script():
    f = open("final.py", "r")
    lines = f.readlines("\n")
    changed_lines = []
    for line in lines:
        if line.strip().startwith("#REQ"):
            #start comparing next
            #WORK HERE
"""

def warning(*objs):
    print("WARNING: ", *objs, file=sys.stderr)

def help():
    print("""
    Create script from har file
    'har2python data1.har > script.py'

    Compare 2 same har files and create script with variables
    'har2python data1.har data2.har > script.py'

    Print out some debug info
    'har2python data1.har data2.har --debug'
""")

def main():
    #get list of entries 
    #(1 entry = http req(data, header, GET/POST data)+response(html/json content)) 
    #loaded from har file

    if len(sys.argv) < 2:
        help()
        exit(1)

    entries = parse_har(sys.argv[1])

    #if two files (same HAR files just with different values) on input, compare them
    #is used for create variables in code
    if len(sys.argv) >= 3:
        compare(entries)

    #prepare script content...
    py = ""
    try:
        py = open("%s%s" % (template_path, header_file), "rb").read()
        py = py.replace("code = \"\"","code = \"%s\""%sys.argv[1][0:2])
    except:
        pass
    make_req = True
    num = 0
    for entry in entries:
        #build request code
        if ((make_req or 
                (len(entry["request"]["get"]) > 0 or 
                len(entry["request"]["post"]) > 0 or
                len(entry["request"]["payload"]) > 0 or
                len(entry["response"]["cookies"]) > 0))): 
            py += """
        #REQ_NUM_%s""" % num
            #cookie info
            if len(entry["response"]["cookies"]) > 0:
                py += """
        #SETTING COOKIES"""
            py += make_request(entry)
            #response status
            py += """
        print g.response.code
"""
            num += 1 
        else:
            print(entry["url"])
            make_req = True

        #redirection
        if entry["response"]["status"][0] == "3":
            make_req = False
    try:
        py += open("%s%s" % (template_path, footer_file), 'rb').read()
        #...prepared
    except:
        pass

    if not debug:
        print(py)
    exit()

if __name__ == "__main__":
    main()
