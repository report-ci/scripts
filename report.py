#!/usr/bin/env python

import os
import sys
import argparse
import subprocess
import re
import fnmatch
import urllib
import json

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

##
tools = ["gcc", "go", "java", "msvc", "net",  "node", "php", "python", "ruby"]
frameworks = ["boost", "junit", "testng", "xunit", "cmocka", "unity", "criterion", "bandit",
              "catch", "cpputest", "cute", "cxxtest", "gtest", "qtest", "go-test", "testunit", "rspec", "minitest",
              "nunit", "mstest", "xunitnet", "phpunit", "pytest", "pyunit", "mocha", "ava", "tap", "tape", "qunit", "doctest"]

framework_names = {
  "boost":     "Boost.test",
  "junit":     "JUnit",
  "testng":    "TestNG",
  "xunit":     "Unspecified xUnit",
  "cmocka":    "CMocka",
  "unity":     "Unity",
  "criterion": "Criterion",
  "bandit":    "Bandit",
  "catch":     "Catch",
  "cpputest":  "CppUTest",
  "cute":      "CuTe",
  "cxxtest":   "CxxTest",
  "gtest":     "Google Test",
  "qtest":     "QTest",
  "go-test":   "Go",
  "testunit":  "TestUnit",
  "rspec":     "RSpec",
  "minitest":  "MiniTest",
  "nunit":     "NUnit",
  "mstest":    "MSTest",
  "xunitnet":  "XUnit.net",
  "phpunit":   "PHPUnit",
  "pytest":    "PyTest",
  "pyunit":    "PyUnit",
  "mocha":     "Mocha",
  "ava":       "AVA",
  "tap":       "Unspecificed TAP",
  "tape":      "Tape",
  "qunit":     "QUnit",
  "doctest":   "Doctest"
}

parser.add_argument("-i", "--include", nargs='+', help="Test files to include with auto, can cointain unix-style wildcard. (default *.xml)", default=["*.xml", "*.json", "*.trx", "*.tap"])


for fr in frameworks:
  parser.add_argument('-i-' + fr, '--include-as-' + fr, nargs='+', help=argparse.SUPPRESS)

parser.add_argument('-i-<framework>, --include-as-<framework>', nargs='+', help="Define test files for <framework>, similar to --include. Available values for framework: [" + ', '.join(frameworks) + ']')

for t in tools:
  parser.add_argument('-l-' + t, '--log-as-' + t, nargs='+', help=argparse.SUPPRESS)

parser.add_argument('-l-<tool>, --log-as-<tool>', nargs='+', help="Define logfiles files for <tools>, similar to --include. Available values for tool: [" + ', '.join(tools) + ']')


parser.add_argument("-x", "--exclude",   nargs='+', help="Test files to exclude, can cointain unix-style wildcard.",      default=[])
parser.add_argument("-l", "--file-list", nargs='+', help="Explicit file list, if given include and exclude are ignored.", default=None)

parser.add_argument("-t", "--token", help="Token to authenticate (not needed for public projects on appveyor, travis and circle-ci")
parser.add_argument("-n", "--name", help="Custom defined name of the upload when commiting several builds with the same ci system")

parser.add_argument("-u", "--result", help="Force a result. Report.ci will deduce it if not provided.", choices=["success", "fail", "neutral"])
parser.add_argument("-r", "--root-dir", help="The root directory of the git-project, to be used for aligning paths properly. Default is the git-root.")
parser.add_argument("-b", "--build-id", help="The identifier The Identifier for the build. When used on a CI system this will be automatically generated.")
parser.add_argument("-a", "--sha", help="Specify the commit sha - normally determined by invoking git")
parser.add_argument("-e", "--report-id", help="The report-id as given by report-ci.")
parser.add_argument("-c", "--check_run", help="The check-run id used by github, used to update reports.")
parser.add_argument("-d", "--id-file" , help="The file to hold the report id given by report.ci.", default=".report-ci-id.json")
parser.add_argument("-D", "--define", help="Define a preprocessor token for the name lookup.", nargs='+')
parser.add_argument("-p", "--preset", help="Select a definition & include preset from .report-ci.yaml.")
parser.add_argument("-m", "--merge", help="Merge similar annotations from different check-runs.")

args = parser.parse_args()



if "REPORT_CI_TOKEN" in env and not args.token:
  args.token = env["REPORT_CI_TOKEN"]

if not args.report_id:
  try:
    args.report_id = json.loads(open(args.id_file, "r").read())["id"]
  except:
    pass


if not args.check_run:
  try:
    args.check_run = json.loads(open(args.id_file, "r").read())["github"]
  except:
    pass

## Alright, now detect the CI - thanks to codecov for the content

root_dir = None
service = None
branch  = None
commit  = None
slug = None
run_name = args.name
build_id = None
account_name = None
os_name = None

meta = None

if "JENKINS_URL" in env:
  print (bcolors.HEADER + "    Jenkins CI detected." + bcolors.ENDC)
  # https://wiki.jenkins-ci.org/display/JENKINS/Building+a+software+project
  # https://wiki.jenkins-ci.org/display/JENKINS/GitHub+pull+request+builder+plugin#GitHubpullrequestbuilderplugin-EnvironmentVariables
  service="jenkins"

  if "ghprbSourceBranch" in env:
     branch=env.get("ghprbSourceBranch")
  elif "GIT_BRANCH" in env:
     branch=env.get("GIT_BRANCH")
  elif "BRANCH_NAME" in env:
     branch=env.get("BRANCH_NAME")

  if "ghprbActualCommit" in env:
    commit = env.get("ghprbActualCommit")
  elif "GIT_COMMIT" in env:
    commit = env.get("GIT_COMMIT")

  if "ghprbPullId" in env:
    pr = env.get("ghprbPullId")
  elif "CHANGE_ID"  in env:
    pr = env.get("CHANGE_ID")

  if "WORKSPACE" in env:
    root_dir = env["WORKSPACE"]

  meta = {
    "service": "jenkins-ci",
    "pull-request": pr,
    "build": env.get("BUILD_NUMBER"),
    "url":  env.get("BUILD_URL"),
    "node": env.get("NODE_NAME"),
    "job":  env.get("JOB_NAME"),
    "tag":  env.get("BUILD_TAG"),
    "executor": env.get("EXECUTOR_NUMBER"),
    "workspace": env.get("WORKSPACE")
  }

elif (env.get("CI") == "true") and (env.get("TRAVIS") == "true") and (env.get("SHIPPABLE") != "true" ):

  print(bcolors.HEADER + "    Travis CI detected." + bcolors.ENDC)
  service = "travis-ci"
  # https://docs.travis-ci.com/user/environment-variables/
  commit = env.get("TRAVIS_COMMIT")
  build_id=env.get("TRAVIS_JOB_ID")
  build=env.get("TRAVIS_JOB_NUMBER")
  slug=env.get("TRAVIS_REPO_SLUG")
  tag=env.get("TRAVIS_TAG")
  root_dir=env.get("TRAVIS_BUILD_DIR")

  if env.get("TRAVIS_BRANCH") != env.get("TRAVIS_TAG"):
    branch=env.get("TRAVIS_BRANCH")

  meta = {
      "service": "travis-ci",
      "build": env.get("TRAVIS_BUILD_ID"),
      "url":  env.get("TRAVIS_BUILD_WEB_URL"),
      "pull-request": env.get("TRAVIS_PULL_REQUEST"),
      "job-name":  env.get("TRAVIS_JOB_NAME"),
      "job":  env.get("TRAVIS_JOB_NUMBER"),
      "tag":  env.get("TRAVIS_TAG"),
      "executor": env.get("TRAVIS_DIST"),
      "os": env.get("TRAVIS_OS_NAME")
    }

elif "DOCKER_REPO" in env:
  print(bcolors.HEADER +"    Docker detected." + bcolors.ENDC)
  # https://docs.docker.com/docker-cloud/builds/advanced/
  service="docker"
  branch=env.get("SOURCE_BRANCH")
  commit=env.get("SOURCE_COMMIT")
  slug=env.get("DOCKER_REPO")
  tag=env.get("CACHE_TAG")

  meta = {
    "service": "docker-cloud",
    "tag" : env.get("DOCKER_TAG")
  }

elif env.get("CI") == "true" and env.get("CI_NAME") == "codeship":
  print(bcolors.HEADER +"    Codeship CI detected." + bcolors.ENDC)
  # https://www.codeship.io/documentation/continuous-integration/set-environment-variables/
  service="codeship"
  branch=env.get("CI_BRANCH")
  build=env.get("CI_BUILD_NUMBER")
  ##build_url=urlencode(env.get("CI_BUILD_URL"));
  commit=env.get("CI_COMMIT_ID")

elif "CF_BUILD_URL" in env and "CF_BUILD_ID" in env:
  print(bcolors.HEADER +"    Codefresh CI detected." + bcolors.ENDC)
  # https://docs.codefresh.io/v1.0/docs/variables
  service="codefresh"
  branch=env.get("CF_BRANCH")
  build=env.get("CF_BUILD_ID")
  #build_url=urlencode(env.get("CF_BUILD_URL"))
  commit=env.get("CF_REVISION")

elif "TEAMCITY_VERSION" in env:
  print(bcolors.HEADER +"    TeamCity CI detected." + bcolors.ENDC)
  # https://confluence.jetbrains.com/display/TCD8/Predefined+Build+Parameters
  # https://confluence.jetbrains.com/plugins/servlet/mobile#content/view/74847298
  if "TEAMCITY_BUILD_ID" in env:
    print ("    Teamcity does not automatically make build parameters available as environment variables.")
    print ("    Add the following environment parameters to the build configuration")
    print ("    env.TEAMCITY_BUILD_BRANCH = %teamcity.build.branch%")
    print ("    env.TEAMCITY_BUILD_ID = %teamcity.build.id%")
    print ("    env.TEAMCITY_BUILD_URL = %teamcity.serverUrl%/viewLog.html?buildId=%teamcity.build.id%")
    print ("    env.TEAMCITY_BUILD_COMMIT = %system.build.vcs.number%")
    print ("    env.TEAMCITY_BUILD_REPOSITORY = %vcsroot.<YOUR TEAMCITY VCS NAME>.url%")

  service="teamcity"
  branch=env.get("TEAMCITY_BUILD_BRANCH")
  build=env.get("TEAMCITY_BUILD_ID")
  #build_url=urlencode(env.get("TEAMCITY_BUILD_URL"))
  if "TEAMCITY_BUILD_COMMIT" in env:
    commit=env.get("TEAMCITY_BUILD_COMMIT")
  else:
    commit=env.get("BUILD_VCS_NUMBER")
  remote_addr=env.get("TEAMCITY_BUILD_REPOSITORY")

elif "CI" in env and "CIRCLECI" in env:
  print(bcolors.HEADER +"    Circle CI detected." + bcolors.ENDC)
  # https://circleci.com/docs/environment-variables
  service = "circle-ci"
  branch = env.get("CIRCLE_BRANCH")
  build_id = env.get("CIRCLE_BUILD_NUM")
  job = env.get("CIRCLE_NODE_INDEX")
  pr = env.get("CIRCLE_PR_NUMBER")
  commit = env.get("CIRCLE_SHA1")
  root_dir = os.path.expanduser(env.get("CIRCLE_WORKING_DIRECTORY"))
  slug = env.get("CIRCLE_PROJECT_USERNAME") + "/" + env.get("CIRCLE_PROJECT_REPONAME")

  meta = {
    "service": "circleci",
    "build": env.get("CIRCLE_BUILD_NUM"),
    "url":  env.get("CIRCLE_BUILD_URL"),
    "pull-request": env.get("CI_PULL_REQUEST"),
    "job":  env.get("CIRCLE_JOB"),
    "node": env.get("CIRCLE_NODE_INDEX"),
    "tag":  env.get("CIRCLE_TAG")
  }

elif "BUDDYBUILD_BRANCH" in env:
  print(bcolors.HEADER + "    buddybuild detected." + bcolors.ENDC)
  # http://docs.buddybuild.com/v6/docs/custom-prebuild-and-postbuild-steps
  service = "buddybuild"
  branch = env.get("BUDDYBUILD_BRANCH")
  build = env.get("BUDDYBUILD_BUILD_NUMBER")
  #build_url = "https://dashboard.buddybuild.com/public/apps/$BUDDYBUILD_APP_ID/build/$BUDDYBUILD_BUILD_ID"

elif env.get("CI") == "true" and env.get("BITRISE_IO") == "true":
  # http://devcenter.bitrise.io/faq/available-environment-variables/
  print(bcolors.HEADER + "    Bitrise detected." + bcolors.ENDC)
  service = "bitrise"
  branch = env.get("BITRISE_GIT_BRANCH")
  build  = env.get("BITRISE_BUILD_NUMBER")
  #build_url =urlencode(env.get("BITRISE_BUILD_URL"))
  pr = env.get("BITRISE_PULL_REQUEST")
  if "GIT_CLONE_COMMIT_HASH" in env:
    commit = env.get("GIT_CLONE_COMMIT_HASH")

elif "CI" in env and "SEMAPHORE" in env:
  print(bcolors.HEADER + "    Semaphore CI detected." + bcolors.ENDC)
  # https://semaphoreapp.com/docs/available-environment-variables.html
  service = "semaphore"
  branch = env.get("BRANCH_NAME")
  build = env.get("SEMAPHORE_BUILD_NUMBER")
  build_id = env.get("SEMAPHORE_CURRENT_THREAD")
  pr = env.get("PULL_REQUEST_NUMBER")
  slug = env.get("SEMAPHORE_REPO_SLUG")
  commit = env.get("REVISION")

elif env.get("CI") == "true" and env.get("BUILDKITE"):
  print(bcolors.HEADER + "    Buildkite CI detected." + bcolors.ENDC)
  # https://buildkite.com/docs/guides/environment-variables
  service = "buildkite"
  branch = env.get("BUILDKITE_BRANCH")
  build  = env.get("BUILDKITE_BUILD_NUMBER")
  build_id = env.get("BUILDKITE_JOB_ID")
  #build_url = urlencode(env.get("BUILDKITE_BUILD_URL"))
  slug = env.get("BUILDKITE_PROJECT_SLUG")
  commit = env.get("BUILDKITE_COMMIT")
  if env.get("BUILDKITE_PULL_REQUEST") != "false":
    pr = env.get("BUILDKITE_PULL_REQUEST")

  tag = env.get("BUILDKITE_TAG")

elif env.get("CI") == "drone" or env.get("DRONE") == "true":
  print(bcolors.HEADER + "    Drone CI detected." + bcolors.ENDC)
  # http://docs.drone.io/env.html
  # drone commits are not full shas
  service = "drone.io"
  branch = env.get("DRONE_BRANCH")
  build_id  = env.get("DRONE_BUILD_NUMBER")
  #build_url =urlencode(env.get("DRONE_BUILD_LINK"))
  pr  = env.get("DRONE_PULL_REQUEST")
  job = env.get("DRONE_JOB_NUMBER")
  tag = env.get("DRONE_TAG")

elif "HEROKU_TEST_RUN_BRANCH" in env:
  print(bcolors.HEADER + "    Heroku CI detected." + bcolors.ENDC)
  # https://devcenter.heroku.com/articles/heroku-ci#environment-variables
  service = "heroku"
  branch = env.get("HEROKU_TEST_RUN_BRANCH")
  build_id  = env.get("HEROKU_TEST_RUN_ID")

elif env.get("CI") == "True" and env.get("APPVEYOR") == "True":
  print(bcolors.HEADER + "    Appveyor CI detected." + bcolors.ENDC)
  # http://www.appveyor.com/docs/environment-variables
  service = "appveyor"
  if "APPVEYOR_PULL_REQUEST_HEAD_REPO_BRANCH" in env:
    branch = env.get("APPVEYOR_PULL_REQUEST_HEAD_REPO_BRANCH")
  else:
    branch = env.get("APPVEYOR_REPO_BRANCH")
  build_id = env.get("APPVEYOR_BUILD_ID")
  pr = env.get("APPVEYOR_PULL_REQUEST_NUMBER")
  commit = env.get("APPVEYOR_REPO_COMMIT")
  slug = env.get("APPVEYOR_REPO_NAME")
  account_name = env.get("APPVEYOR_ACCOUNT_NAME")
  root_dir = env.get("APPVEYOR_BUILD_FOLDER")


  meta = {
    "service": "appveyor",
    "build": env.get("APPVEYOR_BUILD_ID "),
    "url":  env.get("APPVEYOR_URL"),
    "pull-request": env.get("APPVEYOR_PULL_REQUEST_NUMBER"),
    "job":  env.get("APPVEYOR_JOB_ID"),
    "job-name": env.get("APPVEYOR_JOB_NAME"),
    "tag":  env.get("APPVEYOR_REPO_TAG_NAME"),
    "os" : env.get("PLATFORM")
  }

elif env.get("CI") == "true" and "WERCKER_GIT_BRANCH" in env:
  print(bcolors.HEADER + "    Wercker CI detected." + bcolors.ENDC)
  # http://devcenter.wercker.com/articles/steps/variables.html
  service = "wercker"
  branch = env.get("WERCKER_GIT_BRANCH")
  build  = env.get("WERCKER_MAIN_PIPELINE_STARTED")
  commit = env.get("WERCKER_GIT_COMMIT")

elif env.get("CI") == "true" and env.get("MAGNUM") == "true":
  print(bcolors.HEADER + "    Magnum CI detected." + bcolors.ENDC)
  # https://magnum-ci.com/docs/environment
  service = "magnum"
  branch = env.get("CI_BRANCH")
  build  = env.get("CI_BUILD_NUMBER")
  commit = env.get("CI_COMMIT")

elif env.get("SHIPPABLE") == "true":
  print(bcolors.HEADER + "    Shippable CI detected." + bcolors.ENDC)
  # http://docs.shippable.com/ci_configure/
  service = "shippable"
  build = env.get("BUILD_NUMBER")
  #build_url =urlencode(env.get("BUILD_URL"))
  pr = env.get("PULL_REQUEST")
  slug = env.get("REPO_FULL_NAME")
  commit = env.get("COMMIT")

elif env.get("TDDIUM") == "true":
  print(bcolors.HEADER + "    Solano CI detected." + bcolors.ENDC)
  # http://docs.solanolabs.com/Setup/tddium-set-environment-variables/
  service = "solano"
  commit = env.get("TDDIUM_CURRENT_COMMIT")
  branch = env.get("TDDIUM_CURRENT_BRANCH")
  build = env.get("TDDIUM_TID")
  pr = env.get("TDDIUM_PR_ID")

elif env.get("GREENHOUSE") == "true":
  print(bcolors.HEADER + "    Greenhouse CI detected." + bcolors.ENDC)
  # http://docs.greenhouseci.com/docs/environment-variables-files
  service = "greenhouse"
  branch = "$GREENHOUSE_BRANCH"
  build = "$GREENHOUSE_BUILD_NUMBER"
  #build_url =urlencode(env.get("GREENHOUSE_BUILD_URL"))
  pr = "$GREENHOUSE_PULL_REQUEST"
  commit = "$GREENHOUSE_COMMIT"
  search_in = env.get("GREENHOUSE_EXPORT_DIR")

elif "GITLAB_CI" in env:
  print(bcolors.HEADER + "    GitLab CI detected." + bcolors.ENDC)
  # http://doc.gitlab.com/ce/ci/variables/README.html
  service = "gitlab"
  build = env.get("CI_BUILD_ID") + ":" + env.get("CI_JOB_ID")
  remote_addr = env.get("CI_REPOSITORY_URL")
  commit = env.get("CI_COMMIT_SHA")

elif "SYSTEM_TEAMFOUNDATIONSERVERURI" in env:
  print(bcolors.HEADER + "    Azure Pipelines detected." + bcolors.ENDC)
  # https://docs.microsoft.com/en-us/azure/devops/pipelines/build/variables?view=vsts
  service = "azure_pipelines"
  commit = env.get("BUILD_SOURCEVERSION")
  build = env.get("BUILD_BUILDNUMBER")
  if "PULL_REQUEST_NUMBER" in env:
    pr = env.get("PULL_REQUEST_ID")
  else:
   pr = env.get("PULL_REQUEST_NUMBER")
  job = env.get("BUILD_BUILDID")
  branch = env.get("BUILD_SOURCEBRANCHNAME")

elif env.get("GITHUB_ACTIONS") == "true":
  print(bcolors.HEADER + "    Github actions CI detected." + bcolors.ENDC)
  # https://help.github.com/en/actions/configuring-and-managing-workflows/using-environment-variables
  service = "github-actions"
  build_id = env.get("GITHUB_ACTION")
  commit = env.get("GITHUB_SHA")
  slug = env.get("GITHUB_REPOSITORY")
  account_name = env.get("GITHUB_ACTOR")
  root_dir = env.get("GITHUB_WORKSPACE")


  meta = {
    "service": "github-acttions",
    "workflow": env.get("GITHUB_WORKFLOW"),
    "run":  env.get("GITHUB_RUN_ID"),
    "run-number": env.get("GITHUB_RUN_NUMBER"),
    "action": env.get("GITHUB_ACTION"),
    "event-name":  env.get("GITHUB_ACTOR")
  }

else:
    print(bcolors.HEADER + "    No CI detected." + bcolors.ENDC)

if args.root_dir:
  root_dir = args.root_dir

if args.sha:
  commit = args.sha
if not commit:
  commit = subprocess.check_output(["git" ,"rev-parse", "HEAD"]).decode().replace('\n', '')

print (bcolors.OKBLUE + "    Commit hash: " + commit + bcolors.ENDC)

if not root_dir:
  root_dir = subprocess.check_output(["git" ,"rev-parse", "--show-toplevel"]).decode().replace('\n', '')


print (bcolors.OKBLUE + "    Root dir: " + root_dir + bcolors.ENDC)

owner, repo = None, None
if slug:
  try:
    (owner, repo) = slug.split('/')
  except:
    print (bcolors.WARNING + "Invalid Slug: '{0}'".format(slug) + bcolors.ENDC)

if not owner or not repo:
  remote_v = subprocess.check_output(["git" ,"remote", "-v"]).decode()
  match = re.search(r"(?:https://|ssh://git@)github.com/([-_A-Za-z0-9]+)/((?:(?!\.git(?:\s|$))[-._A-Za-z0-9])+)", remote_v)
  if match:
    owner = match.group(1)
    repo = match.group(2)
  else:
    match = re.search(r"git@github\.com:([-_A-Za-z0-9]+)/((?:(?!\.git(?:\s|$))[-._A-Za-z0-9])+)", remote_v)
    owner = match.group(1)
    repo = match.group(2)


print (bcolors.OKBLUE + "    Project: " + owner + '/' + repo + bcolors.ENDC)

# find
def match_file(file_abs, include):
  match = False
  file = os.path.relpath(file_abs)
  for inc in include:
    if fnmatch.fnmatch(file, inc) or fnmatch.fnmatch(file_abs, inc):
      match = True
      break

  for exc in args.exclude:
    if fnmatch.fnmatch(file, exc) or fnmatch.fnmatch(file_abs, exc):
      match = False
      break

  return match

file_list = []
results = []

if not args.file_list:
  for wk in os.walk(root_dir):
    (path, subfolders, files) = wk
    if fnmatch.fnmatch(path, "*/.git*"):
      continue
    for file in files:
      abs_file = os.path.join(path, file)
      file_list.append(abs_file)
else:
  for file in args.file_list:
    abs = os.path.abspath(file)
    if not os.path.isfile(abs):
      print(bcolors.FAIL + "Could not find file '" + file + "'" + bcolors.ENDC)
      exit(1)
    else:
      file_list.append(abs)


for abs_file in file_list:
  if match_file(abs_file, args.include):
    content = None

    ext = os.path.splitext(abs_file)[1].lower()
    binary_content = open(abs_file, "rb").read()
    try:
      content = binary_content.decode('ascii')
    except UnicodeDecodeError:
      try:
        content = binary_content.decode('utf-8').encode("ascii","ignore").decode('ascii')
      except UnicodeDecodeError:
        try:
          content = binary_content.decode('utf-16').encode("ascii","ignore").decode('ascii')
        except UnicodeDecodeError:
          print(bcolors.FAIL + "Can't figure out encoding of file " + abs_file + ", ignoring it" + bcolors.ENDC)
          continue

    if ext == ".xml":
      if re.match(r"(<\?[^?]*\?>\s*)?<(?:TestResult|TestLog)>\s*<TestSuite", content):
        print("    Found " + abs_file + " looks like boost.test")
        results.append({'rawData': content, 'framework': 'boost', 'filename': abs_file})
        continue

      if re.match(r"(<\?[^?]*\?>\s*)?<TestCase", content) and (content.find("<QtVersion>") != -1 or content.find("<qtversion>") != -1):
        print("    Found " + abs_file + ", looks like qtest")
        results.append({'rawData': content, 'framework': 'qtest', 'filename': abs_file})

        continue

      if re.match(r'(<\?[^?]*\?>\s*)?<!-- Tests compiled with Criterion v[0-9.]+ -->\s*<testsuites name="Criterion Tests"', content):
        print("    Found " + abs_file + ", looks like criterion")
        results.append({'rawData': content, 'framework': 'criterion', 'filename': abs_file})
        continue

      if re.match(r"(<\?[^?]*\?>\s*)?(<testsuites>\s*)?<testsuite[^>]", content): #xUnit thingy
        if content.find('"java.version"') != -1 and (content.find('org.junit') != -1 or content.find('org/junit') != -1 or content.find('org\\junit') != -1):
          print("    Found " + abs_file + ", looks like JUnit")
          results.append({'rawData': content, 'framework': 'juni', 'filename': abs_file})
        elif content.find('"java.version"') != -1 and (content.find('org.testng') != -1 or content.find('org/testng') != -1 or content.find('org\    estng') != -1):
          print("    Found " + abs_file + ", looks like TestNG")
          results.append({'rawData': content, 'framework': 'testng', 'filename': abs_file})
        elif content.find('"java.version"') == -1 and content.find('<testsuite name="bandit" tests="') != -1:
          print("    Found " + abs_file + ", looks like Bandit")
          results.append({'rawData': content, 'framework': 'bandit', 'filename': abs_file})
        elif content.find('.php') != -1:
          print("    Found " + abs_file + ", looks like PHPUnit")
          results.append({'rawData': content, 'framework': 'phpunit', 'filename': abs_file})
        elif content.find('.py') != -1:
          print("    Found " + abs_file + ", looks like PyTest")
          results.append({'rawData': content, 'framework': 'pytest', 'filename': abs_file})
        else:
          print("    Found " + abs_file + ", looks like some xUnit")
          results.append({'rawData': content, 'framework': 'xunit', 'filename': abs_file})
        continue


      if re.match(r'(<\?[^?]*\?>\s*)?<Catch\s+name=', content):
        print("    Found " + abs_file + ", looks like catch")
        results.append({'rawData': content, 'framework': 'catch', 'filename': abs_file})
        continue
      if re.match(r'(<\?[^?]*\?>\s*)?<stream>\s*<ready-test-suite>', content):
        print("    Found " + abs_file + ", looks like TestUnit")
        results.append({'rawData': content, 'framework': 'testunit', 'filename': abs_file})
        continue
      if re.match(r'(<\?[^?]*\?>\s*)?(<!--This file represents the results of running a test suite-->)?<test-results\s+name', content) or \
         re.match(r'(<\?[^?]*\?>\s*)?<test-run id="2"', content):
        print("    Found " + abs_file + ", looks like NUnit")
        results.append({'rawData': content, 'framework': 'nunit', 'filename': abs_file})
        continue
      if re.match(r'(<\?[^?]*\?>)?\s*<assemblies', content):
        print("    Found " + abs_file + ", looks like xUnit.net")
        results.append({'rawData': content, 'framework': 'xunitnet', 'filename': abs_file})
        continue

      if re.match(r'(<\?[^?]*\?>)?\s*<doctest', content):
        print("    Found " + abs_file + ", looks like doctest")
        results.append({'rawData': content, 'framework': 'doctest', 'filename': abs_file})
        continue


    elif ext == ".json" and re.match(r"\s*({|\[)", content): #Might be JSON, let's see if it fits go
      try:
        lines = content.splitlines()
        json_lines = [json.loads(ln) for ln in lines]
        if all(val in json_lines[0] for val in ["Time", "Action", "Package"]): #assumption
          print("Found " + abs_file + ", looks like GoTest")
          results.append({'rawData':  content, 'framework': 'go-test', 'filename': abs_file})
          continue
      except:
        pass
      try:
        data = json.loads(content)

        if "version" in data and "examples" in data and "summary" in data and "summary_line" in data :
          print("Found " + abs_file + ", looks like RSpec")
          results.append({'rawData': content, 'framework': 'rspec', 'filename': abs_file})
          continue
        if "stats" in data and "tests" in data and "pending" in data and "passes" in data and "failures" in data:
          print("Found " + abs_file + ", looks like Mocha")
          results.append({'rawData': content, 'framework': 'mocha', 'filename': abs_file})
          continue
      except:
        pass

    elif ext == ".trx" and re.match(r"(<\?[^?]*\?>\s*)?<TestRun", content):
      print("Found " + abs_file + ", looks like MsTest")
      results.append({'rawData': content, 'framework': 'mstest', 'filename': abs_file})

    elif ext == ".tap" and re.match(r"TAP version \d+", content): # is Test anything protocol

      if re.match(r"ava[\\\/]cli.js", content):
        print("Found " + abs_file + ", looks like AVA")
        results.append({'rawData': content, 'framework': 'ava', 'filename': abs_file})
      else:
        print("Found " + abs_file + ", looks like TAP")
        results.append({'rawData': content, 'framework': 'tap', 'filename': abs_file})

for framework in frameworks:
  incl = getattr(args, 'include_as_' + framework.replace('-', '_'))

  if incl is None:
    continue

  for abs_file in (abs_file for abs_file in file_list if match_file(abs_file, incl)):
    content = open(abs_file).read()
    results.append({'rawData': content, 'framework': framework, 'filename': abs_file})

logs = []
for tool in tools:
  incl = getattr(args, 'log_as_' + tool)

  if incl is None:
    continue

  for abs_file in (abs_file for abs_file in file_list if match_file(abs_file, incl)):
    content = open(abs_file).read()
    logs.append({'rawData': content, 'tool': tool, 'logName': abs_file})

for fr in frameworks:
  cnt = len([res for res in results if res["framework"] == fr])
  if cnt > 0:
    print(bcolors.HEADER + str(cnt) + " files for "+  framework_names[fr] + bcolors.ENDC)


content_type = "application/json"
upload_content = json.dumps({'files': file_list, "logs": logs, "results": results, "meta": meta})


upload_content = upload_content.strip()
if len(upload_content) == 0:
  print(bcolors.FAIL + " No test data to upload.")
  exit(1)

if service and not args.name and run_name:
  if os_name:
    run_name += " [" + service +  ", " + os_name + "]"
  else:
    run_name += " [" + service + "]"

headers = {}

query = {
  'owner': owner,
  'repo': repo,
  'head-sha': commit,
  'root-dir': root_dir,
  'branch': branch,
  'account-name': account_name,
}

if run_name: query['run-name'] = run_name
if args.check_run: query['check-run-id'] = args.check_run
if args.preset: query['preset'] = args.preset
if args.define: query['define'] = args.define
if args.merge:  query["merge"] = args.merge
if args.result: query["result"] = args.result

url = "https://api.report.ci/report/"

if sys.version_info >= (3, 0):
  url = urllib.request.urlopen(url).geturl()
else:
  url = urllib.urlopen(url).geturl()

if service and service in ["travis-ci", "appveyor", "circle-ci", "github-actions"] and args.token == None:
  query["build-id"] = build_id
  url += service + "/"

if sys.version_info >= (3, 0):
  upload_content=  bytes(upload_content, "utf8")

if args.check_run and not args.name and 'run-name' in query:
  del query['run-name']


request = Request(url + "?" + urlencode(query), upload_content , headers)
if args.token:   request.add_header("Authorization",  "Bearer " + args.token)
if content_type: request.add_header("Content-Type", content_type)

if args.check_run:
  request.get_method = lambda: 'PATCH'

try:
  response = urlopen(request).read().decode()
  print(bcolors.OKGREEN + "Published: '{0}".format(response) + bcolors.ENDC)
  res = json.loads(response)
  ch_id = str(res["id"])
  print ('Uploaded check_run https://report.ci/reports/gh/{}/{}/{}'.format(owner, repo, ch_id))
  open(args.id_file, 'w').write(response)
  exit(0)

except Exception as e:
  print(bcolors.FAIL + 'Publishing failed: {0}'.format(e) + bcolors.ENDC)
  try:
    print(e.read())
  except:
    exit(1)
  exit(1)
