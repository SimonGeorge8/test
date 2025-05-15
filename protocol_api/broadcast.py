from typing import List
from .protocol import Node

class ByzantineBroadcast(Node):
    @classmethod
    def get_maxrounds(cls):
        return 4

    def protocol(self, round: int) -> bool:
        if round == 0:
            self.outval = None
            self.sender_id, sender_inp = self.get_input(0)
            if self.id == self.sender_id:
                self.send(self.net.ALL, sender_inp)
        elif round < self.get_maxrounds() - 1:
            received = self.get_messages(round - 1, self.sender_id)
            # We will output the first message received.
            if len(received) > 0 and self.outval is None:
                self.outval = received[0]
        else: # round == self.get_maxrounds() - 1
            if self.outval is not None:
                self.output(self.outval)
            else:
                self.output(0)
            return True

        return False

class InconsistentByzantineBroadcast(ByzantineBroadcast):
    def adversary_set_outputs(self, outputs: List[str]) -> None:
        """
        The adversary can call this method to set the outputs *for all parties*.
        This method can only be called by the *sender* (i.e., the input at round 0 was (id, xxx), and id == self.id),
        and must be called before round 1 is executed in order to have an effect.
        :param outputs: a list of outputs. Party i will output `outputs[i]` at the end of the protocol.
        """
        self.inconsistent_outputs = outputs

    def protocol(self, round: int) -> bool:
        retval = super().protocol(round)
        if round == 1 and self.sender_id == self.id:
            # Allow overriding previous output
            try:
                for i, outval in enumerate(self.inconsistent_outputs):
                    self.send(i, outval)
            except AttributeError:
                pass
        elif round == 2:
            # Check if there was an override message
            received = self.get_messages(1, self.sender_id)
            # We will output the first message received.
            if len(received) > 0:
                self.outval = received[0]

        return retval




class InvalidByzantineBroadcast(ByzantineBroadcast):
    def adversary_set_output(self, output: str) -> None:
        """
        The adversary can call this method to set a common output for all parties.
        This method can be called by any corrupt party (not only the sender),
        but must be called before round 1 in order have an effect.
        :param output: an output. All honest parties will output `output` at the end of the protocol.
        """
        self.invalid_output = output

    def protocol(self, round: int) -> bool:
        retval = super().protocol(round)
        if round == 1:
            # Allow overriding previous output
            try:
                self.send(self.net.ALL, self.invalid_output)
            except AttributeError:
                pass
        elif round == 2:
            # Check if there was an override message
            received = self.get_allmessages_contents(1)
            # We will output the first message received.
            if len(received) == 1:
                self.outval = received.pop()

        return retval
