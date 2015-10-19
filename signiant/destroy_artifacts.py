import sys,os

from argparse import ArgumentParser
from ConfigParser import RawConfigParser

#Local jenkins.py
from jenkins import SigniantRemoteArtifactJobEntry


VERBOSE = False
DEBUG = False
JENKINS_JOBS_DIRECTORY_PATH = "/var/lib/jenkins/jobs"
IS_DRY_RUN = True
CONFIG_PATH = "/opt/signiant/destroy_artifacts/config"
ENVIRONMENT_VARIABLES = []
DEPLOYMENT_PATHS = []
DEPLOYMENT_STRUCTURES = []
IGNORE_JOBS = []

def __get_undeleted_artifact_paths__(entry):
    if not isinstance(entry, SigniantRemoteArtifactJobEntry) or entry is None:
        raise TypeError("You must pass in a SigniantRemoteArtifactJobEntry!")

def __enumerate_remote_artifact_config_entries__(jobs_path):
    for root, dirnames, filenames in os.walk(jobs_path):
        if "config.xml" in filenames:
            try:
                yield SigniantRemoteArtifactJobEntry(os.path.join(root,"config.xml"))
            except InvalidEntryError as e:
                if VERBOSE == 1:
                    print "Skipping over " + str(os.path.join(root,"config.xml"))

def __parse_config__(config_file_path):
    config = RawConfigParser()
    config.read('config_file_path')
   
    try:
        ENVIRONMENT_VARIABLES = config.get("jenkinsconfig","ENVIRONMENT_VARIABLES")
    except:
        raise
    try:
        DEPLOYMENT_PATHS = config.get("jenkinsconfig","DEPLOYMENT_PATHS")
    except:
        raise
    try:
        DEPLOYMENT_STRUCTURES = config.get("jenkinsconfig","DEPLOYMENT_STRUCTURES")
    except:
        raise
    try:
        IGNORE_JOBS = config.get("jenkinsconfig","IGNORE_JOBS")
    except:
        raise

def __parse_arguments__():
    pass
    

def destroy_artifacts(is_dry_run):
    #First we want to go through the config entries that contain Environment Variables from envinject
    for entry in __enumerate_remote_artifact_config_entries__(JENKINS_JOBS_DIRECTORY_PATH):
        if entry.get_build_number_list() is None:
            continue
        try:
            release_paths = entry.get_release_path_list(DEFAULT_RELEASE_KEYS)
            if release_paths is not None:
                print entry.name + " -- " + entry.project_title
                for release in entry.get_release_path_list(DEFAULT_RELEASE_KEYS): 
                    print release
        #If there's no match to any of the keys, then we don't care about this entry
        except TypeError:
            continue

if __name__ == "__main__":
    destroy_artifacts(IS_DRY_RUN)


    
