import sys,os

from argparse import ArgumentParser
from ConfigParser import RawConfigParser
from maestro.jenkins.jobs import EnvironmentVariableJobEntry, InvalidEntryError
from maestro.tools import string.replaceall

# Globals used throughout the script
VERBOSE = False
DEBUG = False

#ARG: Which Jenkins instance are we targetting? 
JENKINS_JOBS_DIRECTORY_PATH = "/var/lib/jenkins/jobs"

#ARG: Don't actually delete anything, but list what would be deleted
IS_DRY_RUN = True

#ARG: Where is the config file stored?
CONFIG_PATH = os.path.join("./config")

#CONFIG: REQUIRED environment variables
ENVIRONMENT_VARIABLES = []

#CONFIG: Environment Variables potentially containing deployment paths (i.e. paths to search for builds)
#The script will attempt to replace environment variables in the paths
DEPLOYMENT_PATHS = []

#Not sure yet if we'll need this
BUILD_STRUCTURES = []

#Jobs to ignore
IGNORE_JOBS = []

#Where to strip the deployment paths.
#Signiant: strip on $PROJECT_FAMILY, and prepend /Releases/Jenkins
STRIP_ROOT = {}

def __get_undeleted_artifact_paths__(entry):
    if not isinstance(entry, EnvironmentVariableJobEntry) or entry is None:
        raise TypeError("You must pass in a SigniantRemoteArtifactJobEntry!")

def __enumerate_remote_artifact_config_entries__(jobs_path):
    for root, dirnames, filenames in os.walk(jobs_path):
        if "config.xml" in filenames:
            try:
                yield EnvironmentVariableJobEntry(os.path.join(root,"config.xml"))
            except InvalidEntryError as e:
                if VERBOSE == 1:
                    print "Skipping over " + str(os.path.join(root,"config.xml"))

def __parse_config__(config_file_path):
    global ENVIRONMENT_VARIABLES
    global DEPLOYMENT_PATHS
    global DEPLOYMENT_STRUCTURES
    global IGNORE_JOBS
    global STRIP_ROOT

    config = RawConfigParser()
    config.read(config_file_path)
    
    try:
        ENVIRONMENT_VARIABLES = config.get("ArtifactConfig","ENVIRONMENT_VARIABLES").split(',')
    except:
        raise
    try:
        DEPLOYMENT_PATHS = config.get("ArtifactConfig","DEPLOYMENT_PATHS").split(',')
    except:
        raise
    try:
        DEPLOYMENT_STRUCTURES = config.get("ArtifactConfig","DEPLOYMENT_STRUCTURES").split(',')
    except:
        raise
    try:
        IGNORE_JOBS = config.get("ArtifactConfig","IGNORE_JOBS").split(',')
    except:
        raise
    try:
        entries = config.get("ArtifactConfig","STRIP_ROOT").split(',')
        for entry in entries:
            keyval = entry.strip(":")
            STRIP_ROOT[keyval[0]] = keyval[1]
    except:
        raise

def __verify_environment_variables__(entry):
    """
    Checks for the required environment variables from ENVIRONMENT_VARIABLES, and will raise an InvalidEntryError if one is not found or is None.
    """
    if not isinstance(entry,EnvironmentVariableJobEntry):
        raise TypeError("Received object of type " + str(type(environment_variable_job)) + " expected type SigniantRemoteArtifactJobEntry.")
    for var in ENVIRONMENT_VARIABLES:
        if var not in entry.environment_variables.keys() or entry.environment_variables[var] is None:
		raise InvalidEntryError("Required environment variable " + str(var) + " was not found in job entry " + str(entry.name) + ".")
       
def __get_release_path_list__(entry):

        releases = list()
	for key in DEPLOYMENT_PATHS:
            try:
		string_replace = dict()
		for var in ENVIRONMENT_VARIABLES:
                    try:
                        string_replace[str("$" + var)] = entry.environment_variables[var]
                    except KeyError:
                        continue
                converted_release_path = __strip_release_path(entry.environment_variables[key])
                formatted_release_path = string.replaceall(string_replace, entry.environment_variables[key])
                releases.append(formatted_release_path)
            except KeyError as e:
                #print str(e)
                pass
            except ValueError as e:
                #print str(e)
                pass
        if len(releases) == 0:
            return None
        else:
            return releases 

def __parse_arguments__():
    pass

def __strip_release_path__(release_path):
    clean_path = release_path.replace('\\','/')
    converted_path = os.path.abspath(clean_path)
    key = STRIP_ROOT.keys()[0]
    stripped_path = converted_path.split("key")
    return os.path.join(STRIP_ROOT[key],stripped_path)
    

def destroy_artifacts(is_dry_run):
    if not os.path.exists(CONFIG_PATH):
        raise ValueError("You need to provide a valid config file! Currently looking for: " + str(CONFIG_PATH))

    #Parse config file
    __parse_config__(CONFIG_PATH)
	
    #First we want to go through the config entries that contain Environment Variables from envinject
    for entry in __enumerate_remote_artifact_config_entries__(JENKINS_JOBS_DIRECTORY_PATH):
        if entry.get_build_number_list() is None:
            continue
        try:
            __verify_environment_variables__(entry)
            release_paths = __get_release_path_list__(entry)
            if release_paths is not None:
                print entry.name
                for release in release_paths: 
                    print release
        #If there's no match to any of the keys, then we don't care about this entry
        except TypeError:
            continue
        #If the job doesn't have the variables we're looking for, skip over it
        except InvalidEntryError:
            continue

if __name__ == "__main__":
    destroy_artifacts(IS_DRY_RUN)


    
