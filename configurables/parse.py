"""
Code for loading Configurables from saved file locations.
"""

import itertools
import glob

import yaml

from silico.configurable.util import hasopt, getopt, setopt, appendopt
from silico.configurable.loader import Update_loader, Partial_loader,\
    Single_loader, Configurable_list
from silico.configurable.exception import Configurable_loader_exception


def parse_loaders(definitions):
    """
    Load a number of linked Configurable loaders from file.
    
    The Loaders to read are given by the definitions argument, which is a dict of lists.
    Each key of the dict should be a string identifying the TYPE of the loader to read (which should match the CLASS_NAME of the parent class to load).
    Each item/list should contain the ordered locations to read from. Later entries will have higher precedence over earlier ones.
    
    :param definitions: Definitions to load.
    :returns: A dictionary of Configurable_list objects. Each key will match that given in definitions.
    """
    parsers = {}
    
    # Iterate through each configurable type.
    for TYPE, folders in definitions.items():
        # Load from the location and add to our silico_options object.
        # The name of the attribute we add to is the same as the location we read from, but in lower case...
        try:
            parser = Configurables_parser(*folders, TYPE = TYPE)
            parser.parse()
            parsers[TYPE] = parser
        
        except FileNotFoundError:
            # No need to panic.
            pass
    
    done = {parser_type: Configurable_list([], parser_type) for parser_type in parsers.keys()}
    
    children = None
    for index, (TYPE, parser) in enumerate(reversed(parsers.items())):
        # First, link any parents.
        try:
            parents = parsers[list(parsers.keys())[index -1]].loaders
        
        except IndexError:
            parents = []
        
        # Process parents and previous.
        parser.process_parents(parser.has_parents, parents, "parents")
        parser.process_parents(parser.has_previous, parser.loaders, "previous")
        
        # Now process fully.
        loaders = parser.process(children)
        
        # Add to config object.            
        # TODO: This is a bit weird, could do with a cleaner interface to add more loaders.
        done[TYPE].NEXT.extend(loaders)
        
        # Save children for next iteration.
        children = done[TYPE]
        
    return done


class Configurables_parser():
    """
    Reads and parses all configurable files from a location.
    """
    
    def __init__(self, *paths, TYPE):
        """
        Constructor for Configurables_loader object.
        
        :param paths: Paths to  directories to load .yaml files from. All *.yaml files under each directory will be loaded and processed.
        :param TYPE: The TYPE of the configurables we are loading; this is a string which identifies the type of the configurables (eg, Destination, Calculation etc).
        """
        self.root_directories = paths
        # A type to set for all configurables we load.
        self.TYPE = TYPE
        # A list of the configurable loaders we have parsed.
        self.loaders = []
        # Configs that update other configs.
        self.updates = []
        # Configs that have a link:parents set.
        # This is a list of tuples where the first item is the loader and the second is the list of parent tags.
        self.has_parents = []
        # A similar list but for configs with a link:previous set.
        # link:previous and link:parents work on the same principle, the difference being link:previous refers to loaders of the same type (other calculations for example),
        # while link:parents refers to loaders of a different type (programs being referenced from a calculation, for example).
        self.has_previous = []
            
    def parse(self):
        """
        Read and parse all .yaml files within our directory.
        """
        # Get our file list; all files within our top directory which end in .yaml.
        file_list = itertools.chain( *(sorted(glob.glob(glob.escape(root_directory) + "/**/*.yaml", recursive = True)) for root_directory in self.root_directories) )
        
        # Now parse them.
        for file_name in file_list:
            try:
                with open(file_name, "rt") as file:
                    # Parse each.
                    for config in yaml.safe_load_all(file):
                        if config is None:
                            continue
                        
                        # Before we do anything else, process the namespace option (if given).
                        # This automatically alters the tag, alias, next, and previous options.
                        self.process_namespace(config)
                        
                        # If the config has its link:type set to update, file it away separately.
                        if getopt(config, "link", "type", default = None) == "update":
                            # An update, no need to pre process.
                            self.updates.append(Update_loader(file_name, self.TYPE, config))
                        
                        else:
                            # Normal config, pre process and add.
                            loader = self.pre_process(config, file_name)
                            self.loaders.append(loader)
                            
                            # If the loader has link:parents set, add it to our list.
                            if hasopt(loader.config, "link", "parents"):
                                self.has_parents.append((loader, loader.config["link"]['parents']))
                            
                            if hasopt(loader.config, "link", "previous"):
                                self.has_previous.append((loader, loader.config["link"]['previous']))
                    
            except FileNotFoundError:
                # This should be ok to ignore, just means a file was moved inbetween us looking how many files there are and reading them.
                # Possibly no need to worry about this?
                pass
    
    def process_namespace(self, config):
        """
        Process the namespace option for a config.
        """
        namespace = getopt(config, "link", "namespace", default = None)
        if namespace is None:
            return
        
        # First, if alias has not been set, set it now based on the old tag.
        if not hasopt(config, "link", "alias") and hasopt(config, "link", "tag"):
            setopt(config, "link", "alias", config['link']['tag'])
            
        # Then, add namespace to tag.
        setopt(config, "link", "tag", "{} {}".format(namespace, getopt(config, "link", "tag")))
        
        # Add namespace to next and previous.
        for option in ("next", "previous"):
            if hasopt(config, "link", option):
                config['link'][option] = ["{} {}".format(namespace, item) for item in config['link'][option]]
        
        # Done.
    
    def process(self, children = None):
        """
        Process the config dicts that we have parsed.
        """
        # First, apply any updates.
        for update in self.updates:
            update.update(self.loaders)
                
        # We need to link any partial loaders together.
        for loader in self.loaders:
            loader.link(self.loaders, children = children)
            
        # Next we need to purge partial configurables from the top level list.
        conf_list = [loader for loader in self.loaders if loader.TOP]
        return conf_list
    
    def process_parents(self, loaders, parent_loaders, parents_type = "parents"):
        """
        Process any loaders that have a link:previous/link:parents set.
        
        :param: A list of tuples of loaders that have link:parents or link:previous set.
        :param parent_loaders: A list of loaders that could be referred to.
        :param parents_type: One of either "parents" or "previous".
        """
        for loader, parents in loaders:
            for parent_tag in parents:
                # Find the loader in the parent list that is referenced.
                matching = [parent_loader for parent_loader in parent_loaders if parent_loader.TAG == parent_tag]
                
                # Panic if there were no matches
                if len(matching) == 0:
                    raise Configurable_loader_exception(loader.config, loader.TYPE, loader.file_name, "link:{} tag '{}' could not be found".format(parents_type, parent_tag))
                
                # Add the loader to each of the matching loader's NEXT attr.
                for parent in matching:
                    appendopt(parent.config, "link", "next", value = loader.TAG)
    
    def pre_process(self, config, config_path):
        """
        Convert loaded config dicts to appropriate objects
        """
        setopt(config, "meta", "TYPE", value = self.TYPE)
        
        # First, panic if no TAG is set.
        if getopt(config, 'link', 'tag', default = None) is None:
            raise Configurable_loader_exception(config, self.TYPE, config_path, "missing required option 'link:tag'")
        
        # If we have a sub type set, use that to get the name of the class.
        if getopt(config, "link", "type", default = None) is not None:
            if config['link']['type'] in ["pseudo", "partial"]:
                return Partial_loader(config_path, self.TYPE, config, pseudo = config['link']['type'] == "pseudo")
            
            else:
                # Panic, we don't recognise this sub type.
                raise Configurable_loader_exception(config, self.TYPE, config_path, "link:type '{}' is not recognised".format(config['link']['type']))
            
        else:
            # Use a single loader.
            return Single_loader(config_path, self.TYPE, config)
