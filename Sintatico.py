from Token import Token
from Constants import *
from Errors import SyntacticError

class Sintatico:

	def __init__(self):
		self.previous_token = None
		self.current_token  = None
		self.stack          = []

	def parse(self, scanner, semantic):
		self.scanner  = scanner
		self.semantic = semantic

		self.stack.clear()

		self.stack.append(0)
		self.previous_token = None

		self.current_token = self.scanner.next_token()

		while True:
			if self.step() != False:
				break

	def step(self):

		if self.current_token == None:
			pos = 0
			if self.previous_token != None:
				pos = self.previous_token.position + len(self.previous_token.lexeme)
			self.current_token = Token(TokenId.DOLLAR, "$", pos)

		token = self.current_token.tkid.value
		state = self.stack[-1]

		cmd = PARSER_TABLE[state][token-1]

		match cmd[0]:
			case SLRAction.SHIFT:
				self.stack.append(cmd[1])
				self.previous_token = self.current_token
				self.current_token = self.scanner.next_token()
				return False
			case SLRAction.REDUCE:
				prod = PRODUCTIONS[cmd[1]]

				for i in range(0, prod[1]):
					self.stack.pop()

				oldstate = self.stack[-1]

				self.stack.append(PARSER_TABLE[oldstate][prod[0]-1][1])

				return False
			case SLRAction.ACTION:
				action = FIRST_SEMANTIC_ACTION + cmd[1] - 1
				self.stack.append(PARSER_TABLE[state][action][1])
				self.semantic.execute_action(cmd[1], self.previous_token)
				return False
			case SLRAction.ACCEPT:
				return True
			case SLRAction.ERROR:
				raise SyntacticError(PARSER_ERROR[state], self.current_token.position)
			case _:
				raise RuntimeError('Invalid Command')

		return False
