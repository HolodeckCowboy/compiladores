from Lexico import Lexico
from Sintatico import Sintatico
from Semantico import Semantico
from Errors import AnalysisError

lex = Lexico("")
syn = Sintatico()
sem = Semantico()

try:
	syn.parse(lex, sem)
except AnalysisError as e:
	print(e)
