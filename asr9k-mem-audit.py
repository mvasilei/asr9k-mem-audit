#! /usr/bin/env python
from datetime import datetime, timedelta
import subprocess, re, signal, sys, xlsxwriter, time
import multiprocessing as mp

def signal_handler(sig, frame):
    print('Exiting gracefully Ctrl-C detected...')
    sys.exit(0)

def send_command(name, command):
    response = subprocess.Popen(['rcomauto ' + name.strip() + ' "' + command + '"'],
                                stdout=subprocess.PIPE,
                                shell=True)

    if response.returncode == None:
        return name.strip() + ":\r\n" + response.communicate()[0]
    else:
        print 'An error occurred', response.returncode

def command_set(name, xlsq):
    cresult = send_command(name, 'show memory summary detail location all') + "\r\n"
    time.sleep(15)
    cresult = cresult + send_command(name, 'show process memory det') + "\r\n"
    time.sleep(15)
    cresult = cresult + send_command(name, 'show health memory') + "\r\n"
    time.sleep(15)
    cresult = cresult + send_command(name, 'show watchdog memory-state location all') + "\r\n"
    time.sleep(15)
    cresult = cresult + send_command(name, 'show shmem summary location all') + "\r\n"

    xlsq.put(cresult)

def main():
    try:
        with open('/etc/hosts', 'r') as f:
            lines = f.readlines()
    except IOError:
        print 'Could not read file /etc/hosts'

    # match on the MPEs and IGW hostnames
    devtype = re.compile(r'uk[xtn][a-z]{2}[1-9][ap][be][0-1][1-9]|[a-z]{4}[0-9]{2}-igw-a1')

    flag = 0

    workbook = xlsxwriter.Workbook('asr9k.xlsx')
    cell_format = workbook.add_format()
    cell_format.set_text_wrap()

    pool = []

    xlsq = mp.Queue()

    for host in lines:
        if re.findall(devtype, host.lower()):
            ip, name = host.split()

            worksheet = workbook.add_worksheet(name)
            pool.append(mp.Process(target=command_set, args=(name, xlsq)))

    for p in pool:
        p.start()

    for p in pool:
        queueitem = xlsq.get()
        nodename = re.search(devtype, queueitem)
        worksheet = workbook.get_worksheet_by_name(nodename.group(0))
        string = re.split(devtype,queueitem)

        for i in range(len(string)):
            worksheet.set_column(i, 0, 150)
            worksheet.write(i, 0, string[i], cell_format)

    for p in pool:
        p.join()

    workbook.close()

    response = subprocess.Popen(['uuencode asr9k.xlsx asr9k-mem-audit.xlsx | mailx -s "Memory Audits IGW/MPE" IPMobileCore@vodafone.com'],
                                        stdout=subprocess.PIPE,
                                        shell=True)
if __name__ == '__main__':
    signal.signal(signal.SIGINT, signal_handler)  # catch ctrl-c and call handler to terminate the script
    main()
