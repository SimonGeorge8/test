from typing import Union, Type

from .broadcast import ByzantineBroadcast, InconsistentByzantineBroadcast, InvalidByzantineBroadcast
from .net import IO, SingleInputIO
from .protocol import Node


class TotallyNaiveBlockchain(Node):
    def protocol(self, round: int) -> bool:
        if round == 0:
            # Initialization
            self.pending_inputs = set()
            self.outputs = set()

        if round > 0:
            received = self.get_messages(round - 1, (round - 1) % self.n)
            for msg in received:
                self.output(msg)
            self.outputs.update(received)
            self.pending_inputs.difference_update(received)

        inputs = self.get_input(round)
        if inputs:
            self.pending_inputs.update(set(inputs).difference(self.outputs))  # Add inputs that weren't output yet
        if round % self.n == self.id:
            # I'm the sender. Send my inputs to everyone.
            for inp in self.pending_inputs:
                self.send(self.net.ALL, inp)

        return False  # Blockchain never dies!


class ByzantineBroadcastBlockchain(Node):
    def __init__(self, bbclass: Type[ByzantineBroadcast], *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.bbclass = bbclass
        self.R = bbclass.get_maxrounds()

        # Set of inputs I've received that haven't been output yet
        self.pending_inputs = set()

        # Set of outputs
        self.outputs = set()

        # The node for the current BB instance
        self.bbnode: Union[Node, None] = None

        # IO client for the current BB instance
        self.bbio: Union[IO, None] = None

    def protocol(self, round: int) -> bool:
        k = int(round / self.R)

        # Update any inputs received in this round.
        round_inputs = self.get_input(round)
        if round_inputs:
            inputs = set(round_inputs)
            inputs.difference_update(self.outputs)
            self.pending_inputs.update(inputs)

        if round % self.R == 0:
            # Start new BB instance
            sender = k % self.n
            if sender == self.id:
                # I'm the sender in this BB instance.
                # BB expects a single string as input, so we serialize the pending inputs.
                bbinputs = "|".join(self.pending_inputs)
            else:
                # I'm not the sender in this BB instance, so don't my BB node won't have inputs
                bbinputs = None

            # Create an IO client for the BB instance.
            # the SingleInputIO is a subclass of IO that sends input only in the first round.
            self.bbio = SingleInputIO((sender, bbinputs))

            # Start a new subprotocol for the BB isntance.
            self.bbnode = self.start_subprotocol(self.bbclass, "BB" + str(k), self.bbio)

            # The BB-instance's round 0 is the current round.
            self.bbbaseround = round

        # Execute a protocol round in the BB subprotocol
        self.bbnode.protocol(round - self.bbbaseround)

        # Read any output from the BB instance.
        outputstrs = self.bbio.read_outputs()
        for out in outputstrs:
            # We actually only expect a single, string output, which we deserialze.
            outputs = str(out).split("|")
            for single_output in outputs:
                self.output(single_output)
            self.pending_inputs.difference_update(outputs)
            self.outputs.update(outputs)

        return False  # Blockchain never dies!


class InconsistentBroadcastBlockchain(ByzantineBroadcastBlockchain):
    def __init__(self, *args, **kwargs):
        super().__init__(InconsistentByzantineBroadcast, *args, **kwargs)


class InvalidBroadcastBlockchain(ByzantineBroadcastBlockchain):
    def __init__(self, *args, **kwargs):
        super().__init__(InvalidByzantineBroadcast, *args, **kwargs)
