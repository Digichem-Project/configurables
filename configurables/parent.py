_child_classes = {}

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
        :param case_insensitive: If true, the search is performed ignoring the cAsE of handle.
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
            # class handles are supposed to be unique to each class, hence we want to bypass normal class inheritance (so children don't inherit class names).
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
    def recursive_subclasses(self, refresh = False):
        """
        Recursively get all the subclasses of this class.
        
        :return: A set of all the classes that descend from this class.  
        """
        global _child_classes
        if self in _child_classes and not refresh:
            return _child_classes[self]

        def get_subclasses_worker(cls):
            return set(cls.__subclasses__()).union(
                sub_class for top_sub_class in cls.__subclasses__() for sub_class in get_subclasses_worker(top_sub_class)
            )
        
        _child_classes[self] = get_subclasses_worker(self)
        return _child_classes[self]