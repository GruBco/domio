from typing import Generator, NewType

from scgi_server.local.general.errors import TransactionIdGeneratorError

TransactionIdGeneratorType = NewType('TransactionIdGeneratorType',
                                     Generator[int, int, None])


def transaction_id_generator(from_id: int, to_id: int, step: int = 1
                             ) -> TransactionIdGeneratorType:
    if from_id == to_id:
        raise TransactionIdGeneratorError(
            "`from_id` can't be equal to `to_id`"
        )

    t_id = from_id

    while True:
        yield t_id

        t_id += step
        if t_id == to_id:
            t_id = from_id
