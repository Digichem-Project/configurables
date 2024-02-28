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
    except (ValueError, TypeError):
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