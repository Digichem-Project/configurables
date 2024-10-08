import itertools
import yaml
import textwrap
import math
import collections
from datetime import timedelta, datetime
import re

from configurables.exception import Configurable_option_exception,\
    Missing_option_exception, Disallowed_choice_exception
from configurables.defres import Default, defres
from configurables.misc import is_number


class InheritedAttrError(AttributeError):
    """
    Exception raised when an inherited attribute cannot be found.
    """

class Nested_dict_type(collections.UserDict):
    """A data type for generic nested dicts."""
    
    def __init__(self, text = ""):
        if isinstance(text, dict):
            data = text
            
        elif isinstance(text, type(self)):
            data = text.value
            
        else:
            data = yaml.safe_load(text)
            if data is None:
                data = {}
                
            elif not isinstance(data, dict):
                raise TypeError("Cannot convert string '{}' of converted type '{}' to dict".format(data, type(data)))
            
        super().__init__(data)
    
    @property
    def value(self):
        return self.data
    
    def __str__(self):
        if len(self.data) == 0:
            return ""
        else:
            return yaml.safe_dump(self.data)
        
class Duration():
    """
    Simple type class for recording time durations.
    """
    
    def __init__(self, value):
        # Value could be a Duration object, a timedelta object, a number of seconds, or a duration string.
        if isinstance(value, type(self)):
            self.duration = value.duration
        
        elif isinstance(value, timedelta):
            self.duration = value
        
        elif is_number(value):
            seconds = float(value)
            self.duration = timedelta(seconds = seconds)
            
        else:
            reg = re.compile(r"^([0-9]+-)?([0-9]+):([0-9]+)(:[0-9]+)?$")
            time_match = reg.match(value)
            
            if time_match is None:
                raise ValueError("Failed to parse time string '{}'".format(value))
            
            if time_match.groups()[0] is None:
                days = 0
            
            else:
                days = int(time_match.groups()[0][:-1])
                
            hours = int(time_match.groups()[1])
            minutes = int(time_match.groups()[2])
            
            if time_match.groups()[3] is None:
                seconds = 0
            
            else:
                seconds = int(time_match.groups()[3][1:])
            
            self.duration = timedelta(days = days, hours = hours, minutes = minutes, seconds = seconds)
            
    def to_string(self, include_days = True):
        """
        """
        hours = math.floor(self.duration.seconds / 3600)
        
        minutes = math.floor((self.duration.seconds - hours * 3600) / 60)
        seconds = round(self.duration.seconds - (hours * 3600 + minutes * 60))
        
        if include_days:
            return "{}-{:02d}:{:02d}:{:02d}".format(self.duration.days, hours, minutes, seconds)
        
        else:
            # Wrap days into hours.
            hours += self.duration.days *24
            return "{:02d}:{:02d}:{:02d}".format(hours, minutes, seconds)
    
    def __str__(self):
        """
        """
        return self.to_string()
        


class Option():
    """
    Class for specifying an option in a configurable.
    
    Options are descriptors that perform type checking and other functionality for Configurables; they expose the options that a certain configurable expects.
    """
    
    def __init__(self, name = None, *, default = Default(None), help = Default(None), choices = Default(None), validate = Default(None), list_type = Default(None), type = Default(None), type_func = Default(None), exclude = Default(None), required = Default(False), no_none = Default(None), none_to_default = Default(False), no_edit = Default(False), dump_func = Default(None), edit_vtype = Default(None), data_func = Default(None)):
        """
        Constructor for Configurable Option objects.
        
        :param name: The name of this option. If None is given this will be determined automatically from the name of the attribute this option is stored under.
        :param default: Default value for this option. Alternatively, default can be a callable which will be called with 2 arguments: this Option object and the owning Configurable object and should return the default value. Be careful about setting mutable options (eg, lists, dicts) as default, if one object modifies the object this will be propagated to all objects that have this option.
        :param help: Descriptive help string
        :param choices: An optional iterable of valid choices for this option.
        :param validate: Function called to check that the given value is valid. The function will be called with 3 arguments: this Option object, the owning Configurable object and the value being set, and should return True or False as appropriate.
        :param list_type: If given, indicates that this option should accept a number of elements which will be stored in an object of type list_type (commonly list or tuple, but anything with a similar interface should work). If list_type and type are both given, then type will be used to set the type of each element in the list.
        :param type: A callable that is used to set the type of value.
        :param type_func: An alternative and more powerful type conversion function than 'type'. A function that will be called with 3 arguments: this Option object, the owning Configurable object and the value being set, and should return a converted type of the value.
        :param exclude: A list of strings of the names of attributes that this option is mutually exclusive with.
        :param required: Whether this option is required or not.
        :param no_none: Whether to allow None values. This defaults to False unless required == True, in which case no_none defaults to True.
        :param none_to_default: Whether to convert None values to the default value. False by default.
        :param no_edit: Flag to indicate that this option shouldn't be edited interactively by the user, useful for 'hidden' options that don't make sense to be changed for example.
        :param dump_func: An optional function that will be called to serialize the data of this option ready for dumping to file. The function will be called with 3 arguments: this Option object, the owning Configurable object and the value being set, and should return the value to save.
        :param edit_vtype: An optional explicit string denoting the interactive editor to use for this option.
        :param data_func: A (pseudo) optional function that can be used to retrieve data about the option for editing purposes. Certain edit_vtype options will require this function.
        """
        # Certain constructor arguments can be inherited from a parent Options object if they're not given.
        # Because of this, we check whether they are in kwargs rather than specifying them explicitly, and
        # set a flag not to inherit them if they're not given.
        # Args to inherit from parent.
        self._inherit = []
        
        for arg_name, arg_value in {
            "_default": default,
            "help": help,
            "choices": choices,
            "_validate": validate,
            "list_type": list_type,
            # Type is handled by type_func.
            #"type": type,
            "type_func": type_func,
            "exclude": exclude,
            "required": required,
            "no_none": no_none,
            "none_to_default": none_to_default,
            "no_edit": no_edit,
            "dump_func": dump_func,
            "edit_vtype": edit_vtype,
            "data_func": data_func
        }.items():
            if isinstance(arg_value, Default):
                self._inherit.append(arg_name)
        
        self.name = name
        # TODO: Need to be smarter about storing mutable objects (most notable, list and dict, normally empty ones) as default
        # When a default is accessed, it is this actual object that is returned, hence modifications would be shared by all configurable options of the same type.
        # Perhaps a solution is to on demand copy() the default and store the resulting clone?
        self._default = defres(default)
        self.list_type = defres(list_type)
        #self.type = type
        self.help = defres(help)
        self.choices = defres(choices) if defres(choices) is not None else []
        self._validate = defres(validate) if defres(validate) is not None else self.default_validate
        self.exclude = defres(exclude) if defres(exclude) is not None else []
        if isinstance(self.exclude, str):
            self.exclude = [self.exclude]
        self.required = defres(required)
        self.no_edit = defres(no_edit)
        self.dump_func = defres(dump_func)
        if defres(no_none) is None:
            self.no_none = self.required
        else:
            self.no_none = defres(no_none)
        self.none_to_default = defres(none_to_default)
        self.edit_vtype = defres(edit_vtype)
        # This part of the interface is a bit WIP and might change, this function is used to retrieve data for certain setedits that need it.
        # Currently this is only used for method pickers, which use the data func to retrieve the 'list' of methods to pick from.
        self.data_func = defres(data_func)
        
        # Deal with type and type_func.
        type = defres(type)
        type_func = defres(type_func)
        if type is not None and type_func is not None:
            raise ValueError("type and type_func cannot be specified together")
        
        elif type is not None:
            # Wrap the type function in a wrapper.
            def wrapper_type(option, configurable, value):
                return type(value)
            
            self.type_func = wrapper_type
            
            # If we also don't have a edit_vtype, use this type.
            if self.edit_vtype is None:
                self.edit_vtype = type.__name__
        
        else:
            self.type_func = type_func
            
        
        # If we are a list_type and a default of None has been given, change the default to an empty list.
        if self.list_type is not None and self._default is None:
            self._default = []
        
        # If we are a sub-object (ie, part of a dict), this is a hierarchy of names of the Options object we are owned by.
        self.parents = []
        
        # By definition, Options that are required can have no default, so we'll delete this attribute.
        if self.required:
            del(self._default)

    def __set_name__(self, owning_cls, name):
        """
        Called automatically during class creation, allows us to know the attribute name we are stored under.
        """
        self.name = name if self.name is None else self.name
        
        # Inherit some options from our parent.
        for attr_name in self._inherit:
            try:
                setattr(self, attr_name, self.get_inherited_attribute(owning_cls, attr_name))
                
            except InheritedAttrError:
                # Nothing to inherit.
                pass
            
            except AttributeError:
                # The _default attribute will be missing if this option is required (and so has no default).
                # TOOD: Fix this hack.
                if attr_name == "_default":
                    pass
                
                else:
                    raise
    
    def get_inherited_attribute(self, owning_cls, attr_name):
        """
        Get an attribute that is inherited from a parent Options object.
        
        :param owning_obj: The owning class on which this Option object is set as a class attribute.
        :param attr_name: The name of the attribute to inherit.
        :raises InheritedAttrError: If the attribute could not be found.
        :returns: The attribute.
        """
        try:
            base_options, mro = self.get_base_option(owning_cls)
            return getattr(base_options, attr_name)
         
        except InheritedAttrError:
            raise InheritedAttrError(attr_name) from None
    
    
    def get_base_option(self, owning_cls, _mro = None):
        """
        Get the base Options object from which this Options object inherits attributes.
        
        :param owning_obj: The owning class on which this Option object is set as a class attribute.
        :param: _mro: The method resolution order, a list of classes to inherit from. This argument is used in recursion to walk further back up the hierarchy. If not given, the mro of owning_cls is used.
        :returns: A tuple, where the first item is the found Options object (or None if one could not be found), and the second is the current mro.
        """
        # The full 'access' path to this option.
        # This will consist of an attribute access as the first item,
        # eg: obj.option
        # followed by a number of dict like accesses to a specific option,
        # eg: obj.option['sub1']['sub2']
        resolve_path = [part.name for part in itertools.chain(self.parents, (self,))]
        
        # The 'parent' class of our owning class.
        # Decide which parent class to look at.
        # We do this by walking up the method resolution order of our owning_cls,
        # which we keep track of via the recursive argument _mro.
        if _mro is None:
            _mro = list(owning_cls.__mro__[1:])
        
        # Here, we are not actually interested in the value of the option,
        # but rather the Option(s) object itself.
        # Hence we access via the base class itself, rather than using super().
        try:
            parent_cls = _mro.pop(0)
        
        except IndexError:
            # We've exhausted the mro, give up.
            raise InheritedAttrError() from None
        
        try:
            # Need to be careful here, mixin classes might not inherit from Options_mixin, and so might not have get_cls_option.
            current = parent_cls.get_cls_option(resolve_path[0])
                
        except (ValueError, AttributeError):
            # The class either doesn't have a get_cls_option function,
            # or doesn't have the option we're looking for.
            # No option in this class.
            # Go again.
            return self.get_base_option(owning_cls, _mro)
            
        # Walk up the nested Options object to find ourself.
        try:
            for resolve_part in resolve_path[1:]:
                current = current._options[resolve_part]
        
        except KeyError:
            # Couldn't walk all the way up the path, try again from the next base class.
            # Doing nothing will loop us around again.
            return self.get_base_option(owning_cls, _mro)
        
        else:
            # Got our option.
            # stop for now.
            return current, _mro
            
    @property
    def num_child_options(self):
        """
        The number of child/sub options contained within this one. For 'normal' options, this is always 0.
        """
        return 0
    
    def default_validate(self, option, configurable, value):
        """
        A function used as the default for _validate; always returns True
        """
        return True
    
    @property
    def full_name(self):
        """
        The full name/path of this option, including any parents.
        """
        return ": ".join(itertools.chain([parent.name for parent in self.parents], (self.name,)))
            
    def add_parent(self, parent):
        """
        Add an owning parent Options object to this Option object.
        
        This method is called by the parent Options object when this Option is added to it.
        """
        self.parents.insert(0, parent)

    def __get__(self, owning_obj, cls = None):
        """
        Compute/retrieve the value of this option.
        """
        if owning_obj is None:
            return self
        
        return self.get_from_dict(owning_obj, owning_obj._configurable_options)
    
    def dump(self, owning_obj, dict_obj, explicit = False):
        """
        Dump the value of this option so it can be serialised (for example, to yaml).
        
        :param explicit: If True, all values will be dumped. If False, only non-default values will be dumped.
        :returns: A dumped version of this option's value.
        """
        value = self.get_from_dict(owning_obj, dict_obj)
        if self.dump_func is not None:
            return self.dump_func(self, owning_obj, value)
        
        # TODO: Review this.
        elif value.__class__.__module__ not in ('__builtin__', 'builtins'):
            return str(value)
        
        elif self.list_type is not None:
            return self.list_type(
                
                sub_value.dump() if hasattr(sub_value, "is_configurable")
                else dict(value) if isinstance(value, Nested_dict_type)
                else str(sub_value) if sub_value.__class__.__module__ not in ('__builtin__', 'builtins')
                else sub_value
                
                for sub_value in value
            )
        
        else:
            # Tuple's are a constant problem for representation in yaml, because they have no 'native' representation.
            # Normally, we can just get away with converting to a list, but this doesn't work for dict keys, which
            # cannot be lists.
            return value
        
    def describe(self, owning_obj):
        """
        Describe (in a dict) this option, including its type, expected options etc.
        """
        return {
            "name": self.name,
            "help": self.help,
            "choices": self.choices,
            "list_type": self.list_type.__name__ if self.list_type is not None else None,
            "type": self.edit_vtype,
            "required": self.required,
            "no_none": self.no_none
        }
        
    def get_header(self):
        """
        Generate text that describes this option.
        
        The text contains the most-important meta-data about this option, such as it's help message, default value, type etc.
        
        The text is returned as a list of lines (without newlines).
        """
        headers = []
        # Start with help (if we've got it).
        if self.help is not None:
            headers.append(self.help)
        
        # Add type, choices etc.
        property_strings = []
        # Handle type separately, we just want the 'name' of the function.
        if self.type_func is not None:
            property_strings.append("type: {}".format(self.type_func.__name__))
        
        if self.list_type is not None:
            property_strings.append("list_type: {}".format(self.list_type.__name__))
        
        for property_desc, property_name in (("default", "_default"), ("choices", "choices"), ("excludes", "exclude"), ("required", "required")):
            property_value = getattr(self, property_name, None)
            if property_value != None and (not isinstance(property_value, list) or len(property_value) > 0):
                property_strings.append("{}: {}".format(property_desc, property_value))
        
        if len(property_strings) > 0:
            headers.append(", ".join(property_strings))
            
        return headers
    
    def get_template_value(self, owning_cls_or_obj, dict_obj = None, level = 0):
        """
        """
        # The 'value' we use depends on whether we've been given a configurable class or configurable object to use.
        # If we have a class (dict_obj = None), then we have no 'real' value to use, so we'll use a default instead.
        # If we have an object, then we can try and get the 'real' value, which if it isn't set will get the default.
        if dict_obj is None:
            # No dict_obj, we are getting a default value.
            # Check there is a default.
            if hasattr(self, "_default"):
        
                # If our default is a simple value (non-callable), set that as the example.
                default = self._default if not callable(self._default) else ""
                
                if default.__class__.__module__ not in ('__builtin__', 'builtins'):
                    default = str(default)
                
                value = yaml.safe_dump({self.name: default})
                indent_level = 1
            
            else:
                # If the option is required it will have no default set.
                value = "{}: ".format(self.name)
                indent_level = 2 
            
        else:
            # Yes dict_obj, we are getting a real value.
            # NOTE: If this option is expected but not set, this will fail.
            # We could handle this if we wanted...
            #value = "{}: {}".format(self.name, self.dump(owning_cls_or_obj, dict_obj))
            value = yaml.safe_dump({self.name: self.dump(owning_cls_or_obj, dict_obj)})
            # If this is a real value, don't comment.
            indent_level = 2 if not self.is_default(owning_cls_or_obj, dict_obj) else 1
            
        # We include a blank line after our value just for readability.
        return [(level, indent_level, value), (level, 0, " ")]
            
    def dump_template(self, owning_cls_or_obj, dict_obj = None, level = 0):
        """
        Dump an example version of this option.
        
        This example will be in 'commented' yaml format (text), and will contain the following info:
         - Any help associated with the option.
         - Metadata of the option, such as type, choices, default value etc.
         - The name of the option and its default value (for single options), or the sub-options.
        """
        # Get our headers.
        template = [(level, 0, header) for header in self.get_header()]
        
        # Add the 'body' of the option.
        values = self.get_template_value(owning_cls_or_obj, dict_obj, level)
        template.extend(values)
        #template.append((level, False, " "))
                
        if level == 0:
            wrapped_lines = []
            for line_level, indent_level, lines in template:
                for line in lines.split("\n"):
                    if indent_level == 0:
                        # Comment.
                        indent = "  "
                    elif indent_level == 1:
                        # Default value
                        indent = "#"
                    else:
                        # Real value.
                        indent = ""
                    
                    # We only wrap comment lines, real options can't just be broken.
                    wrapped_lines.extend(
                        textwrap.wrap(
                            line,
                            100 if indent_level == 0 else math.inf,
                            replace_whitespace = False,
                            drop_whitespace = False,
                            #initial_indent = indent + "  " * line_level,
                            #subsequent_indent = indent + "  " * line_level
                            initial_indent = indent + "  " * line_level + ("# " if indent_level == 0 else ""),
                            subsequent_indent = indent + "  " * line_level + ("# " if indent_level == 0 else "")
                        )
                    )
            
            return "\n".join(wrapped_lines)
            #return "\n".join(list(itertools.chain(*[textwrap.wrap(template_line, 100, replace_whitespace = False, drop_whitespace = False, initial_indent = ("# " if not is_value else "#") + "  " * level, subsequent_indent = ("# " if not is_value else "#") + "  " * level) for level, is_value, template_line in template])))
        
        else:
            return template

    def get_from_dict(self, owning_obj, dict_obj):
        """
        Compute/retrieve the value of this option which is stored in a given dictionary.
        
        :param owning_obj: The owning object on which this Option object is set as a class attribute.
        :param dict_obj: The dict in which the value of this Option is stored. In most cases, the value of this option is evaluated simply as dict_obj[self.name]
        """
        try:
            dict_obj[self.name]
            val = dict_obj[self.name]
        except KeyError:
            # No value set, return our default value (if we have one).
            try:
                val = self.default(owning_obj)
            except AttributeError:
                # No value set and no default, panic.
                raise Missing_option_exception(owning_obj, self) from None

        return val


    def __set__(self, owning_obj, value):
        """
        Set the value of this option.
        
        :param owning_obj: The owning object on which this Option object is set as a class attribute.
        :param value: The new value to set.
        """
        self.set_into_dict(owning_obj, owning_obj._configurable_options, value)


    def set_into_dict(self, owning_obj, dict_obj, value):
        """
        Set the value of this option into a specified dict object.
        
        :param owning_obj: The owning object on which this Option object is set as a class attribute.
        :param dict_obj: The dict in which the value of this Option is stored. In most cases, the value of this option is evaluated simply as dict_obj[self.name]
        :param value: The new value to set.
        """
        dict_obj[self.name] = value


    def __delete__(self, owning_obj):
        """
        Delete the explicit value of this option, resorting to the default (if one is given).
        
        :param owning_obj: The owning object on which this Option object is set as a class attribute.
        """
        self.set_default(owning_obj, owning_obj._configurable_options)


    def set_default(self, owning_obj, dict_obj):
        """
        Reset this option to default.
        
        Note that this method is an alias for calling del() on this attribute.
        
        :param owning_obj: The owning object on which this Option object is set as a class attribute.
        :param dict_obj: The dict in which the value of this Option is stored. In most cases, the value of this option is evaluated simply as dict_obj[self.name]
        """
        dict_obj.pop(self.name, None)


    def default(self, owning_obj):
        """
        Get the default value of this Option.
        
        :raises AttributeError: If this Option object is required.
        :param owning_obj: The owning object on which this Option object is set as a class attribute.
        """
        if not callable(self._default):
            return self._default
        else:
            return self._default(self, owning_obj)


    def is_default(self, owning_obj, dict_obj):
        """
        Whether the value of this option is currently the default or not.
        
        :param owning_obj: The owning object on which this Option object is set as a class attribute.
        :param dict_obj: The dict in which the value of this Option is stored. In most cases, the value of this option is evaluated simply as dict_obj[self.name]
        """
        return not self.name in dict_obj
    
    def to_type(self, owning_obj, value):
        """
        Wrapper function to convert a value to the type of this option.
        """
        # Uncommenting the following line will prevent setting the type if our value already has the same type.
        # TODO: Review if this is desirable.
        if value is not None and self.type_func is not None:# and (type(self.type) != type or type(value) != self.type):
            return self.type_func(self, owning_obj, value)
        
        else:
            return value

    def validate(self, owning_obj, dict_obj = None):
        """
        Validate the value of this option.
        
        :param owning_obj: The owning object on which this Option object is set as a class attribute.
        :param dict_obj: The dict in which the value of this Option is stored. In most cases, the value of this option is evaluated simply as dict_obj[self.name]
        """
        if dict_obj is None:
            dict_obj = owning_obj._configurable_options
        
        value = self.get_from_dict(owning_obj, dict_obj)
        
        # If we've been asked to, convert None to default.
        if self.none_to_default and value is None:
            self.set_default(owning_obj, dict_obj)
        
        # If our value is None and that's not allowed, panic.
        elif value is None and self.no_none:
            self.set_default(owning_obj, dict_obj)
            raise Configurable_option_exception(owning_obj, self, "value cannot be None")
        
        # Try and set the type.
        if not self.is_default(owning_obj, dict_obj) and value is not None:
            # If we are a list type, convert the type of value and also each element.
            if self.list_type is not None:
                # We'll first check each item, building a new list as we go, then assign to the list type.
                # We do this because some list types (tuple, for example), are immutable.
                try:
                    temp_list = list(value)
                
                except (TypeError, ValueError) as e:
                    raise Configurable_option_exception(owning_obj, self, "value '{}' of type '{}' could not be converted to list".format(value, type(value).__name__)) from e
                
                
                # First, check each element.
                if self.type_func is not None:
                    for index, element in enumerate(temp_list):
                        try:
                            temp_list[index] = self.to_type(owning_obj, element)
                            
                        except (TypeError, ValueError) as e:
                            raise Configurable_option_exception(owning_obj, self, "item '{}') '{}' of type '{}' is of invalid type".format(index, element, type(element).__name__)) from e
                
                # Then convert the list itself.
                try:
                    value = self.list_type(temp_list)
                    
                except (TypeError, ValueError) as e:
                    raise Configurable_option_exception(owning_obj, self, "value '{}' of type '{}' could not be converted to the list-like type '{}'".format(temp_list, type(temp_list).__name__, self.list_type)) from e
                
                
            else:
                # Not a list type, just convert.
                try:
                    value = self.to_type(owning_obj, value)
                    
                except (TypeError, ValueError) as e:
                    raise Configurable_option_exception(owning_obj, self, "value '{}' of type '{}' is of invalid type".format(value, type(value).__name__)) from e
                
            # Save the new value.
            self.set_into_dict(owning_obj, dict_obj, value)
        
        # If a list of possible choices has been set, check those now.
        if len(self.choices) != 0:
            # If we are a list type, we'll check each item in value (rather than value itself).
            if self.list_type is not None:
                # Check each of our values, storing each in a new list in case they get changed.
                values = value
                new_values = []
                
                try:
                    for sub_value in values:
                        new_values.append(self.validate_choices(sub_value, owning_obj, dict_obj))

                except TypeError as e:
                    raise Configurable_option_exception(owning_obj, self, "value '{}' is not iterable".format(value))
                    
                value = new_values
                    
            else:
                # Not a list type, only a single value.
                value = self.validate_choices(value, owning_obj, dict_obj)
                
            # Now we need to set our value again incase it changed from validation.
            self.set_into_dict(owning_obj, dict_obj, value)
                
        # Check the value is valid.
        if not self._validate(self, owning_obj, value):
            # Invalid.
            raise Configurable_option_exception(owning_obj, self, "value '{}' of type '{}' is invalid".format(value, type(value).__name__))
        
        # Finally, if the value is equivalent to the default, we'll actually delete the value and use the default instead.
        if not self.required and value == self.default(owning_obj):
            self.set_default(owning_obj, dict_obj)


    def validate_choices(self, value, owning_obj, dict_obj = None):
        """
        Check whether the value of this option is one of the allowed choices.
        
        This method is called automatically by validate()
        
        :param value: The value of this option.
        :param owning_obj: The owning object on which this Option object is set as a class attribute.
        :param dict_obj: The dict in which the value of this Option is stored. In most cases, the value of this option is evaluated simply as dict_obj[self.name]
        """
        for choice in self.choices:
            if value == choice:
                # Found a match, all ok.
                return value
            
            elif isinstance(value, str) and isinstance(choice, str) and value.lower() == choice.lower():
                # Found a match, but with different cAsInG, convert to the correct case.
                return choice
            
        # If we get here, there was no match.
        raise Disallowed_choice_exception(owning_obj, self, value)
    