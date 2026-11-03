
from dataclasses import dataclass
from Constants import TokenId

@dataclass(frozen=True)
class Token:
	tkid:     TokenId = TokenId.EPSILON
	lexeme:   str     = ""
	position: int     = -1
