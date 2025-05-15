import unittest
from typing import List, Set, Dict
from protocol_api.protocol import Node, simulate_protocol
from protocol_api.blockchain import TotallyNaiveBlockchain, InconsistentBroadcastBlockchain, InvalidBroadcastBlockchain, InvalidByzantineBroadcast
from protocol_api.net import NetworkClient, IO, default_net

try:
    # Student code should define:
    #  get_inputs(round, id): returns the input for honest player `id` at round `round`
    #  corrupted_id: the corrupted id
    #  class BadNode, BadNode2 and BadNode3: the classes method for the student's bad node.
    from student_code import get_inputs, corrupted_id, BadNode, BadNode2, BadNode3
except ImportError:
    pass


def create_nodes(n: int, HonestCodeClass, CorruptedNodeClass):
    nodes: List[Node] = [HonestCodeClass('test1', i, None, n, NetworkClient(i, n), IO()) for i in range(n)]
    # Replace corrupted node

    nodes[corrupted_id] = CorruptedNodeClass('test1', corrupted_id, None, n,
                                                            NetworkClient(corrupted_id, n), IO())

    return nodes


def check_output_consistency(r: int, honest_nodes: List[Node]):
    output = ''
    outputnode = -1
    for node in honest_nodes:
        nodeout = "|".join(node.io.out)
        if nodeout.startswith(output):
            output = nodeout
            outputnode = node.id
        elif not output.startswith(nodeout):
            return (False,
                    "At round {}, node {}'s output {} is inconsistent with node {}'s output {}".format(r, outputnode,
                                                                                                       output, node.id,
                                                                                                       nodeout))
    return (True, "Consistent at round {}".format(r))


def check_output_liveness(T: int, r: int, honest_nodes: List[Node]):
    """
    Check T-liveness at round r.
    :param T: liveness parameter
    :param r: current round
    :param honest_nodes:
    :return:
    """

    if r < T:
        # Can't violate liveness if we haven't had T rounds yet.
        return (True, "Trivially {}-live at round {}".format(T,r))

    honest_inputs = set()
    # input_rounds = [] # For each round store the set of inputs that were received at that round.

    for i in range(r - T + 1):
        for node in honest_nodes:
            node_input = node.io.get_input(i)
            if node_input:
                honest_inputs.update(node_input)

    # Compute output intersection.
    outputs = honest_inputs.copy()
    for node in honest_nodes:
        outputs.intersection_update(node.io.out)

    notlive = honest_inputs.difference(outputs)
    if len(notlive) > 0:
        return (False,
                ("Not {}-live: Inputs were received by some honest party before round {} "+
                "but not output by all honest parties by round {}: {}").format(T, r - T + 1, r, notlive))
    else:
        return (True, "{}-Live at round {}".format(T, r))


# class TestTotallyNaiveBlockchain(unittest.TestCase):
#     def assertOutputConsistent(self, r: int, honest_nodes: List[Node]):
#         res, msg = check_output_consistency(r, honest_nodes)
#         self.assertTrue(res, msg)

#     def test_inconsistency_attack(self):
#         n = 5
#         rounds = 3
#         nodes = create_nodes(n, TotallyNaiveBlockchain, BadNode)
#         with self.assertRaises(AssertionError, msg = "Protocol output is perfectly consistent for {} parties and {} rounds".format(n, rounds)) as cm:
#             simulate_protocol(rounds, nodes, default_net, get_inputs,
#                               lambda r,nodes,_: self.assertOutputConsistent(r, [node for node in nodes if node.id != corrupted_id]))



# class TestBadBlockchainConsistency(unittest.TestCase):
#     def assertOutputConsistent(self, r: int, honest_nodes: List[Node]):
#         res, msg = check_output_consistency(r, honest_nodes)
#         self.assertTrue(res, msg)

#     def test_inconsistency_attack(self):
#         n = 5
#         rounds = 6
#         nodes = create_nodes(n, InconsistentBroadcastBlockchain, BadNode2)
#         with self.assertRaises(AssertionError, msg = "TestBadBlockchainConsistency: Protocol output is perfectly consistent for {} parties and {} rounds".format(n, rounds)) as cm:
#             simulate_protocol(rounds, nodes, default_net, get_inputs,
#                               lambda r,nodes,_: self.assertOutputConsistent(r, [node for node in nodes if node.id != corrupted_id]))


class TestBadBlockchainLiveness(unittest.TestCase):
    def assertOutputLive(self, T:int, r: int, nodes: List[Node]):
        res, msg = check_output_liveness(T, r, nodes)
        self.assertTrue(res, msg)

    def test_liveness_attack(self):
        n = 3
        T = (n+1) * InvalidByzantineBroadcast.get_maxrounds()
        rounds = T * 2

        nodes = create_nodes(n, InvalidBroadcastBlockchain, BadNode3)

        with self.assertRaises(AssertionError,
                               msg="TestBadBlockchainLiveness: Protocol output is perfectly {}-live for {} parties and {} rounds".format(
                                       T, n, rounds)) as cm:
            simulate_protocol(rounds, nodes, default_net, get_inputs,
                              lambda r, nodes, _: self.assertOutputLive(T, r, [node for node in nodes if node.id != corrupted_id]))


if __name__ == '__main__':
    unittest.main()
