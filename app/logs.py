import time, datetime, re
import os

from file_read_backwards import FileReadBackwards
from flask_socketio import emit
from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer

from . import conf


class MyHandler(FileSystemEventHandler):
    def __init__(self, on_modified=None):
        if on_modified:
            self.on_modified = on_modified

    def on_modified(self, event):
        print(
            f'Watcher event, type: {event.event_type}  path : {event.src_path}'
        )


def watch(path, *args):
    event_handler = MyHandler(*args)
    observer = Observer()
    observer.schedule(event_handler, path, recursive=False)
    observer.start()


def isValidLogLine(line):
    return re.search(
        r"(19|20)[0-9]{2}[- /.](0[1-9]|1[012])[- /.](0[1-9]|[12][0-9]|3[01])\s+[0-9]{2}:[0-9]{2}:[0-9]{2}",
        line) is not None


def getDateFromLine(line):
    reres = re.search(
        r"((19|20)[0-9]{2}[- /.](0[1-9]|1[012])[- /.](0[1-9]|[12][0-9]|3[01])\s+[0-9]{2}:[0-9]{2}:[0-9]{2})(\.|\,)([0-9]{3})",
        line)
    if reres:
        date = reres[1]
        date_parsed = datetime.datetime.strptime(
            date, "%Y-%m-%d %H:%M:%S") + datetime.timedelta(
                milliseconds=int(reres[6]))
        return date_parsed


def getPeriodLog(path, lastNHour=24):
    now = datetime.datetime.now()
    last = now - datetime.timedelta(hours=lastNHour)
    with FileReadBackwards(path, encoding="utf-8") as frb:
        arr = []
        lastLine = ""
        lastValid = False
        while True:
            l = frb.readline()
            if lastLine:
                if lastValid:
                    date_parsed = getDateFromLine(lastLine)
                    if date_parsed and date_parsed > last:
                        arr.append(lastLine)
                        lastLine = l
                else:
                    lastLine = l + "\n" + lastLine
            else:
                lastLine = l
            lastValid = isValidLogLine(l)
            if not l:
                break

    return list(reversed(arr))


def mixLogs(logsA, logsB):
    mixed = logsA + logsB
    mixed.sort(key=lambda line: getDateFromLine(line))
    return mixed


def splitLogs(text):
    splited = text.split("\n")
    arr = []
    lastLine = ""
    for s in splited:
        if isValidLogLine(s):
            if lastLine:
                arr.append(lastLine)
                lastLine = s
            else:
                lastLine = s
        else:
            if lastLine:
                lastLine += '\n' + s
            else:
                lastLine = s
    return arr


def watchLogs():
    fz = open(conf.zeronetLogFile)
    fs = open(conf.spiderLogFile)

    fz.seek(0, os.SEEK_END)
    fs.seek(0, os.SEEK_END)

    def readMore(e):
        more = None
        if e.src_path == conf.zeronetLogFile:
            more = fz.read()
        elif e.src_path == conf.spiderLogFile:
            more = fs.read()
        if more is not None:
            emit("addLogs", splitLogs(more))

    emit(
        "addLogs",
        mixLogs(
            getPeriodLog(conf.zeronetLogFile, 0.1),
            getPeriodLog(conf.spiderLogFile, 0.1)))

    watch(conf.zeronetLogs, readMore)
    watch(conf.spiderLogs, readMore)


def countLog(logType, lastNHour=24):
    hslogs = getPeriodLog(conf.spiderLogFile, lastNHour)
    filtered = list(filter(lambda x: logType in x, hslogs))
    return filtered