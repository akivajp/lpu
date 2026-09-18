#!/usr/bin/env python

# Standard libraries
import argparse
import math
import multiprocessing
import os
import platform
import subprocess
import sys
import time

# Local libraries
from lpu.common import files
from lpu.common import progress
from lpu.common import logging
from lpu.common.config import Config

logger = logging.getColorLogger(__name__)

numCPUs = multiprocessing.cpu_count()
SLEEP_DURATION = 1.0

def getCurrentWorkerID():
    '''return an identifier unique to this host and process

    0.2.x used os.uname(), which does not exist on Windows.

    ホストとプロセスに対して一意な識別子を返す。
    0.2.x は Windows に存在しない os.uname() を使っていた。
    '''
    return f"{platform.node()}:{os.getpid()}"

def report(filepath, message):
    if os.path.exists(filepath):
        logger.info(f'Exists file or directory: {filepath}')
        return False
    else:
        logger.info(f'Reporting into file: {filepath}')
        with open(filepath, 'w', encoding='utf-8') as fobj:
            fobj.write(message)
        return True

def remove(f):
    if type(f) == str:
        logger.info(f'Removing file: {f}')
        os.remove(f)
    elif isinstance(f, files.FileType):
        logger.info(f'Removing file: {f.name}')
        f.close()
        os.remove(f.name)

def checkFile(filepath):
    if os.path.exists(filepath):
        logger.info(f'File already exists: {filepath}')
        return True
    else:
        return False

#def checkStage(tmpdir, basename, stage):
#def checkPhase(tmpdir, phase):
def checkPhase(conf, phase):
    tmpdir = conf.data.tmpdir
#    if checkFile('%s/__INIT__.%s.%s' % (tmpdir,stage,basename)):
    if checkFile(f'{tmpdir}/report.{phase}.begin'):
        return 'started'
#    elif checkFile('%s/__DONE__.%s.%s' % (tmpdir,stage,basename)):
    elif checkFile(f'{tmpdir}/report.{phase}.done'):
        return 'finished'
    else:
        return 'none'

def getPhaseCharge(conf, phase):
    tmpdir = conf.data.tmpdir
    #basename = conf.data.basename
    #path = '%(tmpdir)s/__INIT__.%(stage)s.%(basename)s' % locals()
    path = '{tmpdir}/report.{phase}.begin'.format(**locals())
    #return open(path, 'r').read()
    with open(path, encoding='utf-8') as fobj_charge:
        chargeID = fobj_charge.read()
    return chargeID

def checkPhaseCharge(conf, phase):
    if getPhaseCharge(conf,phase) != getCurrentWorkerID():
        logger.warning(f'Failed to confirm the responsible process of the phase: "{phase}"')
        return False
    return True

def reportInit(conf, phase):
    tmpdir = conf.data.tmpdir
    #basename = conf.data.basename
    #path = '%(tmpdir)s/__INIT__.%(stage)s.%(basename)s' % locals()
    path = '{tmpdir}/report.{phase}.begin'.format(**locals())
    #if not report(path, conf.data.hostproc):
    if not report(path, getCurrentWorkerID()):
        return False
    logger.info(f'Waiting {conf.data.interval} second to confirm the responsible process of the phase')
    time.sleep(conf.data.interval)
    return checkPhaseCharge(conf, phase)

def reportDone(conf, phase):
    tmpdir = conf.data.tmpdir
    #basename = conf.data.basename
    #return report('%(tmpdir)s/__DONE__.%(stage)s.%(basename)s'%locals(), conf.data.hostproc)
    return report('{tmpdir}/report.{phase}.done'.format(**locals()), getCurrentWorkerID())

def waitPhaseDone(conf, phase):
    tmpdir = conf.data.tmpdir
    #basename = conf.data.basename
    #return waitFile('%(tmpdir)s/__DONE__.%(stage)s.%(basename)s'%locals())
    #return wait_file('%(tmpdir)s/report.%(phase)s.done' % locals())
    return files.wait_file('{tmpdir}/report.{phase}.done'.format(**locals()))

def getInBuffer(conf):
    #bufname = '%s/__BUFFER__%s' % (tmpdir,hostproc)
    #bufname = '%(tmpdir)s/__BUFFER__%(hostproc)s' % conf
    # Config は ** 展開 (keys()) を持たないため、直接参照する
    bufname = f"{conf['tmpdir']}/tmp.buffer"
    #progCounter = progress.ProgressCounter(1, "buffering", force=True)
    with open(conf.data.inPath, encoding='utf-8') as inFile:
        inbuf = open(bufname, 'w+', encoding='utf-8')
        logger.info(f"Buffering into file: \"{inbuf.name}\"")
        lineCount = 0
        with progress.view(inFile, 'buffering') as p:
            for line in p:
                lineCount += 1
                inbuf.write(line)
    conf.data.lineCount = lineCount
    #progCounter.flush()
    logger.info(f"Lines: {lineCount}")
    inbuf.seek(0)
    return inbuf

def int2str(number, digits, suppress='0'):
    strNumber = str(number)
    lenNumber = len(strNumber)
    return suppress*(digits-lenNumber) + strNumber

def getSplitPrefix(conf):
    #return "%(tmpdir)s/%(basename)s" % conf
    # Config は ** 展開 (keys()) を持たないため、直接参照する
    return f"{conf['tmpdir']}/split"

def splitFile(conf):
    configFile = f"{conf.data.tmpdir}/config.json"
    if not reportInit(conf, 'split'):
        waitPhaseDone(conf, 'split')
        logger.debug(conf)
        logger.info(f"Updating the configuration with: {configFile}")
        conf.load_json(open(configFile).read(), False)
        logger.debug(conf)
        return True
    #threads = conf.require('threads')
    splitSize = conf.get('splitSize', None)
    numChunks = conf.get('numChunks', conf.data.threads)
    inbuf = getInBuffer(conf)
    lineCount = conf.data.lineCount
    if lineCount == 0:
        logger.info('Nothing to do')
        # runWorkers / concatFiles が参照するため、分割が無いことを記録する
        conf.data.numChunks = 0
        remove(inbuf)
        return
    #prefix = getPrefix(conf)
    #strSplitPrefix = conf.data.tmpdir + "/split"
    prefix = getSplitPrefix(conf)
    if not splitSize:
        #splitSize = int( math.ceil(float(lineCount) / threads) )
        splitSize = conf.data.splitSize = int( math.ceil(float(lineCount) / numChunks) )
        logger.info(f'Split size: {splitSize}')
    #splitCount = conf.data.splitCount = int(math.ceil(float(lineCount) / splitSize))
    #splitCount = int(math.ceil(float(lineCount) / splitSize))
    numChunks = conf.data.numChunks = int(math.ceil(float(lineCount) / splitSize))
    #digits = conf.data.digits = len(str(splitCount))
    digits = conf.data.digits = len(str(numChunks))
    logger.info(f'Splitting into: "{prefix}.*"')
    #progCounter = progress.ProgressCounter(1, "splitting", force=True, maxCount=lineCount)
    progInbuf = progress.FileReader(inbuf, "splitting")
    with inbuf:
        for fileNumber in range(1, numChunks+1):
            path = "{}.{}.in".format(prefix, int2str(fileNumber,digits,'0'))
            with open(path,'w') as outFile:
                for _ in range(0, splitSize):
                    line = progInbuf.readline()
                    #line = inbuf.readline()
                    if line:
                        outFile.write(line)
                    else:
                        break
    progInbuf.close()
    #progCounter.flush()
    logger.info('Finished to split')
    remove(inbuf)
    logger.info(f'Saving configuration into: {configFile}')
    with open(configFile, 'w') as fobj:
        fobj.write(conf.to_json(indent=4))
    reportDone(conf, 'split')
    return True

#def getFileNumberDigits(conf):
#    MAX_DIGITS=20
#    #prefix = getPrefix(conf)
#    for digits in range(1, MAX_DIGITS+1):
#        path = "%s.%s.in" % (prefix,int2str(1, digits, '0'))
#        if os.path.exists(path):
#            return digits
#    logging.alert("Failed to get file number digits")

def waitAvailableWorker(conf, workers, flush = False):
    threads = min(conf.data.threads, numCPUs)
    if flush:
        threads = 1
    if len(workers) == 0:
        return
    while True:
        for i, (proc,phase) in enumerate(workers):
            if proc.poll() != None:
                conf.data.processed += 1
                reportDone(conf,phase)
                workers.pop(i)
                break
        else:
            time.sleep(conf.data.interval)
        if len(workers) < threads:
            break
    processed = conf.data.processed
    numChunks = conf.data.numChunks
    ratio = float(processed) / numChunks
    strTemplate = "Processed files: %s / %s (%2.2f%%), Active processes: %s / %s"
    strMessage = strTemplate % (processed,numChunks,ratio*100,len(workers),threads)
    logger.info(strMessage)

def runWorkers(conf):
    #fileNumber = 1
    #prefix = getPrefix(conf)
    prefix = getSplitPrefix(conf)
    #digits = getFileNumberDigits(conf)
    numChunks = conf.data.numChunks
    digits = conf.data.digits = len(str(numChunks))
    #threads = min(conf.data.threads,numCPUs)
    workers = []
    conf.data.processed = 0
    for fileNumber in range(1, numChunks+1):
        strFileNumber = int2str(fileNumber, digits, '0')
        strPhase = f'cmd.{strFileNumber}'
        inPath = f"{prefix}.{strFileNumber}.in"
        outPath = f"{prefix}.{strFileNumber}.out"
        #cmdline = "%s < %s > %s" % (conf.data.command, inPath, outPath)
        cmdline = f'cat "{inPath}" | {conf.data.command} > "{outPath}"'
        waitAvailableWorker(conf, workers)
        if not reportInit(conf, strPhase):
            logger.info(f"Skipping processing: {inPath}")
            #if checkPhase(conf.data.tmpdir, strPhase) == 'finished':
            if checkPhase(conf, strPhase) == 'finished':
                conf.data.processed += 1
            continue
        proc = subprocess.Popen(cmdline, shell=True)
        workers.append([proc,strPhase])
        logger.info(f"Executing: {cmdline}")
        #logging.debug(p)
        #reportInit(conf, 'cmd.%s' % strFileNumber)
        fileNumber += 1
    waitAvailableWorker(conf, workers, flush=True)

def concatFiles(conf):
    if not reportInit(conf, 'concat'):
        waitPhaseDone(conf, 'concat')
        chargeID = getPhaseCharge(conf, 'concat')
        logger.info(f"Finalizing (concatenation) process is running: {chargeID}")
        return True
    prefix = getSplitPrefix(conf)
    numChunks = conf.data.numChunks
    lineCount = conf.data.lineCount
    digits = conf.data.digits = len(str(numChunks))
    #outPath = "%s.out" % (prefix)
    outPath = conf.data.outPath
    conf.data.processed = 0
    #progCounter = progress.ProgressCounter(1, "concat", force=True, maxCount=lineCount)
    progCounter = progress.SpeedCounter(header="concat", max_count=lineCount)
    for fileNumber in range(1, numChunks+1):
        strFileNumber = int2str(fileNumber, digits, '0')
        inPath = f"{prefix}.{strFileNumber}.out"
        #wait_file(inPath)
        files.wait_file(inPath)
        conf.data.processed += 1
    logger.info(f'Concatenating: "{prefix}.*" -> "{outPath}"')
    with open(outPath, 'w') as outFile:
        for fileNumber in range(1, numChunks+1):
            strFileNumber = int2str(fileNumber, digits, '0')
            inPath = f"{prefix}.{strFileNumber}.out"
            with open(inPath) as inFile:
                for line in inFile:
                    outFile.write(line)
                    progCounter.add(1, view=True)
    progCounter.reset()
    reportDone(conf, 'concat')

def checkConfig(conf):
    conf.setdefault('inPath',  '/dev/stdin')
    conf.data.inPath = os.path.abspath(conf.data.inPath)
    conf.setdefault('outPath', '/dev/stdout')
    conf.data.outPath = os.path.abspath(conf.data.outPath)
    #conf.setdefault('splitSize', None)
    conf.setdefault('interval', SLEEP_DURATION)
    conf.setdefault('threads', numCPUs)
    #conf.setdefault('numChunks', conf.data.threads)
    # 0 も検証対象にするため、真偽値ではなく None との比較で判定する
    if conf.get('numChunks', None) is not None:
        if conf.data.numChunks <= 0:
            strTemplate = "--chunks (number of splitted files) should be positive integer: %s"
            strMessage = strTemplate % (conf.data.numChunks)
            logger.error(strMessage)
            # 続行すると分割サイズの計算で ZeroDivisionError になるため中断する
            return False
    #conf.setdefault('basename', os.path.basename(conf.data.inPath))
    conf.setdefault('basename', os.path.basename(conf.data.outPath))
    conf.setdefault('tmpdir', f'./tmp-{conf.data.basename}')
    conf.data.tmpdir = os.path.abspath(conf.data.tmpdir)
    #if conf.data.threads > numCPUs:
    #    strTemplate = "Number of worker processes is limited to number of available threads: %s -> %s"
    #    strMessage = strTemplate % (conf.data.threads, numCPUs)
    #    logging.warn(strMessage)
    #    conf.data.threads = numCPUs
    return True

def execParallel(conf = None, **others):
    conf = Config(conf, **others)
    if not checkConfig(conf):
        return
    logger.debug(conf)
    #hostproc = conf.data.hostproc = getHostProcID()
    workerID = getCurrentWorkerID()
    files.safeMakeDirs(conf.data.tmpdir)
    logger.info(f"Worker ID (Host+Proc): \"{workerID}\"")
    splitFile(conf)
    runWorkers(conf)
    concatFiles(conf)

def cmdExecParallel(args):
    parser = argparse.ArgumentParser(description='Execute command in multiple processes by splitting the target file')
    #parser.add_argument('inFile', type=str, help='input file name for execution')
    #parser.add_argument('outFile', type=str, help='output file name for execution')
    parser.add_argument('command', type=str, help='command line string for execution, replacing %%1 and %%2 with input and output files respectively')
    parser.add_argument('--input',  '-I', dest='inPath', type=str, default='/dev/stdin',  help='path to input file for execution (default: /dev/stdin)')
    parser.add_argument('--output', '-O', dest='outPath', type=str, default='/dev/stdout', help='path to output file for execution (default: /dev/stdout)')
    #parser.add_argument('--digitsize', '-d', type=int, default=6, help='assign the number of digits in suffix of splitted files')
    parser.add_argument('--splitsize', '-s', dest='splitSize', type=int, default=None, help='assign the size (number of lines) of each splitted file')
    parser.add_argument('--chunks', '-c', dest='numChunks', type=int, default=None, help='assign the number of splitted files (default: same as --threads parameter)')
    parser.add_argument('--threads', '-n', type=int, default=None, help=f'assign the maximum number of worker processes (default: {numCPUs} in your computer')
    #parser.add_argument('--tmpdir', '-t', type=str, default='./tmp', help='assign the path of working directory')
    parser.add_argument('--tmpdir', '-t', type=str, default=None, help='assign the path of working directory (default: "./tmp-[basename]"')
    parser.add_argument('--verbose', '-v', action='store_true', help='verbosely print progressive messages')
    parser.add_argument('--interval', '-i', type=float, default=SLEEP_DURATION, help='sleep time duration for each confirmation (default: %(default)s)')
    parsed = parser.parse_args(args)
    #conf = Config(vars(parsed))
    conf = Config()
    conf.update(vars(parsed))
    logger.debug(conf)
    #execParallel(**vars(parsed))
    execParallel(conf)

def main():
    cmdExecParallel(sys.argv[1:])

if __name__ == '__main__':
    main()

