import sys,os,re
from maestro.jenkins.jobs import EnvironmentVariableJobEntry
from maestro import string

class SigniantRemoteArtifactJobEntry(EnvironmentVariableJobEntry):

    #Listed project branch
    project_branch = None

    #Listed project family
    project_family = None

    #Listed project title
    project_title = None

    def __init__(self,config_file = None, verbose = False, debug = False):

        self.super = super(SigniantRemoteArtifactJobEntry, self)

        self.super.__init__(config_file, verbose, debug)

        try:
            #Set some of the conveniece members
            self.jenkins_config_file_path = config_file
            self.jenkins_build_path = os.path.join(os.path.dirname(config_file) + "/builds")
            self.project_family = self.environment_variables["PROJECT_FAMILY"]
            self.project_title = self.environment_variables["PROJECT_TITLE"]
            self.project_branch = self.environment_variables["PROJECT_BRANCH"]
        
        #Fatal Exception when trying to find an environment variable
        except(IndexError,KeyError):
            if debug is True:
                print "ERROR: It appears that the job using " + config_file + " is missing an environment variable required by this class."
            raise InvalidEntryError("This entry does not have the proper environment variables!") 

    def get_release_path_list(self, release_location_keys, verbose = False, debug = False):

        releases = list()
        for key in release_location_keys:
            try:
                string_replace = {"$PROJECT_FAMILY":self.project_family, "$PROJECT_TITLE":self.project_title, "$PROJECT_BRANCH":self.project_branch}
                formatted_release_path = string.replaceall(string_replace, self.environment_variables[key])
                releases.append(formatted_release_path)
            except KeyError as e:
                if debug:
                    print "Job doesn't contain " + key
                pass
            except ValueError as e:
                if debug:
                    print "Job doesn't contain " + key
                pass
        if len(releases) == 0:
            return None
        else:
            return releases

