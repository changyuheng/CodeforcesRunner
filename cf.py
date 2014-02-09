#! /usr/bin/env python
# -*- coding: utf-8 -*-

import os.path
import sys
import time
import re
import subprocess
import urllib2
from optparse import *
from lxml import etree

CODEFORCES_URL = 'http://codeforces.com'
EPS = 1e-6

class Executer(object):
    def __init__(self, env, id):
        self.env = env
        self.id = id

    def compile(self):
        if len(self.env['compile']) == 0: return 0
        return subprocess.call(self.env['compile'].format(self.id), shell=True)

    def execute(self):
        return subprocess.Popen(self.env['execute'].format(self.id), shell=True, stdin=subprocess.PIPE, stdout=subprocess.PIPE)

def add_options():
    usage = '%prog [options] [source code]'
    parser = OptionParser(usage=usage)
    parser.add_option( '-c', '--contest', dest='contest_id', help='Download the specific contest. '
            'If the PROBLEM_ID isn\'t specific, then download all problems in the contest.')
    parser.add_option( '-p', '--problem', dest='problem_id', help='Download the specific problem. '
            'The CONTEST_ID is required.')
    return parser.parse_args()

def download_contest(contest_id):
    contest_url = '/'.join((CODEFORCES_URL, 'contest', contest_id))
    contest_page = urllib2.urlopen(contest_url)
    tree = etree.HTML(contest_page.read())
    for i in tree.xpath(".//table[contains(@class, 'problems')]//td[contains(@class, 'id')]/a"):
        download_problem(contest_id, i.text.strip())

def download_problem(contest_id, problem_id):
    node_to_string = lambda node: ''.join([node.text]+map(etree.tostring, node.getchildren()))

    problem_url = '/'.join((CODEFORCES_URL, 'contest', contest_id, 'problem', problem_id))
    problem_page = urllib2.urlopen(problem_url)
    tree = etree.HTML(problem_page.read())

    title = tree.xpath('.//div[contains(@class, "problem-statement")]/div/div[contains(@class, "title")]')[0].text
    name = title[3:]

    filename = conf.PATTERN.format(id=problem_id, name=name, contest=contest_id)
    filename = re.sub(r'upper\((.*?)\)', lambda x: x.group(1).upper(), filename)
    filename = re.sub(r'lower\((.*?)\)', lambda x: x.group(1).lower(), filename)
    filename = filename.replace(' ', conf.REPLACE_SPACE)
    filename += conf.EXTENSION

    with open(filename, 'w') as f:
        f.write('<tests>\n')
        for (input_node, answer_node) in zip(
                tree.xpath('.//div[contains(@class, "input")]/pre'),
                tree.xpath('.//div[contains(@class, "output")]/pre')):
            f.write('<input><![CDATA[\n')
            f.write(node_to_string(input_node).replace('<br/>', '\n'))
            f.write('\n')
            f.write(']]></input>\n')
            f.write('<answer><![CDATA[\n')
            f.write(node_to_string(answer_node).replace('<br/>', '\n'))
            f.write('\n')
            f.write(']]></answer>\n')
        f.write('</tests>\n')

    print 'contest={0!r}, id={1!r}, problem={2!r} is downloaded.'.format(contest_id, problem_id, name)

def is_integer(s):
    try:
        int(s)
    except ValueError:
        return False
    return True

def is_number(s):
    try:
        float(s)
    except ValueError:
        return False
    return True

def floating_equal(a, b):
    return abs(a-b) < EPS

def check_result(answer_text, output_text):
    answer_tokens = answer_text.split()
    output_tokens = output_text.split()
    if len(answer_tokens) != len(output_tokens): return False
    for answer_token, output_token in zip(answer_tokens, output_tokens):
        if is_integer(answer_token) and is_integer(output_token):
            if int(answer_token) != int(output_token): return False
        elif is_number(answer_token) and is_number(output_token):
            if not floating_equal(float(answer_token), float(output_token)): return False
        else:
            if answer_token != output_token: return False
    return True

def handle_test(executer, case, input_text, answer_text):
    print 'output:'
    start = time.time()
    proc = executer.execute()
    proc.stdin.write(input_text)
    output_text = ''
    for output_line in iter(proc.stdout.readline,''):
        print output_line,
        output_text += output_line
    proc.wait()
    print
    end = time.time()

    if proc.returncode != 0:
        result = 'RE'
    elif answer_text == output_text:
        result = 'EXACTLY'
    elif check_result(answer_text, output_text):
        result = 'AC'
    else:
        result = 'WA'

    if result != 'EXACTLY':
        print 'answer:'
        print answer_text

    print '=== Case #{0}: {1} ({2} ms) ===\n'.format(case, result, int((end-start)*1000))
    if result != 'EXACTLY':
        raw_input('press enter to continue or <C-c> to leave.')

def main():
    global options, conf
    (options, args) = add_options()

    try:
        import conf
    except ImportError, e:
        print 'conf.py is not exist.'
        print 'Maybe you should copy `conf.py.example` to `conf.py`.'
        sys.exit(1)

    if options.contest_id != None:
        if options.problem_id != None:
            download_problem(options.contest_id, options.problem_id)
        else:
            download_contest(options.contest_id)
        sys.exit(0)

    if len(args) < 1 or not os.path.exists(args[0]):
        print 'Source code not exist!'
        sys.exit(1)

    id, lang = os.path.splitext(args[0])
    executer = Executer(conf.ENV[lang], id)

    ret = executer.compile()

    if ret != 0:
        print '>>> failed to Compile the source code!'
        sys.exit(1)

    with open('{0}{1}'.format(id, conf.EXTENSION)) as test_file:
        tree = etree.XML(test_file.read())

        inputs = tree.xpath('./input')
        answers = tree.xpath('./answer')
        case_count = len(inputs)

        for case in xrange(case_count):
            input_text = inputs[case].text[1:-1]
            answer_text = answers[case].text[1:-1]
            handle_test(executer, case, input_text, answer_text)

if __name__ == '__main__':
    main()
