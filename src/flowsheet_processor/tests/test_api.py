"""
Tests for api module.
"""
# standard library
from io import StringIO
import os
from pathlib import Path

# third-party
import pytest

# from pyomo.environ import units as pyunits
from pyomo.environ import Var, Set, Reals
from watertap.ui.api import *

# Mocking and fixtures


class MockSubBlock1:
    name = "subblock1"
    doc = "sub-block 1"


class MockSubBlock2:
    name = "subblock2"
    doc = "sub-block 2"


class MockSubBlock3:
    name = "subblock3"
    doc = "sub-block 3"
    # sub-blocks
    subblock1 = MockSubBlock1()
    set_block_interface(subblock1, {})

    def component_map(self, **kwargs):
        return {"subblock1": getattr(self, "subblock1")}


class MockBlock:
    # name = "watertap.ui.tests.test_api.MockBlock"
    name = "Flowsheet"
    doc = "flowsheet description"
    foo_var = Var(name="foo_var", initialize=0.0, within=Reals)
    foo_var.construct()
    bar_idx = Set(initialize=[0, 1, 2])
    bar_idx.construct()
    bar_var = Var(bar_idx, name="bar_var", initialize=[0.0, 0.0, 0.0], within=Reals)
    bar_var.construct()
    # sub-blocks
    subblock1 = MockSubBlock1()
    set_block_interface(subblock1, {})
    subblock2 = MockSubBlock2()
    set_block_interface(subblock2, {})
    subblock3 = MockSubBlock3()  # note: no interface

    def component_map(self, **kwargs):
        return {
            "subblock1": getattr(self, "subblock1"),
            "subblock2": getattr(self, "subblock2"),
            "subblock3": getattr(self, "subblock3"),
        }


@pytest.fixture
def mock_block():
    return MockBlock()


def build_options(display_name=False, description=False, variables=0,
                  readonly_variables=[]):
    opts = {}
    if display_name:
        opts["display_name"] = "foo"
    if description:
        opts["description"] = "This is a foo"
    if variables >= 0:
        v = {}
        for i in range(min(variables, 2)):
            name = "foo" if i == 0 else "bar"
            entry = {"display_name": f"{name} variable"}
            if i in readonly_variables:
                entry["readonly"] = True
            v[f"{name}_var"] = entry
        opts["variables"] = v
    return opts


# Tests
# -----


@pytest.mark.unit
def test_export_variables_simple(mock_block):
    export_variables(mock_block, name="Feed Z0", desc="Zero-Order feed block",
                     variables=["foo_var", "bar_var"])


@pytest.mark.unit
def test_export_variables_complex(mock_block):
    kw = dict(name="Feed Z0", desc="Zero-Order feed block")
    # bad 'variables'
    for bad_vars in [[{"name": "foo_var"}, "bar_var"], 12, "foo"]:
        with pytest.raises(ValueError):
            export_variables(mock_block,  variables=bad_vars, **kw)
    # ok
    for ok_vars in [["foo_var", "bar_var"], {"foo_var": {"readonly": True,
                                                         "display_name": "The Foo"}}]:
        export_variables(mock_block, variables=ok_vars, **kw)


@pytest.mark.unit
def test_set_block_interface(mock_block):
    # no keys
    set_block_interface(mock_block, {})
    # invalid key
    data = {"test": "data"}
    set_block_interface(mock_block, data)
    assert get_block_interface(mock_block)._block_info.meta == data
    # ok key
    data = {"display_name": "foo"}
    set_block_interface(mock_block, data)
    # existing object
    obj = BlockInterface(mock_block, data)
    set_block_interface(mock_block, obj)


@pytest.mark.unit
def test_get_block_interface(mock_block):
    # data
    data = {"display_name": "foo"}
    set_block_interface(mock_block, data)
    assert get_block_interface(mock_block) is not None
    # existing object
    obj = BlockInterface(mock_block, data)
    set_block_interface(mock_block, obj)
    obj2 = get_block_interface(mock_block)
    assert obj2 is obj


@pytest.mark.unit
def test_block_interface_constructor(mock_block):
    for i in range(4):  # combinations of display_name and description
        disp, desc = (i % 2) == 0, ((i // 2) % 2) == 0
        obj = BlockInterface(
            mock_block, build_options(display_name=disp, description=desc)
        )
        obj.get_exported_variables()  # force looking at contents


@pytest.mark.unit
def test_block_interface_get_exported_variables(mock_block):
    # no variables section
    obj = BlockInterface(mock_block, build_options(variables=-1))
    exvar = obj.get_exported_variables()
    print(f"Got exported variables: {exvar}")
    assert len(exvar) == 0
    # empty variables section
    obj = BlockInterface(mock_block, build_options(variables=0))
    assert len(obj.get_exported_variables()) == 0
    # 1 variable
    obj = BlockInterface(mock_block, build_options(variables=1))
    assert len(obj.get_exported_variables()) == 1
    # 2 variables
    obj = BlockInterface(mock_block, build_options(variables=2))
    assert len(obj.get_exported_variables()) == 2


@pytest.mark.unit
def test_workflow_actions():
    wfa = WorkflowActions
    assert wfa.build is not None
    assert wfa.solve is not None


@pytest.mark.unit
def test_flowsheet_interface_constructor(mock_block):
    fsi = FlowsheetInterface(build_options(variables=2))
    fsi.set_block(mock_block)


@pytest.mark.unit
def test_flowsheet_interface_as_dict(mock_block):
    obj = FlowsheetInterface(build_options(variables=2))
    obj.set_block(mock_block)
    d = obj.as_dict()

    # only blocks/meta at top-level
    assert "blocks" in d
    assert "meta" in d
    assert "variables" not in d

    # whole tamale in root block
    assert len(d["blocks"]) == 1
    root = list(d["blocks"].keys())[0]
    for v in "variables", "display_name", "description", "category":
        assert v in d["blocks"][root]


@pytest.mark.unit
def test_flowsheet_interface_save(mock_block, tmpdir):
    obj = FlowsheetInterface(build_options(variables=2))
    obj.set_block(mock_block)
    # string
    filename = "test-str.json"
    str_path = os.path.join(tmpdir, filename)
    obj.save(str_path)
    assert os.path.exists(os.path.join(tmpdir, filename))
    # path
    filename = "test-path.json"
    path_path = Path(tmpdir) / filename
    obj.save(path_path)
    assert os.path.exists(os.path.join(tmpdir, filename))
    # stream
    strm = StringIO()
    obj.save(strm)
    assert strm.getvalue() != ""


@pytest.mark.unit
def test_flowsheet_interface_load(mock_block, tmpdir):
    obj = FlowsheetInterface(build_options(variables=2))
    obj.set_block(mock_block)
    filename = "saved.json"
    obj.save(Path(tmpdir) / filename)
    # print(f"@@ saved: {json.dumps(obj.as_dict(), indent=2)}")
    obj2 = FlowsheetInterface.load_from(Path(tmpdir) / filename, mock_block)
    assert obj2 == obj


@pytest.mark.unit
def test_flowsheet_interface_load_missing(mock_block, tmpdir):
    obj = FlowsheetInterface(build_options(variables=2))
    obj.set_block(mock_block)
    filename = "saved.json"
    # manual save, and remove some variables
    d = obj.as_dict()
    block = d["blocks"]["Flowsheet"]
    block["variables"] = {}
    fpath = Path(tmpdir) / filename
    fp = open(fpath, "w", encoding="utf-8")
    json.dump(d, fp)
    fp.close()
    # reload
    obj2 = FlowsheetInterface.load_from(Path(tmpdir) / filename, mock_block)
    assert obj2.get_var_extra() != {}
    assert obj2.get_var_missing() == {}


class ScalarValueBlock:
    name = "Flowsheet"
    doc = "flowsheet description"
    foo_var = Var(name="foo_var", initialize=0.0, within=Reals)
    foo_var.construct()
    bar_var = Var(name="bar_var", initialize=0.0, within=Reals)
    bar_var.construct()


@pytest.mark.unit
def test_flowsheet_interface_load_readonly(tmpdir):
    block = ScalarValueBlock()
    export_variables(block, variables={"foo_var": {}, "bar_var":{"readonly": True}})
    obj = FlowsheetInterface({"display_name": "Flowsheet"})
    obj.set_block(block)
    readonly_index = 1
    filename = "saved.json"
    # manual save, and change the variables
    dblock = obj.as_dict()
    root = list(dblock["blocks"].keys())[0]
    root_block = dblock["blocks"][root]
    # Save old values, modify all the variables (add 1)
    old_values = []
    for var_entry in root_block["variables"]:
        value = var_entry["value"]
        old_values.append(value)
        var_entry["value"] = value + 1
    # Write out
    fp = open(Path(tmpdir) / filename, "w", encoding="utf-8")
    json.dump(dblock, fp)
    fp.close()
    # Reload
    obj.load(Path(tmpdir) / filename)
    # See that variables have changed, except readonly one
    block = obj.as_dict()
    root = list(block["blocks"].keys())[0]
    root_block = block["blocks"][root]
    for i, var_entry in root_block["variables"]:
        if i == readonly_index:
            assert var_entry["value"] == old_values[i]
        else:
            assert var_entry["value"] == old_values[i] + 1


def test_flowsheet_interface_get_var(mock_block):
    fsi = FlowsheetInterface(build_options(variables=1))
    fsi.set_block(mock_block)
    with pytest.raises(KeyError):
        fsi.get_var_missing()
    with pytest.raises(KeyError):
        fsi.get_var_extra()


def test_add_action_type(mock_block):
    fsi = FlowsheetInterface(build_options(variables=1))
    fsi.set_block(mock_block)

    # Add 2 actions:
    #   cook <- eat
    fsi.add_action_type("cook")
    fsi.add_action_type("eat", deps=["cook"])
    fsi.set_action("cook", add_action_cook, dish=_dish)
    fsi.set_action("eat", add_action_eat)

    # Check actions
    assert fsi.get_action("cook") == (add_action_cook, {"dish": _dish})
    assert fsi.get_action("eat") == (add_action_eat, {})

    # Run actions
    fsi.run_action("eat")

    # Add some problematic actions
    with pytest.raises(KeyError):
        # unknown dependency
        fsi.add_action_type("go-inside", deps=["open-door"])

    with pytest.raises(ValueError):
        # cannot depend on self
        fsi.add_action_type("a1", deps=["a1"])


_dish = "mac&cheese"
_cooked = None


def add_action_cook(dish=None, **kwargs):
    global _cooked
    _cooked = dish
    print("cook")


def add_action_eat(**kwargs):
    assert _cooked == _dish
    print("eat")
