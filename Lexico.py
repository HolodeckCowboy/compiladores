from Constants import *
from Errors    import LexicalError
from Token     import Token

class Lexico:

	def __init__(self, input: str = None):
		self.set_input(input)

	def set_input(self, input: str):
		self.input    = input
		self.position = 0

	def next_token(self):

		if self.has_input() == False:
			return None

		start    = self.position
		state    = 0
		oldState = 0
		endState = -1
		end      = -1

		while self.has_input():

			oldState = state
			state    = self.next_state(self.next_char(), state)

			if state < 0:
				break

			else:
				if self.token_for_state(state) >= 0:
					endState = state
					end      = self.position

		if endState < 0 or (endState != state and self.token_for_state(oldState) == -2):
			raise LexicalError(SCANNER_ERRORS[oldState], start)

		self.position = end

		token = self.token_for_state(endState)

		if token == 0:
			return self.next_token()
		else:
			lexeme = self.input[start:end]
			if TOKEN_DEPENDENCY or CASE_INSENSITIVITY:
				token = self.lookup_token(token, lexeme)
			return Token(TokenId(token), lexeme, start)

	def next_state(self, c: int, state: int):
		return SCANNER_TABLE[state][c]

	def token_for_state(self, state: int):
		token = -1

		if state >= 0 and state < STATES_COUNT:
			token = TOKEN_STATE[state]

		return token

	def lookup_token(self, base: int, key: str):
		start =  SPECIAL_CASES_INDEXES[base]
		end   =  SPECIAL_CASES_INDEXES[base+1]-1

		key_u = key
		if CASE_INSENSITIVITY:
			key_u = key.upper()

		while start <= end:
			half    = (start + end) // 2
			current = SPECIAL_CASES_KEYS[half]

			if current == key_u:
				return TokenId(SPECIAL_CASES_VALUES[half])
			elif current < key_u:
				start = half + 1
			else:
				end   = half - 1

		return base

	def has_input(self):
		return self.position < len(self.input)

	def next_char(self):
		if self.has_input():
			res = self.input[self.position]
			self.position += 1
			return ord(res)
		else:
			return -1

