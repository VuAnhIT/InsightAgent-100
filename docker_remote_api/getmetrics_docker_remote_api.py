#!/bin/python
import subprocess
import os
from optparse import OptionParser
import linecache
import json
import time
import datetime
import socket
import sys

usage = "Usage: %prog [options]"
parser = OptionParser(usage=usage)
parser.add_option("-d", "--directory",
    action="store", dest="homepath", help="Directory to run from")
(options, args) = parser.parse_args()
date = time.strftime("%Y%m%d")
hostname=socket.gethostname().partition(".")[0]

if options.homepath is None:
    homepath = os.getcwd()
else:
    homepath = options.homepath
datadir = 'data/'

newInstanceAvailable = False

def listtocsv(lists):
    finallog = ''
    for i in range(0,len(lists)):
        finallog = finallog + str(lists[i])
        if(i+1 != len(lists)):
            finallog = finallog + ','
    if finallog != "":
        csvFile.write("%s\n"%(finallog))

def getindex(colName):
    if colName == "CPU":
        return 4001
    elif colName == "DiskRead" or colName == "DiskWrite":
        return 4002
    elif colName == "NetworkIn" or colName == "NetworkOut":
        return 4003
    elif colName == "MemUsed":
        return 4004
    elif "InOctets" in colName or "OutOctets" in colName:
        return 4005
    elif "InDiscards" in colName or "OutDiscards" in colName:
        return 4006
    elif "InErrors" in colName or "OutErrors" in colName:
        return 4007
    elif colName == "SwapUsed" or colName == "SwapTotal":
        return 4008

metricResults = {}
def toJson (header, values):
    global metricResults
    if header == "" or values == "":
        return
    headerFields = header.split(",")
    valueFields = values.split(",")
    for i in range(0,len(headerFields)):
        metricResults[headerFields[i]] = valueFields[i]

def updateResults():
    print "In Function updateResults()" 
    global metricResults
    if not metricResults:
        return
    with open(os.path.join(homepath,datadir+"previous_results.json"),'w') as f:
        json.dump(metricResults,f)

def initPreviousResults():
    print "In Function initPreviousResults()" 
    global numlines
    global date
    global hostname

    log = ''
    fieldnames = ''
    for i in range(len(dockers)-1):
        try:
            filename = "stat%s.txt"%dockers[i]
            statsFile = open(os.path.join(homepath,datadir+filename),'r')
            data = statsFile.readlines()
        except IOError as e:
            print "I/O error({0}): {1}: {2}".format(e.errno, e.strerror, e.filename)
            continue
        finally:
            statsFile.close()

        for eachline in data:
            if isJson(eachline) == True:
                metricData = json.loads(eachline)
                break
        #Generating the header line for the data file
        if(numlines < 1):
            fields = ["timestamp","CPU","DiskRead","DiskWrite","NetworkIn","NetworkOut","MemUsed","SwapTotal","SwapUsed"]
            if i == 0:
                fieldnames = fields[0]
            host = dockers[i]
            for j in range(1,len(fields)):
                if(fieldnames != ""):
                    fieldnames = fieldnames + ","
                groupid = getindex(fields[j])
                nextfield = fields[j] + "[" +host+"_"+hostname+"]"+":"+str(groupid)
                fieldnames = fieldnames + nextfield
        else:
            fieldnames = linecache.getline(os.path.join(homepath,datadir+date+".csv"),1)
        timestamp = metricData['read'][:19]
        timestamp =  int(time.mktime(datetime.datetime.strptime(timestamp, "%Y-%m-%dT%H:%M:%S").timetuple())*1000)

        try:
            networkInterfaceMetrics = []
            if 'network' in metricData or 'networks' in metricData:
                networkRx = round(float(float(metricData['network']['rx_bytes'])/(1024*1024)),4) #MB
                networkTx = round(float(float(metricData['network']['tx_bytes'])/(1024*1024)),4) #MB
            else:
                networkRx = 0
                networkTx = 0
        except KeyError,e:
            try:
                networkMetrics = metricData['networks']
                networkRx = 0
                networkTx = 0
                for key in networkMetrics:
                    # Append New Field Headers for specific Interface
                    if (numlines < 1 or newInstanceAvailable == True):
                        nextfield = "InOctets-" + key + "[" + host + "_" + hostname + "]" + ":" + str(
                            getindex("InOctets"))
                        fieldnames = fieldnames + "," + nextfield
                        nextfield = "OutOctets-" + key + "[" + host + "_" + hostname + "]" + ":" + str(
                            getindex("OutOctets"))
                        fieldnames = fieldnames + "," + nextfield
                        nextfield = "InDiscards-" + key + "[" + host + "_" + hostname + "]" + ":" + str(
                            getindex("InDiscards"))
                        fieldnames = fieldnames + "," + nextfield
                        nextfield = "OutDiscards-" + key + "[" + host + "_" + hostname + "]" + ":" + str(
                            getindex("OutDiscards"))
                        fieldnames = fieldnames + "," + nextfield
                        nextfield = "InErrors-" + key + "[" + host + "_" + hostname + "]" + ":" + str(
                            getindex("InErrors"))
                        fieldnames = fieldnames + "," + nextfield
                        nextfield = "OutErrors-" + key + "[" + host + "_" + hostname + "]" + ":" + str(
                            getindex("OutErrors"))
                        fieldnames = fieldnames + "," + nextfield

                    metricVal = float(networkMetrics[key]['rx_bytes'])
                    networkInterfaceMetrics.append(round(float(metricVal / (1024 * 1024)), 4))
                    metricVal = float(networkMetrics[key]['tx_bytes'])
                    networkInterfaceMetrics.append(round(float(metricVal / (1024 * 1024)), 4))
                    metricVal = float(networkMetrics[key]['rx_dropped'])
                    networkInterfaceMetrics.append(round(float(metricVal / (1024 * 1024)), 4))
                    metricVal = float(networkMetrics[key]['tx_dropped'])
                    networkInterfaceMetrics.append(round(float(metricVal / (1024 * 1024)), 4))
                    metricVal = float(networkMetrics[key]['rx_errors'])
                    networkInterfaceMetrics.append(round(float(metricVal / (1024 * 1024)), 4))
                    metricVal = float(networkMetrics[key]['tx_errors'])
                    networkInterfaceMetrics.append(round(float(metricVal / (1024 * 1024)), 4))
                    #Adding up values for all interfaces to get the total
                    networkRx += float(networkMetrics[key]['rx_bytes'])
                    networkTx += float(networkMetrics[key]['tx_bytes'])
                networkRx = round(float(networkRx/(1024*1024)),4) #MB
                networkTx = round(float(networkTx/(1024*1024)),4) #MB
            except KeyError, e:
                print "Couldn't fetch network information for container: " + dockers[i]
                networkRx = "NaN"
                networkTx = "NaN"
        try:
            cpu = round(float(metricData['cpu_stats']['cpu_usage']['total_usage'])/10000000,4) #Convert nanoseconds to jiffies
        except KeyError, e:
            print "Couldn't fetch cpu information for container: " + dockers[i]
            cpu = "NaN"
        try:
            memUsed = round(float(float(metricData['memory_stats']['usage'])/(1024*1024)),4) #MB
        except KeyError, e:
            print "Couldn't fetch memory information for container: " + dockers[i]
            memUsed = "NaN"
        try:
            if len(metricData['blkio_stats']['io_service_bytes_recursive']) == 0:
                diskRead = "NaN"
                diskWrite = "NaN"
            else:
                diskRead = round(float(float(metricData['blkio_stats']['io_service_bytes_recursive'][0]['value'])/(1024*1024)),4) #MB
                diskWrite = round(float(float(metricData['blkio_stats']['io_service_bytes_recursive'][1]['value'])/(1024*1024)),4) #MB
        except (KeyError, IndexError) as e:
            print "Couldn't fetch disk information for container: " + dockers[i]
            diskRead = "NaN"
            diskWrite = "NaN"
        try:
            swapTotal = round(float(float(metricData['memory_stats']['stats']['total_swap'])/(1024*1024)),4) #MB
            swapUsed = round(float(float(metricData['memory_stats']['stats']['swap'])/(1024*1024)),4) #MB
        except KeyError, e:
            print "Couldn't fetch swap information for container: " + dockerInstances[i]
            swapUsed = "NaN"
            swapTotal = "NaN"
        if i == 0:
            log = log + str(timestamp)
        log = log + "," + str(cpu) + "," + str(diskRead) + "," + str(diskWrite) + "," + str(networkRx) + "," + str(networkTx) + "," + str(memUsed) + "," + str(swapTotal)+ "," + str(swapUsed)
        if networkInterfaceMetrics:
            log = log + "," + ",".join(map(str, networkInterfaceMetrics))
    toJson(fieldnames,log)
    updateResults()
    time.sleep(1)
    proc = subprocess.Popen([os.path.join(homepath,datadir+"getmetrics_docker.sh")], cwd=homepath, stdout=subprocess.PIPE, shell=True)
    (out,err) = proc.communicate()


def getPreviousResults():
    print "In Function getPreviousResults()" 
    with open(os.path.join(homepath,datadir+"previous_results.json"),'r') as f:
        return json.load(f)

def isJson(jsonString):
    print "In Function isJson()" 
    try:
        jsonObject = json.loads(jsonString)
        if jsonObject['read'] != "":
            return True
    except ValueError, e:
        return False
    except TypeError, e:
        return False
    return False

def checkDelta(fd):
    print "In Function checkDelta()" 
    deltaFields = ["CPU", "DiskRead", "DiskWrite", "NetworkIn", "NetworkOut","InOctets", "OutOctets", "InErrors", "OutErrors", "InDiscards", "OutDiscards"]
    for eachfield in deltaFields:
        if(eachfield == fd or fd.startswith(eachfield)):
            return True
    return False

precpu={}
def calculateDelta():
    print "In Function calculateDelta()" 
    global fieldnames
    global metricResults
    finallogList = []
    if fieldnames == "":
        return finallogList
    fieldsList = fieldnames.split(",")
    previousResult = getPreviousResults()
    currentResult = metricResults
    for key in fieldsList:
        if((key.split('[')[0]) == "CPU"):
            if  key not in precpu:
                deltaValue = "NaN"
                finallogList.append(deltaValue)
                continue
            previousCPU = precpu[key]
            if str(currentResult[key]) == "NaN" or str(previousCPU) == "NaN":
                deltaValue = "NaN"
            else:
                deltaValue =  round((float(currentResult[key]) - float(previousCPU)),4)
                if deltaValue < 0:
                    deltaValue = 0
            finallogList.append(deltaValue)
        elif(checkDelta(key.split('[')[0]) == True):
            if key not in currentResult or key not in previousResult:
                deltaValue = "NaN"
            elif str(currentResult[key]) == "NaN" or str(previousResult[key]) == "NaN":
                deltaValue = "NaN"
            else:
                deltaValue = float(currentResult[key]) - float(previousResult[key])
                if deltaValue < 0:
                    deltaValue = 0
            finallogList.append(deltaValue)
        else:
            if key not in currentResult:
                currentValue = "NaN"
                finallogList.append(currentValue)
            else:
                finallogList.append(currentResult[key])
    return finallogList

def removeStatFiles():
    print "In Function removeStatFiles()" 
    global dockerInstances
    for i in range(len(dockerInstances)):
        statfile = "stat%s.txt"%dockerInstances[i]
        if os.path.isfile(os.path.join(homepath,datadir+statfile)) == True:
            os.remove(os.path.join(homepath,datadir+statfile))

dockerInstances = []
def update_docker():
    print "In Function update_docker()" 
    global dockers
    global newInstanceAvailable
    global dockerInstances
    proc = subprocess.Popen(["docker ps | awk '{if(NR!=1) print $1}'"], stdout=subprocess.PIPE, shell=True)
    (out, err) = proc.communicate()
    dockers = out.split("\n")
    cronfile = open(os.path.join(homepath,datadir+"getmetrics_docker.sh"),'w')
    cronfile.write("#!/bin/bash\nDATADIR='data/'\ncd $DATADIR\n")
    cronfile.write("now=$(date +%M)\n")
    containerCount = 0
    for container in dockers:
        if container == "":
            continue
        containerCount+=1
        command = "echo -e \"GET /containers/"+container+"/stats?stream=0 HTTP/1.1\\r\\nHost: localhost\\r\\n\" | nc -U -i 10 /var/run/docker.sock > stat"+container+".txt & PID"+str(containerCount)+"=$!"
        cronfile.write(command+"\n")
    for i in range(1,containerCount+1):
        cronfile.write("wait $PID"+str(i)+"\n")
    cronfile.write(
        "if [ $now -eq \"00\" ] || [ $now -eq \"15\" ] || [ $now -eq \"30\" ] || [ $now -eq \"45\" ];\nthen\n")
    for container in dockers:
        if container == "":
            continue
        command = "    cat stat" + container + ".txt > stat" + container + "_backup.txt\n"
        cronfile.write(command)
    cronfile.write("else\n")
    for container in dockers:
        if container == "":
            continue
        command = "    cat stat" + container + ".txt >> stat" + container + "_backup.txt\n"
        cronfile.write(command)
    cronfile.write("fi\n")
    cronfile.close()
    os.chmod(os.path.join(homepath,datadir+"getmetrics_docker.sh"),0755)
    if os.path.isfile(os.path.join(homepath,datadir+"totalInstances.json")) == False:
        towritePreviousInstances = {}
        for containers in dockers:
            if containers != "":
                dockerInstances.append(containers)
        towritePreviousInstances["overallDockerInstances"] = dockerInstances
        with open(os.path.join(homepath,datadir+"totalInstances.json"),'w') as f:
            json.dump(towritePreviousInstances,f)
    else:
        with open(os.path.join(homepath,datadir+"totalInstances.json"),'r') as f:
            dockerInstances = json.load(f)["overallDockerInstances"]
    dockers = filter(None, dockers)
    for eachDocker in dockers:
        print ("Searching for",eachDocker)
        if eachDocker not in dockerInstances:
            newInstanceAvailable = True
    if newInstanceAvailable or (len(dockers) != len(dockerInstances)):
        newInstanceAvailable = True
        print ("Making the call to the server for update instance information.",len(dockers),len(dockerInstances))
        writeInsatanceFile("currentInstances", dockers)
        writeInsatanceFile("previousInstances", dockerInstances)
        towritePreviousInstances = {}
        towritePreviousInstances["overallDockerInstances"] = dockers
        dockerInstances = dockers
        with open(os.path.join(homepath,datadir+"totalInstances.json"),'w') as f:
            json.dump(towritePreviousInstances,f)

def writeInsatanceFile(filename, instanceList):
    global hostname
    jsonData = {}
    print "In Function writeInsatanceFile()"
    print instanceList
    newInstanceList = []
    for index in range(len(instanceList)):
        newInstanceList.append(instanceList[index] + "_" + hostname)
    jsonData["instanceList"] = newInstanceList
    with open(os.path.join(homepath, datadir + filename + ".json"), 'w') as f:
        json.dump(jsonData, f)

metricData = {}
def getmetrics():
    print "In Function getmetrics()" 
    global dockerInstances
    global numlines
    global date
    global fieldnames
    global csvFile
    global hostname
    global newInstanceAvailable
    timestampAvailable = False
    global metricData
    try:
        while True:
            fields = ["timestamp","CPU","DiskRead","DiskWrite","NetworkIn","NetworkOut","MemUsed","SwapTotal","SwapUsed"]
            if newInstanceAvailable == True:
                oldFile = os.path.join(homepath,datadir+date+".csv")
                newFile = os.path.join(homepath,datadir+date+"."+time.strftime("%Y%m%d%H%M%S")+".csv")
                os.rename(oldFile,newFile)
            csvFile = open(os.path.join(homepath,datadir+date+".csv"), 'a+')
            numlines = len(csvFile.readlines())
            if(os.path.isfile(homepath+"/"+datadir+"previous_results.json") == False):
                initPreviousResults()
            log = ''
            fieldnames = ''
            for i in range(len(dockerInstances)):
                try:
                    filename = "stat%s.txt"%dockerInstances[i]
                    if os.path.isfile(os.path.join(homepath,datadir+filename)) == False:
                        for fieldIndex in range(1,len(fields)):
                            if(log != ""):
                                log = log + ","
                            log = log + "NaN"
                        continue
                    else:
                        try:
                            statsFile = open(os.path.join(homepath,datadir+filename),'r')
                        finally:
                            statsFile.close()
                except IOError as e:
                    print "I/O error({0}): {1}: {2}".format(e.errno, e.strerror, e.filename)
                    continue
                data = statsFile.readlines()
                jsonAvailable = False
                for eachline in data:
                    if isJson(eachline) == True:
                        metricData = json.loads(eachline)
                        jsonAvailable = True
                        break
                if(numlines < 1 or newInstanceAvailable == True):
                    if i == 0:
                        fieldnames = fields[0]
                    host = dockerInstances[i]
                    for j in range(1,len(fields)):
                        if(fieldnames != ""):
                            fieldnames = fieldnames + ","
                        groupid = getindex(fields[j])
                        #Creating the header/first line for the data file
                        nextfield = fields[j] + "[" +host+"_"+hostname+"]"+":"+str(groupid)
                        fieldnames = fieldnames + nextfield
                else:
                    fieldnames = linecache.getline(os.path.join(homepath,datadir+date+".csv"),1).rstrip("\n")
                #File available but stat file doesn't have json object
                if jsonAvailable == False:
                    for fieldIndex in range(1,len(fields)):
                        if(log != ""):
                            log = log + ","
                        log = log + "NaN"
                    continue
                timestamp = metricData['read'][:19]
                timestamp =  int(time.mktime(datetime.datetime.strptime(timestamp, "%Y-%m-%dT%H:%M:%S").timetuple())*1000)
                try:
                    networkInterfaceMetrics = []
                    if "network" in metricData or "networks" in metricData:
                        networkRx = round(float(float(metricData['network']['rx_bytes'])/(1024*1024)),4) #MB
                        networkTx = round(float(float(metricData['network']['tx_bytes'])/(1024*1024)),4) #MB
                    else:
                        networkRx = 0
                        networkTx = 0
                except KeyError,e:
                    try:
                        networkMetrics = metricData['networks']
                        networkRx = 0
                        networkTx = 0
                        for key in networkMetrics:
                            #Append New Field Headers for specific Interface
                            if (numlines < 1 or newInstanceAvailable == True):
                                nextfield = "InOctets-" +key+ "[" +host+"_"+hostname+"]"+":"+str(getindex("InOctets"))
                                fieldnames = fieldnames + "," + nextfield
                                nextfield = "OutOctets-" + key + "[" + host + "_" + hostname + "]" + ":" + str(
                                getindex("OutOctets"))
                                fieldnames = fieldnames + "," + nextfield
                                nextfield = "InDiscards-" + key + "[" + host + "_" + hostname + "]" + ":" + str(
                                getindex("InDiscards"))
                                fieldnames = fieldnames + "," + nextfield
                                nextfield = "OutDiscards-" + key + "[" + host + "_" + hostname + "]" + ":" + str(
                                getindex("OutDiscards"))
                                fieldnames = fieldnames + "," + nextfield
                                nextfield = "InErrors-" + key + "[" + host + "_" + hostname + "]" + ":" + str(
                                getindex("InErrors"))
                                fieldnames = fieldnames + "," + nextfield
                                nextfield = "OutErrors-" + key + "[" + host + "_" + hostname + "]" + ":" + str(
                                getindex("OutErrors"))
                                fieldnames = fieldnames + "," + nextfield

                            metricVal = float(networkMetrics[key]['rx_bytes'])
                            networkInterfaceMetrics.append(round(float(metricVal/(1024*1024)),4))
                            metricVal = float(networkMetrics[key]['tx_bytes'])
                            networkInterfaceMetrics.append(round(float(metricVal/(1024*1024)),4))
                            metricVal = float(networkMetrics[key]['rx_dropped'])
                            networkInterfaceMetrics.append(round(float(metricVal/(1024*1024)),4))
                            metricVal = float(networkMetrics[key]['tx_dropped'])
                            networkInterfaceMetrics.append(round(float(metricVal/(1024*1024)),4))
                            metricVal = float(networkMetrics[key]['rx_errors'])
                            networkInterfaceMetrics.append(round(float(metricVal/(1024*1024)),4))
                            metricVal = float(networkMetrics[key]['tx_errors'])
                            networkInterfaceMetrics.append(round(float(metricVal/(1024*1024)),4))
                            #Adding up values for all interfaces to get the total
                            networkRx += float(networkMetrics[key]['rx_bytes'])
                            networkTx += float(networkMetrics[key]['tx_bytes'])

                        networkRx = round(float(networkRx/(1024*1024)),4) #MB
                        networkTx = round(float(networkTx/(1024*1024)),4) #MB
                    except KeyError, e:
                        print "Couldn't fetch network information for container: " + dockerInstances[i]
                        networkRx = "NaN"
                        networkTx = "NaN"
                try:
                    cpu = round(float(metricData['cpu_stats']['cpu_usage']['total_usage'])/10000000,4) #Convert nanoseconds to jiffies
                    precpu["CPU["+dockerInstances[i]+"_"+hostname+"]"+":"+str(4001)] = round(float(metricData['precpu_stats']['cpu_usage']['total_usage'])/10000000,4)
                except KeyError, e:
                    print "Couldn't fetch cpu information for container: " + dockerInstances[i]
                    cpu = "NaN"
                    precpu["CPU["+dockerInstances[i]+"_"+hostname+"]"+":"+str(4001)] = "NaN"
                try:
                    memUsed = round(float(float(metricData['memory_stats']['usage'])/(1024*1024)),4) #MB
                except KeyError, e:
                    print "Couldn't fetch memory information for container: " + dockerInstances[i]
                    memUsed = "NaN"
                try:
                    if len(metricData['blkio_stats']['io_service_bytes_recursive']) == 0:
                        diskRead = "NaN"
                        diskWrite = "NaN"
                    else:
                        diskRead = round(float(float(metricData['blkio_stats']['io_service_bytes_recursive'][0]['value'])/(1024*1024)),4) #MB
                        diskWrite = round(float(float(metricData['blkio_stats']['io_service_bytes_recursive'][1]['value'])/(1024*1024)),4) #MB
                except (KeyError, IndexError) as e:
                    print "Couldn't fetch disk information for container: " + dockerInstances[i]
                    diskRead = "NaN"
                    diskWrite = "NaN"
                #Adding Swap Metrics
                try:
                    swapTotal = round(float(float(metricData['memory_stats']['stats']['total_swap'])/(1024*1024)),4) #MB
                    swapUsed = round(float(float(metricData['memory_stats']['stats']['swap'])/(1024*1024)),4) #MB
                except KeyError, e:
                    print "Couldn't fetch swap information for container: " + dockerInstances[i]
                    swapUsed = "NaN"
                    swapTotal = "NaN"

                if timestampAvailable == False:
                    if log == "":
                        log = str(timestamp)
                    else:
                        log = str(timestamp) + "," + log
                    timestampAvailable = True
                log = log + "," + str(cpu) + "," + str(diskRead) + "," + str(diskWrite) + "," + str(networkRx) + "," + str(networkTx) + "," + str(memUsed) +  "," + str(swapTotal)+  "," + str(swapUsed)
                if networkInterfaceMetrics:
                    log = log + "," + ",".join(map(str, networkInterfaceMetrics))
            if timestampAvailable == False and fieldnames != "":
                log = "NaN" + "," + log
                csvFile.close()
                sys.exit()
            toJson(fieldnames,log)
            deltaList = calculateDelta()
            updateResults()
            #Writing the fieldnames header in the csv file
            if numlines < 1 or newInstanceAvailable == True:
                if fieldnames != "":
                    csvFile.write("%s\n"%(fieldnames))
            listtocsv(deltaList)
            csvFile.flush()
            csvFile.close()
            break
    except KeyboardInterrupt:
        print "Keyboard Interrupt"

try:
    update_docker()
    proc = subprocess.Popen([os.path.join(homepath,datadir+"getmetrics_docker.sh")], cwd=homepath, stdout=subprocess.PIPE, shell=True)
    (out,err) = proc.communicate()
    getmetrics()
    removeStatFiles()
except KeyboardInterrupt:
    print "Interrupt from keyboard"
