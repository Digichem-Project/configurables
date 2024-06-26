from configurables.defres import Default, defres
import configurables.exception


#########################
# Function Definitions. #
#########################
def _resolve_value_default(option_names, value):
    if isinstance(value, Default):
        if len(option_names) > 0:
            return option_names[:-1], option_names[-1]
        
        else:
            raise ValueError("Missing argument 'value'")
    
    else:
        return option_names, defres(value)


def setopt(configurable_or_option, *option_names, value = Default(None)):
    """
    Set an option into an optionally nested dict.
    """
    option_names, value = _resolve_value_default(option_names, value)        
    
    if len(option_names) > 1:
        if getattr(configurable_or_option, 'is_configurable', False):
            # Base is a configurable.
            setopt(getattr(configurable_or_option, option_names[0]), *option_names[1:], value = value)
            
        else:
            # Base is a dict.
            if option_names[0] not in configurable_or_option:
                configurable_or_option[option_names[0]] = {}
            
            setopt(configurable_or_option[option_names[0]], *option_names[1:], value = value)
    
    else:
        if getattr(configurable_or_option, 'is_configurable', False):
            # Base is a configurable.
            setattr(configurable_or_option, option_names[0], value)
        
        else:
            # Base is a dict.
            configurable_or_option[option_names[0]] = value

        
def appendopt(dict_obj, *option_names, value = Default(None)):
    """
    Append a value to a list-like item in an optionally nested dict.
    """
    option_names, value = _resolve_value_default(option_names, value)
    
    if len(option_names) > 1:
        if option_names[0] not in dict_obj:
            dict_obj[option_names[0]] = {}
        
        appendopt(dict_obj[option_names[0]], *option_names[1:], value = value)
    
    else:
        try:
            # Add to the list.
            dict_obj[option_names[0]].append(value)
        
        except (AttributeError, KeyError):
            # No list yet, create one.
            dict_obj[option_names[0]] = [value]


def getopt(configurable_or_option, *option_names, default = Default(None)):
    """
    Get an option from a Configurable (or Options objects).
    
    :param configurable_or_option: A Configurable or Options objects to get from.
    :param option_names: A number of names specifying the path to the option. If more than one item is given, each subsequent item specifies a sub option of the previous.
    :param default: If given and the option could not be found, return this instead.
    """
    try:
        # Check if our base is a Configurable or not.
        if getattr(configurable_or_option, 'is_configurable', False):
            current = getattr(configurable_or_option, option_names[0])
    
        else:
            current = configurable_or_option[option_names[0]]
            
    except (AttributeError, KeyError, configurables.exception.Configurable_option_exception):
        if isinstance(default, Default):
            raise AttributeError("Missing sub option '{}'".format(option_names[0])) from None
        
        else:
            return defres(default)
        
    if len(option_names) == 1:
        return current
    
    else:
        return getopt(current, *option_names[1:], default = default)
    

def hasopt(configurable_or_option, *option_names):
    """
    Determine whether a configurable (or Options object) has a sub-option.
    """
    try:
        getopt(configurable_or_option, *option_names)
        
        return True
    
    except Exception:
        
        return False