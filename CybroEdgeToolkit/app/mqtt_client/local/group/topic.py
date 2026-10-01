from typing import List


class Topic:
    SEPARATOR = "/"

    def __init__(self, topic: str):
        self._levels: List[str] = topic.split(Topic.SEPARATOR)

    def __repr__(self) -> str:
        return Topic.SEPARATOR.join(self._levels)

    def get_level(self, index: int)-> str:
        return self._levels[index]

    def match(self, other: 'Topic')-> bool:
        for i in range(len(self._levels)):
            level = self.get_level(i)
            other_level = other.get_level(i)

            if level == '#' or other_level == '#':
                break

            if level != other_level and level != '+' and other_level != '+':
                return False

        return True

    def match_str(self, other: str)-> bool:
        return self.match(Topic(other))
