import inspect

import pandas as pd
import pytest

from hamilton import graph
from hamilton import node
import tests.resources.bad_functions
import tests.resources.dummy_functions
import tests.resources.parametrized_nodes
import tests.resources.parametrized_inputs
import tests.resources.extract_column_nodes
import tests.resources.config_modifier
import tests.resources.typing_vs_not_typing
from hamilton.node import NodeSource


def test_find_functions():
    """Tests that we filter out _ functions when passed a module and don't pull in anything from the imports."""
    expected = [('A', tests.resources.dummy_functions.A),
                ('B', tests.resources.dummy_functions.B),
                ('C', tests.resources.dummy_functions.C)]
    actual = graph.find_functions(tests.resources.dummy_functions)
    assert len(actual) == len(expected)
    assert actual == expected


def test_add_dependency_missing_param_type():
    """Tests case that we error if types are missing from a parameter."""
    with pytest.raises(ValueError):
        a_sig = inspect.signature(tests.resources.bad_functions.A)
        node.Node('A', a_sig.return_annotation, 'A doc', tests.resources.bad_functions.A)  # should error out


def test_add_dependency_missing_function_type():
    """Tests case that we error if types are missing from a function."""
    with pytest.raises(ValueError):
        b_sig = inspect.signature(tests.resources.bad_functions.B)
        node.Node('B', b_sig.return_annotation, 'B doc', tests.resources.bad_functions.B)  # should error out


def test_add_dependency_strict_node_dependencies():
    """Tests that we add node dependencies between functions correctly.

    Setup here is: B depends on A. So A is depended on by B. B is not depended on by anyone.
    """
    b_sig = inspect.signature(tests.resources.dummy_functions.B)
    func_node = node.Node('B', b_sig.return_annotation, 'B doc', tests.resources.dummy_functions.B)
    func_name = 'B'
    nodes = {'A': node.Node('A', inspect.signature(tests.resources.dummy_functions.A).return_annotation, 'A doc',
                            tests.resources.dummy_functions.A)}
    param_name = 'A'
    param_type = b_sig.parameters['A'].annotation

    graph.add_dependency(func_node, func_name, nodes, param_name, param_type)
    assert nodes['A'] == func_node.dependencies[0]
    assert func_node.depended_on_by == []


def test_typing_to_primitive_conversion():
    """Tests that we can mix function output being typing type, and dependent function using primitive type."""
    b_sig = inspect.signature(tests.resources.typing_vs_not_typing.B)
    func_node = node.Node('B', b_sig.return_annotation, 'B doc', tests.resources.typing_vs_not_typing.B)
    func_name = 'B'
    nodes = {'A': node.Node('A', inspect.signature(tests.resources.typing_vs_not_typing.A).return_annotation, 'A doc',
                            tests.resources.typing_vs_not_typing.A)}
    param_name = 'A'
    param_type = b_sig.parameters['A'].annotation

    graph.add_dependency(func_node, func_name, nodes, param_name, param_type)
    assert nodes['A'] == func_node.dependencies[0]
    assert func_node.depended_on_by == []


def test_primitive_to_typing_conversion():
    """Tests that we can mix function output being a primitive type, and dependent function using typing type."""
    b_sig = inspect.signature(tests.resources.typing_vs_not_typing.B2)
    func_node = node.Node('B2', b_sig.return_annotation, 'B2 doc', tests.resources.typing_vs_not_typing.B2)
    func_name = 'B2'
    nodes = {'A2': node.Node('A2', inspect.signature(tests.resources.typing_vs_not_typing.A2).return_annotation,
                             'A2 doc', tests.resources.typing_vs_not_typing.A2)}
    param_name = 'A2'
    param_type = b_sig.parameters['A2'].annotation

    graph.add_dependency(func_node, func_name, nodes, param_name, param_type)
    assert nodes['A2'] == func_node.dependencies[0]
    assert func_node.depended_on_by == []


def test_throwing_error_on_incompatible_types():
    """Tests we error on incompatible types."""
    d_sig = inspect.signature(tests.resources.bad_functions.D)
    func_node = node.Node('D', d_sig.return_annotation, 'D doc', tests.resources.bad_functions.D)
    func_name = 'D'
    nodes = {'C': node.Node('C', inspect.signature(tests.resources.bad_functions.C).return_annotation,
                            'C doc', tests.resources.bad_functions.C)}
    param_name = 'C'
    param_type = d_sig.parameters['C'].annotation
    with pytest.raises(ValueError):
        graph.add_dependency(func_node, func_name, nodes, param_name, param_type)


def test_add_dependency_user_nodes():
    """Tests that we add node user defined dependencies correctly.

    Setup here is: A depends on b and c. But we're only doing one call. So expecting A having 'b' as a dependency,
    and 'b' is depended on by A.
    """
    a_sig = inspect.signature(tests.resources.dummy_functions.A)
    func_node = node.Node('A', a_sig.return_annotation, 'A doc', tests.resources.dummy_functions.A)
    func_name = 'A'
    nodes = {}
    param_name = 'b'
    param_type = a_sig.parameters['b'].annotation

    graph.add_dependency(func_node, func_name, nodes, param_name, param_type)
    # user node is created and added to nodes.
    assert nodes['b'] == func_node.dependencies[0]
    assert nodes['b'].depended_on_by[0] == func_node
    assert func_node.depended_on_by == []


def test_create_function_graph_simple():
    """Tests that we create a simple function graph."""
    expected = create_testing_nodes()
    actual = graph.create_function_graph(tests.resources.dummy_functions, config={})
    assert actual == expected


def create_testing_nodes():
    """Helper function for creating the nodes represented in dummy_functions.py."""
    nodes = {'A': node.Node('A',
                            inspect.signature(tests.resources.dummy_functions.A).return_annotation,
                            'Function that should become part of the graph - A',
                            tests.resources.dummy_functions.A),
             'B': node.Node('B',
                            inspect.signature(tests.resources.dummy_functions.B).return_annotation,
                            'Function that should become part of the graph - B',
                            tests.resources.dummy_functions.B),
             'C': node.Node('C',
                            inspect.signature(tests.resources.dummy_functions.C).return_annotation,
                            '',
                            tests.resources.dummy_functions.C),
             'b': node.Node('b',
                            inspect.signature(tests.resources.dummy_functions.A).parameters['b'].annotation,
                            node_source=NodeSource.EXTERNAL),
             'c': node.Node('c',
                            inspect.signature(tests.resources.dummy_functions.A).parameters['c'].annotation,
                            node_source=NodeSource.EXTERNAL)}
    nodes['A'].dependencies.append(nodes['b'])
    nodes['A'].dependencies.append(nodes['c'])
    nodes['A'].depended_on_by.append(nodes['B'])
    nodes['A'].depended_on_by.append(nodes['C'])
    nodes['b'].depended_on_by.append(nodes['A'])
    nodes['c'].depended_on_by.append(nodes['A'])
    nodes['B'].dependencies.append(nodes['A'])
    nodes['C'].dependencies.append(nodes['A'])
    return nodes


def test_execute():
    """Tests graph execution along with basic memoization since A is depended on by two functions."""
    nodes = create_testing_nodes()
    inputs = {
        'b': 2,
        'c': 5
    }
    expected = {'A': 7, 'B': 49, 'C': 14, 'b': 2, 'c': 5}
    actual = graph.FunctionGraph.execute_static(nodes.values(), inputs)
    assert actual == expected
    actual = graph.FunctionGraph.execute_static(nodes.values(), inputs, overrides={'A': 8})
    assert actual['A'] == 8


def test_get_required_functions():
    """Exercises getting the subset of the graph for computation on the toy example we have constructed."""
    nodes = create_testing_nodes()
    final_vars = ['A', 'B']
    expected_user_nodes = {nodes['b'], nodes['c']}
    expected_nodes = {nodes['A'], nodes['B'], nodes['b'], nodes['c']}  # we skip 'C'
    fg = graph.FunctionGraph(tests.resources.dummy_functions, config={})
    actual_nodes, actual_ud_nodes = fg.get_required_functions(final_vars)
    assert actual_nodes == expected_nodes
    assert actual_ud_nodes == expected_user_nodes


def test_get_impacted_nodes():
    """Exercises getting the downstream subset of the graph for computation on the toy example we have constructed."""
    nodes = create_testing_nodes()
    var_changes = ['A']
    expected_nodes = {nodes['B'], nodes['C'], nodes['A']}
    # expected_nodes = {nodes['A'], nodes['B'], nodes['b'], nodes['c']}  # we skip 'C'
    fg = graph.FunctionGraph(tests.resources.dummy_functions, config={})
    actual_nodes = fg.get_impacted_nodes(var_changes)
    assert actual_nodes == expected_nodes


def test_function_graph_from_multiple_sources():
    fg = graph.FunctionGraph(tests.resources.dummy_functions, tests.resources.parametrized_nodes, config={})
    assert len(fg.get_nodes()) == 8  # we take the union of all of them, and want to test that


def test_end_to_end_with_parametrized_nodes():
    """Tests that a simple function graph with parametrized nodes works end-to-end"""
    fg = graph.FunctionGraph(tests.resources.parametrized_nodes, config={})
    results = fg.execute(fg.get_nodes(), {})
    assert results == {'parametrized_1': 1, 'parametrized_2': 2, 'parametrized_3': 3}


def test_end_to_end_with_parametrized_inputs():
    fg = graph.FunctionGraph(tests.resources.parametrized_inputs, config={'static_value': 3})
    results = fg.execute(fg.get_nodes())
    assert results == {
        'input_1': 1,
        'input_2': 2,
        'output_1': 1 + 3,
        'output_2': 2 + 3,
        'static_value': 3
    }


def test_get_required_functions_askfor_config():
    """Tests that a simple function graph with parametrized nodes works end-to-end"""
    fg = graph.FunctionGraph(tests.resources.parametrized_nodes, config={'a': 1})
    nodes, user_nodes = fg.get_required_functions(['a', 'parametrized_1'])
    n, = user_nodes
    assert n.name == 'a'
    results = fg.execute(user_nodes)
    assert results == {'a': 1}


def test_end_to_end_with_column_extractor_nodes():
    """Tests that a simple function graph with nodes that extract columns works end-to-end"""
    fg = graph.FunctionGraph(tests.resources.extract_column_nodes, config={})
    nodes = fg.get_nodes()
    results = fg.execute(nodes, {}, {})
    df_expected = tests.resources.extract_column_nodes.generate_df()
    pd.testing.assert_series_equal(results['col_1'], df_expected['col_1'])
    pd.testing.assert_series_equal(results['col_2'], df_expected['col_2'])
    pd.testing.assert_frame_equal(results['generate_df'], df_expected)
    assert nodes[0].documentation == 'Function that should be parametrized to form multiple functions'


def test_end_to_end_with_config_modifier():
    config = {
        'fn_1_version': 1,
    }
    fg = graph.FunctionGraph(tests.resources.config_modifier, config=config)
    results = fg.execute(fg.get_nodes(), {}, {})
    assert results['fn'] == 'version_1'

    config = {
        'fn_1_version': 2,
    }
    fg = graph.FunctionGraph(tests.resources.config_modifier, config=config)
    results = fg.execute(fg.get_nodes(), {}, {})
    assert results['fn'] == 'version_2'
    config = {
        'fn_1_version': 3,
    }
    fg = graph.FunctionGraph(tests.resources.config_modifier, config=config)
    results = fg.execute(fg.get_nodes(), {}, {})
    assert results['fn'] == 'version_3'


def test_non_required_nodes():
    fg = graph.FunctionGraph(tests.resources.test_default_args, config={'required': 10})
    results = fg.execute([n for n in fg.get_nodes() if n.node_source == NodeSource.STANDARD], {}, {})
    assert results['A'] == 10
    fg = graph.FunctionGraph(tests.resources.test_default_args, config={'required': 10, 'defaults_to_zero': 1})
    results = fg.execute([n for n in fg.get_nodes() if n.node_source == NodeSource.STANDARD], {}, {})
    assert results['A'] == 11


def test_config_can_override():
    config = {
        'new_param': 'new_value'
    }
    fg = graph.FunctionGraph(tests.resources.config_modifier, config=config)
    out = fg.execute([n for n in fg.get_nodes()])
    assert out['new_param'] == 'new_value'
