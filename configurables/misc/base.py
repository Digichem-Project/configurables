import argparse

def to_bool(booly):
    """
    Convert something that might be a bool into a bool.
    """
    if type(booly) is str:
        # Convert to lowercase.
        booly = booly.lower()
        if booly in ["yes", "1", "one", "true"]:
            return True
        elif booly in ["no", "0", "zero", "false"]:
            return False
        else:
            raise Exception("Could not convert '{}' to bool".format(booly))
    else:
        return bool(booly)
    
def to_number(value):
    """
    Convert a variable to an int or float representation.
    """
    try:
        return int(value)
    
    except ValueError:
        pass
    
    return float(value)
    
def is_number(value):
    """
    Determine whether a variable has a valid int or float representation.
    """
    return is_float(value) or is_int(value)

def is_float(value):
    """
    Determine whether a variable has a valid float representation.
    
    :returns: True or False.
    """
    try:
        float(value)
        return True
    except (TypeError, ValueError):
        return False

def is_int(value):
    """
    Determine whether a variable has a valid integer representation.
    
    :returns: True or False.
    """
    try:
        int(value)
        return True
    except ValueError:
        return False
    
def is_iter(value):
    """
    Determine whether a variable is iterable.
    
    :returns: True or False.
    """
    try:
        iter(value)
        return True
    except TypeError:
        return False
    

class Dynamic_parent():
    """
    A mixin class for classes that can recursively get all known children.
    """
    
    # An iterable of strings that identify this class.
    CLASS_HANDLE = []
    
    @classmethod
    def from_class_handle(self, handle, case_insensitive = True):
        """
        Get a class that is a child of this class from its human-readable name/handle.
        
        :raises ValueError: If a class with name could not be found.
        :param handle: The handle of the class to get (this is defined by this class itself).
        :paran case_insensitive: If true, the search is performed ignoring the cAsE of handle.
        :return: The class.
        """
        # Our known classes.
        known_classes = self.recursive_subclasses()
        
        # Convert to lower case if we're doing a case insensitive search.
        if case_insensitive:
            handle = handle.lower()
            
        # Keep track of found matches.
        found = []
        
        # Get the class we've been asked for.
        for known_class in known_classes:
            # Get the current class' list of handles.
            # class handles are supposed to be unqiue to each class, hence we want to bypass normal class inheritance (so children don't inherit class names).
            # Thus we look directly in the class's vars/__dict__.
            class_handles = vars(known_class).get('CLASS_HANDLE', [])
            
            # If the handle is a single string, panic.
            if isinstance(class_handles, str):
                raise TypeError("CLASS_HANDLE of class '{}' is a single string; CLASS_HANDLE should be an iterable of strings".format(known_class.__name__))
            
            # Convert to lower case if we're doing a case insensitive search.
            if case_insensitive:
                class_handles = [cls_handle.lower() for cls_handle in class_handles]
            
            # See if we have a match.    
            if handle in class_handles:
                # Got a match.
                found.append(known_class)
        
        
        if len(found) == 0:
            # No class.
            raise ValueError("No {} class with name '{}' could be found".format(self.__name__, handle))
        
        elif len(found) > 1:
            # Too many.
            raise ValueError("Found multiple classes with name '{}': {}".format(handle, ", ".join(str(cls) for cls in found)))
        
        else:
            return found[0]
        
    @classmethod
    def known_handles(self):
        """
        Get a list of names that can be used to identify children of this class.
        """
        handles = []
        for known_class in self.recursive_subclasses():
            class_handles = vars(known_class).get('CLASS_HANDLE', [])
            
            if len(class_handles) > 0:
                handles.append(class_handles[0])
                
        return sorted(handles)
    
    @classmethod
    def recursive_subclasses(self):
        """
        Recursively get all the subclasses of this class.
        
        :return: A set of all the classes that descend from this class.  
        """
        def get_subclasses_worker(cls):
            return set(cls.__subclasses__()).union(
                [sub_class for top_sub_class in cls.__subclasses__() for sub_class in get_subclasses_worker(top_sub_class)]
            )
            
        return get_subclasses_worker(self)
    

class List_grouper(argparse.Action):
    """
    Custom action class that groups lists together so we know in what order they were specified.
    """    
    
    def __init__(self, option_strings, *args, **kwargs):
        """
        """
        argparse.Action.__init__(self, option_strings, *args, **kwargs)
        # We'll give ourself a name so we also group no matter which of our option_strings is used.
        self.name = [name for name in option_strings if name[:2] == "--"]
    
    def __call__(self, parser, namespace, values, option_string=None):
        """
        """
        grouped_list = {
            'group': self,
            'values': values
        }
        try:
            getattr(namespace, self.dest).append(grouped_list)
        except AttributeError:
            setattr(namespace, self.dest, [grouped_list])