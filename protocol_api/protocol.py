from typing import List, Set, Union, Tuple, Type, Iterable, Callable, Any
from .net import Network, NetworkClient, IO

class Node:
    def __init__(self, instance: str, id: int, sk, n: int, net: NetworkClient, io: IO):
        """
            :param instance: a unique identifier for the protocol instance.
            :param id: node's id (an integer between 0 and n-1)
            :param sk: node's secret key
            :param n: number of participating nodes
            :param net: communication network
            """
        self.instance = instance
        self.id = id
        self.sk = sk
        self.n = n
        self.net = net
        self.io = io
        self.has_terminated = False
        self.net.newinstance(instance)

    def start_subprotocol(self, nodetype: Type['Node'], subinstance: str, subio: IO, *args, **kwargs) -> 'Node':
        subnode = nodetype(self.instance + "-" + subinstance, self.id, self.sk, self.n, self.net, subio, *args, **kwargs)
        return subnode

    ## Network functions
    def send(self, target: Union[int,Iterable[int],object], msg):
        self.net.send(self.instance, target, msg)

    def get_messages(self, round: int, src: int) -> List:
        return self.net.get_messages(self.instance, round, src)

    def get_allmessages(self, round: int) -> dict:
        return self.net.get_allmessages(self.instance, round)

    def get_allmessages_contents(self, round: int) -> set:
        return self.net.get_allmessages_contents(self.instance, round)

    ## IO functions
    def output(self, msg):
        self.io.output(msg)

    def get_input(self, round: int):
        return self.io.get_input(round)

    ## Abstract (to be overridden in subclass)
    def protocol(self, round: int) -> bool:
        """
        Execute a single protocol round.
        The node may use `self.io` to get any input and send output,
        and use `self.net` to communicate with other nodes
        (the network is synchronous, so messages will only be available to other nodes in the next round).

        :param round: the current round number (starts from 0)

        :return: the true iff the protocol has terminated.
        """
        pass



def simulate_protocol(rounds: int, nodes: Iterable[Node], net: Network, get_inputs: Callable[[int,int],Any],
                      round_assertion: Callable[[int,Iterable[Node],Set[int]],None] = None,
                      node_assertion: Callable[[int,Node,Set[int]],None] = None) -> Set[int]:
    terminated = set()
    for r in range(rounds):
        net.setround(r)
        for node in nodes:
            if node.id not in terminated:
                inputs = get_inputs(node.id, r)
                node.io.set_input(r, inputs)
                if node.protocol(r):
                    terminated.add(node.id)
                    node.has_terminated = True
                if node_assertion:
                    node_assertion(r, node, terminated)
        if round_assertion:
            round_assertion(r, nodes, terminated)

    return terminated