"""Tests for configurable objects"""

import pytest

from configurables.base import Configurable
from configurables.options import Options
from configurables.option import Option
from configurables.exception import Configurable_option_exception


# Setup our two test classes.
class Parent(Configurable):
    
    scf = Option(help = "Options for self-consistent field", default = True, type = bool, no_edit = True)
    
    dft = Options(help = "Options for density-functional theory",
        grid = Options(
            help = "DFT grid options",
            size = Option(help = "Size of the DFT grid", type = int, default = 10)
        )
    )
    
class Intermediate(Parent):
    
    scf = Option(help = "Options for SCF")
    
    dft = Options(
        functional = Option(help = "DFT functional", default = "B3LYP", no_edit = True)
    )
    
    _post_hf = Option("post_hf", default = "off")
    
class Child(Intermediate):
    
    dft = Options(
        functional = Option(help = "Functional to use for DFT"),
        grid = Options(
            grid_name = Option(help = "Shorthand name of the DFT grid", default = "big")
        )
    )

    list_items = Option(help = "A list of many things", default = [], none_to_default = True, type = list)
    none_items = Option(help = "A list of fewer things", default = [], none_to_default = False, type = list)
    
    _post_hf = Option("post_hf", help = "Post HF options")

@pytest.fixture
def child1():
    return Child()

@pytest.fixture
def child2():
    return Child()

@pytest.fixture
def intermediate():
    return Intermediate()

@pytest.fixture
def parent():
    return Parent()


def test_basic(parent):
    """Test basic access."""
    
    # Can we retrieve default values?
    assert parent.scf is True
    assert parent.dft['grid']['size'] == 10
    
    # Can we change and retrieve values?
    parent.scf = False
    parent.dft['grid']['size'] = 20
    
    assert parent.scf is False
    assert parent.dft['grid']['size'] == 20
    
    
def test_meta_inheritance(child1, child2, intermediate,parent):
    """Test the inheritance mechanism of Options meta data."""
    
    # Test that help is inherited correctly.
    assert child1.get_options()['dft'].help == parent.get_options()['dft'].help
    
    # Test that base Option objects (not nested Options) can also inherit.
    assert child1.get_options()['scf'].no_edit == parent.get_options()['scf'].no_edit
    
    # Test that sub-options can inherit properly.
    assert intermediate.get_options()['dft'].get_options(type(intermediate))['functional'].no_edit is True
    assert child1.get_options()['dft'].get_options(type(child1))['functional'].no_edit is True


def test_value_inheritance(child1, child2, parent):
    """Test the inheritance mechanism of Options objects."""
    
    # Before any change, all objects should have equivalent values of grid size.
    assert child1.dft['grid']['size'] == child2.dft['grid']['size'] and child2.dft['grid']['size'] == parent.dft['grid']['size']
    
    # Child objects should have grid name...
    assert child1.dft['grid']['grid_name'] == child2.dft['grid']['grid_name']
    
    # ...but not parent.
    with pytest.raises(Configurable_option_exception):
        parent.dft['grid']['grid_name']
        
    # Make a change to one of the children.
    child1.dft['grid']['size'] = 100
    
    # Check the change, and that the others have not changed
    assert child1.dft['grid']['size'] == 100
    assert child2.dft['grid']['size'] == 10
    assert parent.dft['grid']['size'] == 10
    
    # Check we can also change the parent property.
    parent.dft['grid']['size'] = 1
    
    # Check the change, and that the others have not changed
    assert child1.dft['grid']['size'] == 100
    assert child2.dft['grid']['size'] == 10
    assert parent.dft['grid']['size'] == 1
    
    # Check we can change an actual child property.
    child2.dft['grid']['grid_name'] = "small"
    
    # Check the change, and that the others have not changed
    assert child1.dft['grid']['grid_name'] == "big"
    assert child2.dft['grid']['grid_name'] == "small"
    
    with pytest.raises(Configurable_option_exception):
        nothing = parent.dft['grid']['grid_name']
        
    # Check we can't set a property of parent that doesn't exist.
    with pytest.raises(Configurable_option_exception):
        parent.dft['grid']['grid_name'] = "medium"
        
    # Check we can set a whole bunch of sub options at once.
    child1.dft = {"functional": "B3LYP", "grid": {"grid_name": "tiny"}}
    assert child1.dft['functional'] == "B3LYP"
    assert child1.dft['grid']['grid_name'] == "tiny"
        

def test_dumping(child1):
    """Test dumping of the objects to text."""
    
    # Non-explicit dump; everything default.
    assert child1.dump(False) == {}
    
    # Explicit dump.
    assert child1.dump(True) == {
        'scf': True,
        'dft': {
            'functional': "B3LYP",
            'grid': {
                'size': 10,
                'grid_name': "big"
            }
        },
        'list_items': [],
        'none_items': [],
        'post_hf': "off"
    }

def test_cls_doc(child1):
    """Test the auto documentation feature."""
    child1.dump_cls_template()

def test_obj_doc(child1):
    """Test the auto documentation feature."""
    child1.dump_obj_template()

def test_none_to_list(child1):
    """Can we convert None values to a default"""
    child1.list_items = [1,2,3]
    child1.none_items = [4,5,6]

    child1.list_items = None
    child1.none_items = None
    # Before we validate, no magic happens.
    assert child1.list_items is None
    assert child1.none_items is None
    child1.validate()
    # Now it's been converted.
    assert child1.list_items == []
    assert child1.none_items is None