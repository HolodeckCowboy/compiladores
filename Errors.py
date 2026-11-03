from dataclasses import dataclass

@dataclass
class AnalysisError(Exception):
	message:  str
	position: int = -1

# São funcionalmente idênticos ao AnalysisError
class SemanticError(AnalysisError):
	pass

class SyntacticError(AnalysisError):
	pass

class LexicalError(AnalysisError):
	pass
