#!/usr/bin/env python

import os
import sys
import argparse
import subprocess
import re
import fnmatch
import urllib

if sys.version_info >= (3, 0):
  import urllib

  from urllib.parse import urlencode
  from urllib.request import Request, urlopen
else:
  from urllib import urlencode
  import urllib2
  from urllib2 import Request, urlopen

env = os.environ

class bcolors:
  HEADER = '\033[95m'
  OKBLUE = '\033[94m'
  OKGREEN = '\033[92m'
  WARNING = '\033[93m'
  FAIL = '\033[91m'
  ENDC = '\033[0m'
  BOLD = '\033[1m'
  UNDERLINE = '\033[4m'

parser = argparse.ArgumentParser()

parser.add_argument("-t", "--token", help="Token to authenticate (not needed for public projects on appveyor, travis and circle-ci", required=True)
parser.add_argument("-n", "--name", help="Custom name for the text run")
parser.add_argument("-r", "--root_dir", help="The root directory of the git-project, to be used for aligning paths properly. Default is the git-root.")
parser.add_argument("-s", "--sha", help="Specify the commit sha - normally determined by invoking git")
parser.add_argument("-u", "--slug", help="Slug of the reporistory, e.g. report-ci/scripts")
parser.add_argument("-c", "--check_run", help="The check-run id used by github, used to update reports.")
parser.add_argument("-x", "--text", help="Text for the placeholder")

args = parser.parse_args()

commit = None
if args.sha:
  commit = args.sha
if not commit:
  commit = subprocess.check_output(["git" ,"rev-parse", "HEAD"]).decode().strip()

print(bcolors.OKBLUE + '    Commit hash: ' + commit + bcolors.ENDC)

root_dir = args.root_dir
if not root_dir:
  root_dir = subprocess.check_output(["git" ,"rev-parse", "--show-toplevel"]).decode().replace('\n', '')


print (bcolors.OKBLUE + "    Root dir: " + root_dir + bcolors.ENDC)

owner, repo = None, None
if args.slug:
  try:
    (owner, repo) = args.slug.split('/')
  except:
    print (bcolors.WARNING + "Invalid Slug: '{0}'".format(slug) + bcolors.ENDC)
    exit(1)

if not owner or not repo:
  remote_v = subprocess.check_output(["git" ,"remote", "-v"]).decode()
  match = re.search(r"https:\/\/github.com\/([-_A-Za-z0-9]+)\/([-._A-Za-z0-9]+)\.git", remote_v)
  if match:
    owner = match.group(1)
    repo  = match.group(2)
  else:
    match = re.search(r"git@github\.com:([-_A-Za-z0-9]+)\/([-._A-Za-z0-9]+)\.git", remote_v)
    owner = match.group(1)
    repo  = match.group(2)

print (bcolors.OKBLUE + "    Project: " + owner + '/' + repo + bcolors.ENDC)

query = {
  'owner': owner,
  'repo': repo,
  'head-sha': commit,
  'root-dir': root_dir,
  'check-run-id': args.check_run,
  'token' : args.token,
}

if args.name:
    query['run-name'] = args.name

url = "https://api.report.ci/publish/cancel"
if sys.version_info >= (3, 0):
  url = urllib.request.urlopen(url).geturl()
else:
  url = urllib.urlopen(url).geturl()

upload_content = ""
if args.text:
    upload_content = open(args.text, "r").read()

uc =  bytes(upload_content, "utf8") if sys.version_info >= (3, 0) else upload_content

request = Request(url + "?" + urlencode(query), uc)
request.get_method = lambda: 'PATCH';
request.add_header("Authorization",  "Bearer " + args.token)
request.add_header("Content-Type",  "text/plain")

try:
  response = urlopen(request).read().decode()
  print(response)
  exit(0)
except Exception  as e:
  print(bcolors.FAIL + 'Cancelling failed: {0}'.format(e) + bcolors.ENDC);
  print(e.read())
  exit(1)
