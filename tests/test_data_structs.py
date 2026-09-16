# -*- coding: utf-8 -*-

'''Tests for lpu.data_structs

lpu.data_structs のテスト。
'''

import pytest

from conftest import requires_trie

from lpu.data_structs import trees


class TestTreeNode:
    def test_append_accepts_nodes_and_strings(self):
        root = trees.TreeNode('S')
        root.append(trees.TreeNode('NP')).append('VP')
        assert [child.label for child in root.children] == ['NP', 'VP']

    def test_to_str_parenthesizes_every_node(self):
        root = trees.TreeNode('S')
        root.append('NP')
        assert root.toStr() == '(S (NP))'

    def test_check_valid_accepts_a_labeled_subtree(self):
        '''A deep check must recurse instead of always failing

        Up to 0.2.x the recursive condition was commented out while its
        "return False" was left behind, so any node with children was
        reported as invalid.

        deep 判定が常に失敗せず再帰すること。
        0.2.x までは再帰の条件式がコメントアウトされたまま
        "return False" が残っており、子を持つノードは全て不正とされた。
        '''
        root = trees.TreeNode('S')
        root.append('NP').append('VP')
        assert root.checkValid(deep=True)
        assert root.checkValid(deep=False)

    def test_check_valid_rejects_an_empty_label_with_children(self):
        root = trees.TreeNode('')
        root.append('NP')
        assert not root.checkValid(deep=False)

    def test_check_valid_detects_an_invalid_descendant(self):
        root = trees.TreeNode('S')
        broken = trees.TreeNode('')
        broken.append('X')
        root.append(broken)
        assert root.checkValid(deep=False)
        assert not root.checkValid(deep=True)

    def test_from_s_builds_the_tree(self):
        '''fromS parses an S-expression instead of returning an empty node

        Up to 0.2.x fromS ignored its argument.

        Note that toStr() parenthesizes leaves as well, so the output is
        not byte-identical to the input expression.

        fromS が引数を無視せず S 式を解析すること。
        0.2.x までは引数が無視されていた。
        なお toStr() は葉も括弧で囲むため、出力は入力式と文字列としては
        一致しない。
        '''
        root = trees.TreeNode.fromS('(S (NP the cat) (VP sat))')
        assert root.label == 'S'
        assert [child.label for child in root.children] == ['NP', 'VP']
        assert [n.label for n in root.children[0].children] == ['the', 'cat']
        assert root.toStr() == '(S (NP (the) (cat)) (VP (sat)))'


class TestParseSExpression:
    def test_parses_nested_expressions(self):
        parsed, _ = trees.parseSExpression('(S (NP the cat) (VP sat))')
        assert parsed == ['S', ['NP', 'the', 'cat'], ['VP', 'sat']]

    def test_parses_a_flat_expression(self):
        parsed, _ = trees.parseSExpression('(S a b)')
        assert parsed == ['S', 'a', 'b']


class TestTreeUtilities:
    def test_count_elements(self):
        tree, _ = trees.parseSExpression('(S (NP the cat) (VP sat))')
        # 3 inner nodes (S, NP, VP) and 3 leaves (the, cat, sat)
        # 内部ノード 3 個 (S, NP, VP) と葉 3 個 (the, cat, sat)
        assert trees.countElements(tree) == 6

    def test_index_tree_returns_post_order_labels(self):
        tree, _ = trees.parseSExpression('(S (NP a) (VP b))')
        labels, left_ranges = trees.indexTree(tree)
        assert labels == ['a', 'NP', 'b', 'VP', 'S']
        assert len(left_ranges) == len(labels)


class TestEditDistance:
    @pytest.mark.parametrize('seq1,seq2,expected', [
        ('kitten', 'sitting', 3),
        ('', '', 0),
        ('abc', '', 3),
        ('', 'abc', 3),
        ('abc', 'abc', 0),
        ('abc', 'abd', 1),
    ])
    def test_calc_edit_distance(self, seq1, seq2, expected):
        assert trees.calcEditDistance(seq1, seq2) == expected

    def test_is_symmetric(self):
        assert (trees.calcEditDistance('kitten', 'sitting')
                == trees.calcEditDistance('sitting', 'kitten'))

    def test_tree_edit_distance_of_identical_trees_is_zero(self):
        expr = '(S (NP a) (VP b))'
        assert trees.calcTreeEditDistance(expr, expr) == 0

    def test_tree_edit_distance_counts_a_single_label_change(self):
        assert trees.calcTreeEditDistance(
            '(S (NP a) (VP b))', '(S (NP a) (VP c))') == 1


@requires_trie
class TestIDMap:
    '''Double-Array Trie based ID maps / Double-Array Trie ベースの ID マップ'''

    def test_append_assigns_stable_ids(self):
        from lpu.data_structs.trie import IDMap
        idmap = IDMap()
        first = idmap.append('apple')
        assert idmap.append('apple') == first
        assert idmap.append('banana') != first

    def test_str2id_returns_minus_one_for_unknown_keys(self):
        from lpu.data_structs.trie import IDMap
        idmap = IDMap()
        idmap.append('apple')
        assert idmap.str2id('apple') > 0
        assert idmap.str2id('unknown') == -1

    def test_items_yields_key_id_pairs(self):
        from lpu.data_structs.trie import IDMap
        idmap = IDMap()
        for word in ['apple', 'banana']:
            idmap.append(word)
        assert sorted(idmap.items()) == [('apple', 1), ('banana', 2)]

    def test_remove_frees_the_key(self):
        from lpu.data_structs.trie import IDMap
        idmap = IDMap()
        idmap.append('apple')
        idmap.remove('apple')
        assert idmap.str2id('apple') == -1


@requires_trie
class TestTwoWayIDMap:
    def test_id2str_inverts_append(self):
        '''Two-way conversion must round-trip

        Up to 0.2.x this path was unreachable because append() called the
        removed pycedar API num_keys().

        双方向変換が往復すること。
        0.2.x では append() が廃止済みの pycedar API num_keys() を呼んで
        いたため、この経路に到達できなかった。
        '''
        from lpu.data_structs.trie import TwoWayIDMap
        idmap = TwoWayIDMap()
        ids = {word: idmap.append(word) for word in ['apple', 'apricot', 'kiwi']}
        for word, index in ids.items():
            assert idmap.id2str(index) == word

    def test_keys_and_ids_are_enumerable(self):
        '''ids/keys must not fail on the std::string elements

        Up to 0.2.x these methods typed the C++ std::string elements as
        Python objects, so calling .empty() on them raised AttributeError.

        std::string の要素で失敗しないこと。
        0.2.x までは C++ の std::string を Python オブジェクトとして
        受けていたため、.empty() の呼び出しが AttributeError になった。
        '''
        from lpu.data_structs.trie import TwoWayIDMap
        idmap = TwoWayIDMap()
        words = ['apple', 'apricot', 'kiwi']
        ids = [idmap.append(word) for word in words]
        assert sorted(idmap.keys()) == sorted(words)
        assert sorted(idmap.ids()) == sorted(ids)

    def test_items_yields_key_id_pairs_like_the_parent_class(self):
        '''items() is unified on (key, ID) as in IDMap

        Up to 0.2.x TwoWayIDMap.items() yielded (ID, key), the reverse of
        the parent class. BREAKING change in 0.3.0.

        items() は IDMap と同じく (キー, ID) に統一されている。
        0.2.x までは親クラスと逆の (ID, キー) を返していた (0.3.0 で変更)。
        '''
        from lpu.data_structs.trie import TwoWayIDMap
        idmap = TwoWayIDMap()
        for word in ['apple', 'banana']:
            idmap.append(word)
        assert sorted(idmap.items()) == [('apple', 1), ('banana', 2)]

    def test_remove_then_purge(self):
        from lpu.data_structs.trie import TwoWayIDMap
        idmap = TwoWayIDMap()
        for word in ['apple', 'banana']:
            idmap.append(word)
        idmap.remove('apple')
        idmap.purge()
        assert sorted(idmap.keys()) == ['banana']


@requires_trie
class TestDict:
    def test_stores_and_retrieves_objects(self):
        from lpu.data_structs.trie import Dict
        mapping = Dict()
        mapping['foo'] = {'a': 1}
        assert mapping.get('foo') == {'a': 1}
        assert mapping.get('missing', 'default') == 'default'
