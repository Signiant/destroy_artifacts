"""
destroy_artifacts.py

Goes through current jobs in Jenkins and finds artifacts that have been deleted in Jenkins, but not in the artifact share. Sort of flexible, but it ties into Signiant's current build patterns fairly tightly in some areas.
"""

import sys,os,shutil

reload(sys)  
sys.setdefaultencoding('utf8')

from getopt import getopt,GetoptError
from argparse import ArgumentParser
from ConfigParser import RawConfigParser
from maestro.jenkins.jobs import EnvironmentVariableJobEntry, InvalidEntryError
from maestro.tools import string, path

## Globals used throughout the script

VERBOSE = False
DEBUG = False

#ARG: Which Jenkins instance are we targetting? 
JENKINS_JOBS_DIRECTORY_PATH = "/var/lib/jenkins/jobs"

#ARG: Don't actually delete anything, but list what would be deleted
IS_DRY_RUN = False

#ARG: Where is the config file stored?
CONFIG_PATH = "./config"

#CONFIG: REQUIRED environment variables
ENVIRONMENT_VARIABLES = []

#CONFIG: Environment Variables potentially containing deployment paths (i.e. paths to search for builds)
#The script will attempt to replace $VARIABLES with their corresponding value from ENVIRONMENT_VARIABLES
DEPLOYMENT_PATHS = []

#CONFIG: REGEX to apply to the subfolders of the deployment directorys. (i.e. {[0-9]+} )
BUILD_FOLDER_REGEX = ""

#CONFIG: Jobs to ignore (use the job name)
IGNORE_JOBS = []

#CONFIG: Where to split the deployment paths, the script takes the second index ( [1] ) 
#Signiant: Default in config is to split on $PROJECT_FAMILY
SPLIT_TOKEN = ""

#CONFIG: What to prepend to the string[1] from deployment path split with SPLIT_TOKEN
#Signiant: Default in config is to 
PREPEND_STRING = ""

#CONFIG: What to append to the  string[1] frpm deployment path split with SPLIT_TOKEN
APPEND_STRING = ""

#Tracks dupicates by having $PROJECT_FAMILY:$PROJECT_TITLE:$PROJECT_BRANCH as a key, and the name of the entry as a value (for error messaging)
__duplicate_tracker__ = dict()

#List of found duplicates
__duplicates__ = list()

#We pass in undeleted_paths set in order to avoid duplicates, and get an accurate byte clean up count
#Makes it fairly slow, but whatever. It's still under a minute for scanning the entire thing

def __get_undeleted_artifact_paths__(entry, release_paths, undeleted_paths_dict = None):
    """
    Loop through release paths and see if we can find anything with Build-XXX, strip the number out and compare to the job entry. Put all ones not in the job entry into a set.
    """
    if not isinstance(entry, EnvironmentVariableJobEntry) or entry is None:
        raise TypeError("You must pass in a EnvironmentVariableJobEntry!")
    if undeleted_paths_dict is None:
        undeleted_paths_dict = dict()
    for path in release_paths:
        #TODO: Find a better way to do this
        #We need to strip off any deploy path that has Build-$BUILD_NUMBER at the end
        if path.endswith("$BUILD_NUMBER"):
            #This is kind of neat. Prepend a slash, and unpack the list returned from path.split without the last element and join it
            path = os.path.join("/",*path.split("/")[:-1]) 
        try:
            for subdir in os.listdir(path):
                try:
                    #TODO: Find a better way to do this (dont rely on Build-XXX)
                    build_no = subdir.split("-")[1]
                    if build_no not in entry.get_build_number_list():
                        #print str(entry.get_build_number_list()) + "  " + str(build_no)
                        undeleted_paths_dict[os.path.join(path,subdir)] = entry
                except IndexError as e:
                    #Unrecognized build directory
                    #print e
                    continue
        except OSError as e:
            #There are no deployed artifacts for this directory
            #print e
            continue
    return undeleted_paths_dict

def __enumerate_remote_artifact_config_entries__(jobs_path):
    """
    Loop through the found config.xml files and return their folder path
    """
    for root, dirnames, filenames in os.walk(jobs_path):
        if "config.xml" in filenames:
            try:
                #print root
                yield EnvironmentVariableJobEntry(root)
            except InvalidEntryError as e:
                if VERBOSE == 1:
                    print "Skipping over " + str(root)

def __parse_config__(config_file_path):
    """
    Parses the config file and sets the globals.
    """
    global ENVIRONMENT_VARIABLES
    global DEPLOYMENT_PATHS
    global DEPLOYMENT_STRUCTURES
    global BUILD_FOLDER_REGEX
    global IGNORE_JOBS
    global SPLIT_TOKEN
    global PREPEND_STRING
    global APPEND_STRING

    config = RawConfigParser()
    config.read(config_file_path)
    # I wrapped these in trys just in case we want something optional 
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
        BUILD_FOLDER_REGEX = config.get("ArtifactConfig","BUILD_FOLDER_REGEX")
    except:
        raise
    try:
        IGNORE_JOBS = config.get("ArtifactConfig","IGNORE_JOBS").split(',')
    except:
        raise
    try:
        SPLIT_TOKEN = config.get("ArtifactConfig","SPLIT_TOKEN")
    except:
        raise
    try:
        PREPEND_STRING = config.get("ArtifactConfig","PREPEND_STRING")
    except:
        raise
    try:
        APPEND_STRING = config.get("ArtifactConfig","APPEND_STRING")
    except:
        raise

def __verify_environment_variables__(entry):
    """
    Checks for the required environment variables from ENVIRONMENT_VARIABLES, and will raise an InvalidEntryError if one is not found or is None.
    """
    if not isinstance(entry,EnvironmentVariableJobEntry):
        raise TypeError("Received object of type " + str(type(environment_variable_job)) + " expected type SigniantRemoteArtifactJobEntry.")
    for var in ENVIRONMENT_VARIABLES:
        if entry.name == "Media Shuttle Store-mjc":
            print str(entry.environment_variables.keys())
        if var not in entry.environment_variables.keys() or entry.environment_variables[var] is None:
            raise InvalidEntryError("Required environment variable " + str(var) + " was not found in job entry " + str(entry.name) + ".")
       
def __get_release_path_list__(entry):
    """
    Builds a string replace dictionary out of the environment variables, calls __strip_release_path__, replaces the $VARIABLES with their values (if found), normalizes the path and adds it to a list which is returned by this method.
    """
    releases = list()
    for key in DEPLOYMENT_PATHS:
        try:
            string_replace = dict()
            for var in ENVIRONMENT_VARIABLES:
                try:
                    string_replace[str("$" + var)] = entry.environment_variables[var]
                except KeyError:
                    continue
            converted_release_path = __strip_release_path__(entry.environment_variables[key])
            if converted_release_path is None:
                continue
            replaced_release_path = string.replaceall(string_replace, converted_release_path)
            formatted_release_path = os.path.normpath(replaced_release_path)
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
    """
    Currently unused and uses defaults defined above
    """
    global IS_DRY_RUN
    try:
        if sys.argv[1] == "-n" or sys.argv[1] == "--dry-run":
            IS_DRY_RUN = True
    except IndexError:
        #Not a dry run..
        pass

def __strip_release_path__(release_path):
    """
    Converts UNC/Windows paths into forward slashes, and then splits and pre/appends
    """

    try:
        clean_path = release_path.replace('\\','/')
#        converted_path = os.path.abspath(clean_path)
        stripped_path = clean_path.split(SPLIT_TOKEN)
        return PREPEND_STRING + stripped_path[1] + APPEND_STRING
    except:
        return None
    

def destroy_artifacts():
    if not os.path.exists(CONFIG_PATH):
        raise ValueError("You need to provide a valid config file! Currently looking for: " + str(CONFIG_PATH))

    #Parse arguments
    __parse_arguments__()

    #Parse config file
    __parse_config__(CONFIG_PATH)
	
    #Bytes cleaned up
    cleaned_byte_count = 0

    #Set containing ALL the paths to be deleted
    undeleted_paths_dict = dict()

    #First we want to go through the config entries that contain Environment Variables from envinject
    for entry in __enumerate_remote_artifact_config_entries__(JENKINS_JOBS_DIRECTORY_PATH):
        #Safety net... if there's NO builds, we shouldn't clean anything up
        if entry.get_build_number_list() is None or len(entry.builds_in_jenkins) == 0:
            continue
        try:
            __verify_environment_variables__(entry)
            __verify_duplicates__(entry)
            release_paths = __get_release_path_list__(entry)
            if release_paths is not None:
                for undeleted_artifact_path in __get_undeleted_artifact_paths__(entry,release_paths,undeleted_paths_dict):
                    pass #Building set...
        #If there's no match to any of the keys, then we don't care about this entry
        except TypeError as e:
            #print str(e)
            continue
        #If the job doesn't have the variables we're looking for, skip over it
        except InvalidEntryError as e:
            #print str(e)
            continue

    #Loop through the (now) unique path list so we can get the size and delete
    for artifact_path in undeleted_paths_dict.keys():
        if undeleted_paths_dict[artifact_path].name in __duplicates__:
            print "Not deleting duplicate: " + artifact_path
        print "Deleting " + str(artifact_path)
        cleaned_byte_count = path.get_tree_size(artifact_path) + cleaned_byte_count
        if not IS_DRY_RUN:
            shutil.rmtree(artifact_path)

    if IS_DRY_RUN:
        print "Would have cleaned up " + str(cleaned_byte_count) + " bytes!"
    else:
        print "Cleaned up " + str(cleaned_byte_count) + " bytes!"

    if len(__duplicates__) > 0:
        print "The job failed because of the following errors:"
        for duplicate in __duplicates__:
            key = str(duplicate.environment_variables["PROJECT_FAMILY"] + "/" + duplicate.environment_variables["PROJECT_TITLE"] + "/" + duplicate.environment_variables["PROJECT_BRANCH"])
            print "Attempted to parse entry with name '" + str(duplicate.name) + "' but entry with name '" + str(__duplicate_tracker__[key]) + "' is currently using the same deployment strategy: " + key
        sys.exit(1)

#TODO: Make less Signiant specific
def __verify_duplicates__(entry):
    global __duplicate_tracker__
    global __duplicates__

    # Key is all environment variables seperated by a colon
    key = str(entry.environment_variables["PROJECT_FAMILY"] + "/" + entry.environment_variables["PROJECT_TITLE"] + "/" + entry.environment_variables["PROJECT_BRANCH"])
    #Check for duplicate
    if key in __duplicate_tracker__.keys():
        __duplicates__.append(entry)
        raise InvalidEntryError("Found a duplicate entry! Please see error message at the end of the script.")
    else:
        __duplicate_tracker__[key] = entry.name

if __name__ == "__main__":
    destroy_artifacts()


    
