import requests, os, urllib3, re, base64
from json import loads
from time import sleep
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
# Alteon credentials
AlteonMgmt = ''
AlteonUname = ''
AlteonPasswd = ''
AlteonCreds = base64.b64encode(f'{AlteonUname}:{AlteonPasswd}'.encode('ascii')).decode('ascii')

headers = { 'Authorization': f'Basic {AlteonCreds}', 'Content-Type': 'text/plain;charset=UTF-8' }
out = open("Apply_test_result.txt", "w+")
def test_script(data, name):
    if "/" in name:
        name = name.split("/")[-1]
    while True:
        r=requests.post(f"https://{AlteonMgmt}/config?action=revert", headers=headers, verify=False)
        if loads(r.text)["status"] == "ok":
            break
        sleep(1)

    while True:
        r=requests.post(f"https://{AlteonMgmt}/config/appshapeimport?id={name}&state=1", data=data, headers=headers, verify=False)
        if loads(r.text)["status"] == "ok":
            break
        sleep(1)
    
    while True:
        r=requests.post(f"https://{AlteonMgmt}/config?action=apply", headers=headers, verify=False)
        if loads(r.text)["status"] == "ok":
            break
        sleep(1)
        
    while True:
        r=requests.get(f"https://{AlteonMgmt}/config?prop=agApplyConfig", headers=headers, verify=False)
        code = loads(r.text)["agApplyConfig"]
        if code == 4:
            while True:
                r=requests.delete(f"https://{AlteonMgmt}/config/SlbNewCfgAppShapeTable/{name}/", headers=headers, data={}, verify=False)
                if loads(r.text)["status"] == "ok":
                    break
                sleep(1)

            while True:
                r=requests.post(f"https://{AlteonMgmt}/config?action=apply", headers=headers, verify=False)
                if loads(r.text)["status"] == "ok":
                    break
                sleep(1)

            while True:
                r = requests.get(f"https://{AlteonMgmt}/config?prop=agApplyConfig", headers=headers, verify=False)
                code = loads(r.text)["agApplyConfig"]
                if code == 3:
                    sleep(1)
                elif code == 4:
                    return "Apply Successfull!"
                else:
                    return f"encountered an error! apply got response code {code}"

        elif code == 5:
            r = requests.get(f"https://{AlteonMgmt}/config/AgApplyTable?", headers=headers, verify=False)
            try:
                while True:
                    r1 = requests.post(f"https://{AlteonMgmt}/config?action=revert", headers=headers, verify=False)
                    if loads(r1.text)["status"] == "ok":
                        break
                    sleep(1)
                
                return loads(r.text)["AgApplyTable"][0]["StringVal"]
            except Exception as e:
                print(e, loads(r.text))
        sleep(1)

def replacer(old, new, string):
    tmp = string
    while re.search(old, tmp):
        tmp = re.sub(old, new, tmp)
    return tmp

for item in os.listdir("Original"):
    
    res = ""
    tmp = ""
    with open(os.path.join("Original", item)) as f:
        data = f.read().splitlines()
    name = data[0].split()[2]
    # remove comments
    data = "\n".join([ line for line in data[1:-1] if not re.match(r'^(\s)*#', line) and len(line)>0])
    # Add space between curly brackets
    data = data.replace('}{', '} {')
    
    # Correct clock command syntax
    data = data.replace("clock clicks -milliseconds", "clock milliseconds")
    
    # Correct log command syntax
    data = replacer(r'log local\d.[^ ]* ', r'log -a 7 ', data)

    # Adjust curly brackets blocks opennings
    data = replacer(r'\n\s*{\s*\n', r'{\n', data)

    # Replace Node command to Host command
    data = replacer(r'\n(\s*)node', r'\n\1host', data)

    # Correct "HTTP::Cookie" syntax
    data = replacer(r'\[HTTP::cookie ([^\s\\]*)\]', r'[HTTP::cookie value \1]', data)

    # Adjust if and loop conditions 
    data = replacer(r'{(.*)?not ([^(\n]*)}', r'{\1! (\2)}', data)
    data = replacer(r'{(.*)?not ([\s\S]*?)}', r'{\1! \2}', data)
    data = replacer(r'{(.*)? and (.*)}', r'{\1 && \2}', data)
    data = replacer(r'{(.*)? or (.*)}', r'{\1 || \2}', data)

    # change persist "uie" to "usid"
    data = replacer(r'([\t ])*persist(.*)? uie', r'\1persist\2 usid', data)

    # remove "noserver" argument from "HTTP::respond" command
    data = replacer(r'(HTTP::respond)([\s\S]*?)noserver', r'\1\2', data)

    # remove priority from events
    data = replacer(r'when ([A-Z]+_[A-Z]+) (priority \d+) {', r'when \1 {', data)

    # replace "use pool" with "group" command
    data = replacer(r'(\n\s*)use pool ([^\s])', r'\1group select \2', data)
    
    # replace "getfield" and "findstr" commands with AS syntax
    cfg = ""
    for line in data.splitlines():
        if "getfield" in line or "findstr" in line:
            l=list()
            c=0
            while "[" in line:
                s_idx=line.rfind("[")
                e_idx=line[s_idx:].index("]")+s_idx+1
                l.append(line[s_idx:e_idx])
                line=line.replace(line[s_idx:e_idx], f'##l{c}##')
                c+=1
            l.append(line)
            length = len(l)-1
            idx=0
            for y in l:
                if "getfield" in y:
                    x=y.split()
                    cmd=f'[lindex [split {x[1]} {x[2]}] {x[3]}]'
                    break
                elif "findstr" in y:
                    x=y.split()
                    if len(x)==3:
                        cmd=f'[string range {x[1]} [string first {x[2]} {x[1]}] end]'
                    elif len(x)==4:
                        cmd=f'[string range {x[1]} [expr {{[string first {x[2]} {x[1]}] + {x[3]} }} end]'
                    elif len(x)==5:
                        cmd=f'[string range {x[1]} [expr {{[string first {x[2]} {x[1]}] + {x[3]} }}] [string first {x[4].replace("]","")} [string range {x[1]} [expr {{[string first {x[2]} {x[1]}] + {x[3]} }}] end]]]'
                    break
                idx+=1
            tbd=[]
            l[idx]=cmd
            while "##l" in " ".join(l):
                idx=0
                for x in l:
                    for y in x.split():
                        while y[-1]==']':
                            y=y[:-1]
                        while re.search(r'\#\#l\d+\#\#', y):
                            i = re.search(r'\#\#l(\d+)\#\#', y)
                            x = x.replace(i.group(0), l[int(i.group(1))])
                            y = y.replace(i.group(0), "")
                            if not int(i.group(1)) in tbd:
                                tbd.append(int(i.group(1)))
                    l[idx] = x
                    idx+=1
                for i in sorted(tbd, reverse=True):
                    try:
                        l.pop(i)
                    except Exception as e:
                        pass
                tbd.clear()
            l.reverse()
            line=" ".join(l)
        cfg+=line+"\n"
    
    # add AS closing statement
    data=cfg+"\n-----END"
    res = test_script(data, name)
    if res == "Apply Successfull!":
        out.write(f"Testing script: {name}, result = {res}\n")
        try:
            with open(os.path.join("Successful", name+".txt"), 'w') as newFile:
                newFile.write(data)
            os.rename(os.path.join("Original", item), os.path.join("OK", name+".txt"))
        except Exception as e:
            print(f'Failure in success proccess, got the following error: {e}')
    else:
        try:
            os.rename(os.path.join("Original", item), os.path.join("Failed", name+".txt"))
        except Exception as e:
            print(f'Failure in failure proccess, got the following error: {e}')
        err = open(os.path.join("Errors", item+"_error.log"), "w")
        failed_cmd=re.search(r"invalid command name\s+([^\s]+)", res)
        if failed_cmd and failed_cmd.group(1):
            err.write(f"Finished testing script: '{name}', Encountered an unsupported command {failed_cmd.group(1)}\n,full result:\n{res}\n, tested script was:\n{data}")
            out.write(f"Finished testing script: '{name}', Encountered an unsupported command '{failed_cmd.group(1)}'\n")
        else:
            err.write(f"Finished testing script: '{name}', result = {res}\n, uploaded script=\n{data}")
            out.write(f"Finished testing script: '{name}', result = {res}\n")
        err.close()
