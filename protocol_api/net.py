from typing import Set, List, Iterable, Union, Callable, Any
from enum import Enum

class Network:
    # Internal API
    def __init__(self):
        self.msgs: List[dict] = [] # list of messages for each round.
        self.baserounds: dict = {} # Base round for every instance
        self.round = -1
        self.setround(0)

    def newinstance(self, instance: str):
        if instance not in self.baserounds:
            self.baserounds[instance] = self.round

    def setround(self, round: int):
        self.round = round
        if len(self.msgs) <= round:
            for r in range(round + 1 - len(self.msgs)):
                self.msgs.append({}) # In each round, the messages are indexed by instance.

    # External API
    def send(self, instance: str, src: int, targets: Iterable[int], msg) -> None:
        """
        Send a message on channel ``instance`` to the target nodes.
        :param instance: channel name
        :param src: id of node that is sending the message
        :param targets: ids of nodes that will receive the message
        :param msg: the message itself
        """
        if instance not in self.msgs[self.round]:
            self.msgs[self.round][instance] = {}

        for target in targets:
            if target not in self.msgs[self.round][instance]:
                self.msgs[self.round][instance][target] = {}
            if src not in self.msgs[self.round][instance][target]:
                self.msgs[self.round][instance][target][src] = []

            self.msgs[self.round][instance][target][src].append(msg)

    def get_allmessages(self, instance: str, instance_round: int, target: int) -> dict:
        """
        Returns all messages sent to the target node at a given round (relative to the instance base)
        :param instance:
        :param instance_round:
        :param target:
        :return:
        """
        round = instance_round + self.baserounds.get(instance, 0)
        if round >= len(self.msgs):
            raise RuntimeError("We haven't reached round {} yet for instance {}".format(instance_round, instance))

        if instance not in self.msgs[round] or target not in self.msgs[round][instance]:
            return {}
        else:
            return self.msgs[round][instance][target]

    def get_messages(self, instance: str, round: int, target: int, src: int) -> List:
        targetmsgs = self.get_allmessages(instance, round, target)
        if src not in targetmsgs:
            return []
        else:
            return targetmsgs[src]

default_net = Network()

class PartiallySynchronousNetwork(Network):
    def __init__(self, Delta: int):
        self.Delta = Delta

        # Pending messages. This dict maps each round to a subdict; the subdict has
        # maps each instance to the messages that were sent at the round
        # (as a dict mapping msgid to a tuple (src,target,msg), where msgid is a unique message id. ).
        self.pending_msgs = {}

        # This dict maps message id to a tuple (src,target,msg,round,idx)
        self.pending_msgs_byid = {}
        self.lastid = 0
        super().__init__()

    def deliver_pending_msg(self, id) -> bool:
        if id not in self.pending_msgs_byid:
            return False

        (src, target, msg, instance, r) = self.pending_msgs_byid[id]
        super().send(instance, src, [target], msg)
        del self.pending_msgs_byid[id]
        del self.pending_msgs[r][instance][id]
        return True


    def force_delta_deliveries(self):
        """
        Force messages that were sent ``Delta`` rounds ago to be delivered.
        :return:
        """
        r = self.round - self.Delta + 1
        if r < 0:
            return
        for instance in self.pending_msgs[r]:
            msgs = list(self.pending_msgs[r][instance].keys())
            for id in msgs:
                self.deliver_pending_msg(id)

    def setround(self, round: int):
        for r in range(self.round + 1, round+1):
            self.force_delta_deliveries()
            super().setround(r)

        self.pending_msgs[round] = {}

    def send(self, instance: str, src: int, targets: Iterable[int], msg) -> None:
        # Send only adds the messages to the pending_msgs
        # Messages must be *delivered* in order to be read.
        if instance not in self.pending_msgs[self.round]:
            self.pending_msgs[self.round][instance] = {}

        for target in targets:
            self.pending_msgs[self.round][instance][self.lastid] = (src, target, msg)
            self.pending_msgs_byid[self.lastid] = (src, target, msg, instance, self.round)
            self.lastid += 1

    # Adversarial interface
    def get_pendingmessages(self, instance: str):
        """
        Return all pending messages from ``instance``.
        The return value is a list of tuples of the form (id, round, src, target, msg)
        where id is the message id, round is the round (relative to the instance) at which the message was sent,
        src is the source node, target is the destination node and msg is the message itself.
        :param instance:
        :return:
        """
        if instance not in self.baserounds:
            return []
        return [(id, r - self.baserounds[instance], src, target, msg) for (id, (src, target, msg, inst, r)) in self.pending_msgs_byid.items() if inst == instance]



class NetworkTargets(Enum):
    ALL = 'all'


class NetworkClient:
    ALL = object()

    def __init__(self, id: int, n: int, shared_net: Network = default_net):
        self.id = id
        self.n = n
        self.net = shared_net

    def newinstance(self, instance: str):
        self.net.newinstance(instance)

    def send(self, instance: str, target: Union[int,Iterable[int],object], msg) -> None:
        if isinstance(target, int):
            targets = [target]
        elif target is NetworkClient.ALL:
            targets = range(self.n)
        else:
            targets = target
        self.net.send(instance, self.id, targets, msg)

    def get_messages(self, instance: str, round: int, src: int) -> List:
        return self.net.get_messages(instance, round, self.id, src)

    def get_allmessages(self, instance: str, round: int) -> dict:
        """
        Return all the messages received in a round.

        :param instance:
        :param round:
        :return: The return value is a dict of the form {src1: [s1msg1, s1msg2, ...], src2: [s2msg1, s2msg2],...}
        """
        return self.net.get_allmessages(instance, round, self.id)

    def get_allmessages_contents(self, instance: str, round: int) -> set:
        """
        Return the *contents* of all messages, as a set.
        :param instance:
        :param round:
        :return:
        """
        msgs: Set[str] = set()
        for msglist in self.get_allmessages(instance, round).values():
            msgs.update(msglist)
        return msgs


class IO:
    def __init__(self):
        self.out  = []
        self.inp  = {}

    # For protocol implementation
    def output(self, msg):
        self.out.append(msg)

    def get_input(self, round: int):
        return self.inp.get(round, None)

    # For external caller
    def set_input(self, round: int, inp) -> None:
        self.inp[round] = inp

    def get_outputs(self) -> List:
        return self.out

    def read_outputs(self) -> List:
        """
        Read current outputs, and clear output list.
        :return:
        """
        outputs = self.out
        self.out = []
        return outputs


class SingleInputIO(IO):
    """
    A helper IO class that supports a single input in round 0
    """
    def __init__(self, inp):
        super().__init__()
        self.set_input(0, inp)
