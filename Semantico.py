"""Analisador Semântico -- T3.

Cada número de ação (#N na gramática) corresponde a um bloco abaixo. A tabela
completa de QUAL número vai em QUAL ponto da gramática está documentada no
arquivo GRAMATICA_ACOES.md que acompanha esta entrega -- a ordem dos números
aqui é só para organização, o que importa é o `match` ao final.

Estado "pendente": como o parser é ascendente (SLR) e as ações disparam na
ordem em que os tokens são lidos (esquerda para direita), usamos alguns
atributos de instância para "lembrar" informação de um token para o próximo,
dentro do processamento de UM declarador/parâmetro/sub-rotina de cada vez
(nunca há duas dessas coisas sendo processadas ao mesmo tempo, então não há
risco de uma pisar na informação pendente da outra).

Verificação de tipos (ações 20-40): PILHA de tipos. Cada operando empilha o
seu tipo; cada operador desempilha os operandos e empilha o resultado; quem
consome a expressão (atribuição, condição, retorno...) desempilha e confere.
Expressões aninhadas (chamada dentro de índice dentro de chamada...) são
naturais numa pilha, ao contrário do estado "pendente" acima.

Tipo None = desconhecido (variável/parâmetro declarado sem tipo e ainda sem
valor): é aceito em qualquer posição, sem erro -- a linguagem é estilo Python
e a anotação de tipo é opcional. Vetor inteiro (sem índice) tem tipo "int[]".
"""

from functools import lru_cache
from typing import TYPE_CHECKING
from TabelaDeSimbolos import TabelaDeSimbolos, Modalidade
from Errors import SemanticError

if TYPE_CHECKING:
	# Import só para checagem de tipos (ex: no seu editor/IDE); em tempo de
	# execução não é necessário -- só usamos token.lexeme e token.position,
	# então esta classe não precisa do Constants.py gerado para funcionar
	# isoladamente (ex: nos testes deste arquivo).
	from Token import Token


NUMERICOS = ("int", "float")


def compativel(destino, origem) -> bool:
	"""origem pode ser guardada em destino? int -> float é permitido (alargamento)."""
	if destino is None or origem is None:
		return True
	return destino == origem or (destino == "float" and origem == "int")


def _nome_tipo(t) -> str:
	return t if t else "desconhecido"


def tipo_binario(op: str, a, b):
	"""Tipo do resultado de 'a op b', ou levanta ValueError se a combinação é inválida.
	Operando None (desconhecido) nunca causa erro, mas o lado conhecido é conferido."""
	def exige(permitidos):
		for t in (a, b):
			if t is not None and t not in permitidos:
				raise ValueError

	if op in ("||", "&&"):
		exige(("bool",))
		return "bool"
	if op in ("|", "^", "&", "<<", ">>", "%"):
		exige(("int",))
		return "int"
	if op in ("<", ">", "<=", ">="):
		exige(NUMERICOS + ("char",))
		if a and b and (a in NUMERICOS) != (b in NUMERICOS):
			raise ValueError
		return "bool"
	if op in ("==", "!="):
		if a and b and not (a == b or (a in NUMERICOS and b in NUMERICOS)):
			raise ValueError
		return "bool"
	# + - * /
	if op == "+" and "string" in (a, b):
		exige(("string",))
		return "string"
	exige(NUMERICOS)
	if a is None or b is None:
		return None
	return "float" if "float" in (a, b) else "int"


def tipo_unario(op: str, a):
	permitidos = {"-": NUMERICOS, "!": ("bool",), "~": ("int",)}[op]
	if a is not None and a not in permitidos:
		raise ValueError
	return a if op == "-" else permitidos[0]


def tipo_literal(lexema: str) -> str:
	"""Pelo lexema basta: hex (0x..) e binário (0b..) são int; só lit_real tem '.'."""
	if lexema in ("true", "false"):
		return "bool"
	if lexema[0] == '"':
		return "string"
	if lexema[0] == "'":
		return "char"
	return "float" if "." in lexema else "int"


def tipo_valor(simbolo) -> str:
	"""Tipo de um identificador usado SEM índice."""
	if simbolo.modalidade == Modalidade.VETOR and simbolo.tipo:
		return simbolo.tipo + "[]"
	return simbolo.tipo


@lru_cache(maxsize=None)
def tabelas_tem_tipos() -> bool:
	"""O Constants.py gerado usa alguma ação >= 20 (verificação de tipos)?"""
	from Constants import PARSER_TABLE, SLRAction
	return any(c[0] == SLRAction.ACTION and c[1] >= 20 for linha in PARSER_TABLE for c in linha)


@lru_cache(maxsize=None)
def tabelas_tem_propagacao() -> bool:
	"""O Constants.py gerado emite a ação 41 (começo de <declaracao>)?
	Sem ela o grupo de nomes nunca é zerado e o tipo vazaria entre declarações,
	então a propagação do tipo na lista só fica ativa se a gramática tiver o #41."""
	from Constants import PARSER_TABLE, SLRAction
	return any(c[0] == SLRAction.ACTION and c[1] == 41 for linha in PARSER_TABLE for c in linha)


class Semantico:

	def __init__(self, fonte: str = None, checar_tipos: bool = None, propagar_tipo: bool = None):
		# 'fonte' (opcional): com o texto do editor, os avisos dizem 'linha N'.
		self.tabela = TabelaDeSimbolos(fonte)

		# --- nomes inseridos na <declaracao> em andamento (ação 41) ---
		self._grupo = []
		self._anotado_pendente = False   # o declarador atual tem ': tipo' ESCRITO?
		self._propaga = tabelas_tem_propagacao() if propagar_tipo is None else propagar_tipo

		# Tabelas geradas antes das ações 20-40 nunca empilham/desempilham tipos
		# direito (só a 14 empilha); nelas a ação 4 não pode desempilhar.
		self.checar_tipos = tabelas_tem_tipos() if checar_tipos is None else checar_tipos

		# --- estado pendente de um <declarador> (var ...) sendo processado ---
		self._nome_pendente    = None
		self._pos_pendente     = -1
		self._vetor_pendente   = False
		self._tipo_pendente    = None
		self._inic_pendente    = False

		# --- estado pendente de um <nome_param> sendo processado ---
		self._nome_param_pendente  = None
		self._pos_param_pendente   = -1
		self._vetor_param_pendente = False

		# --- nome da função cujo corpo está sendo processado agora (ou None) ---
		self._funcao_atual = None

		# --- verificação de tipos ---
		self._tipos      = []    # pilha de tipos das (sub)expressões
		self._operadores = []    # pilha de (lexema, posição) dos operadores
		self._vetores    = []    # pilha de (Simbolo, posição) de vetores sendo indexados
		self._chamadas   = []    # pilha de (Simbolo, posição) de chamadas abertas
		self._ultima_chamada = None   # chamada que acabou de fechar (ação 24 -> 23)
		self._alvo       = None  # (Simbolo, indexado, posição) da atribuição corrente

	# ------------------------------------------------------------------
	# Despacho
	# ------------------------------------------------------------------

	def execute_action(self, action: int, token: "Token"):
		match action:

			# ---------- DECLARAÇÃO (var ...) -- reusada em escopo global e local ----------
			case 41:  # logo após 'var': começa uma nova <declaracao>
				self._grupo = []
			case 1:   # após 'id' em <nome>
				self._anotado_pendente = False
				self._nome_pendente  = token.lexeme
				self._pos_pendente   = token.position
				self._vetor_pendente = False
				self._tipo_pendente  = None
				self._inic_pendente  = False
			case 2:   # após ']' em <nome> (forma vetor)
				self._vetor_pendente = True
			case 3:   # após <tipo> -- reusada em declarador, parâmetro e tipo_retorno
				self._tipo_pendente = token.lexeme
				self._anotado_pendente = True
			case 4:   # fim de <declarador> com inicializador ('= <exp>')
				tipo_exp = self._tipos.pop() if self.checar_tipos else None
				if self._tipo_pendente is None:
					self._tipo_pendente = tipo_exp   # sem anotação: herda o tipo do valor
				elif not compativel(self._tipo_pendente, tipo_exp):
					raise SemanticError(
						"tipo incompatível: '%s' é %s e recebe valor %s"
						% (self._nome_pendente, self._tipo_pendente, _nome_tipo(tipo_exp)),
						self._pos_pendente,
					)
				self._inic_pendente = True
				self._finalizar_declarador()
			case 5:   # fim de <declarador> sem inicializador
				self._finalizar_declarador()

			# ---------- PARÂMETRO ----------
			case 6:   # após 'id' em <nome_param>
				self._nome_param_pendente  = token.lexeme
				self._pos_param_pendente   = token.position
				self._vetor_param_pendente = False
				self._tipo_pendente        = None
			case 7:   # após ']' em <nome_param> (forma vetor)
				self._vetor_param_pendente = True
			case 8:   # fim de <parametro> (com ou sem tipo anotado)
				self._finalizar_parametro()

			# ---------- SUB-ROTINA ----------
			case 9:   # após 'id' (nome da função), antes de '('
				nome = token.lexeme
				self.tabela.inserir(nome, None, Modalidade.FUNCAO,
				                     inicializado=True, posicao=token.position)
				self.tabela.entrar_escopo(nome)
				self._funcao_atual = nome
			case 10:  # após ')' quando NÃO há tipo de retorno (-> void), antes do '{'
				self._patch_tipo_retorno("void")
			case 11:  # após 'tipo_retorno' quando HÁ tipo de retorno, antes do '{'
				self._patch_tipo_retorno(self._tipo_pendente)
			case 12:  # fim de <tipo_retorno> quando a alternativa é 'void'
				self._tipo_pendente = "void"
			case 13:  # fim de <subrotina> (depois do '}' do corpo)
				self.tabela.sair_escopo()
				self._funcao_atual = None

			# ---------- REFERÊNCIA COMO VALOR (rvalue) -- marca "usado" ----------
			case 14:  # <referencia> ::= id   (variável simples usada numa expressão)
				simbolo = self.tabela.marcar_usado(token.lexeme, token.position)
				self._nao_funcao(simbolo, token.position)
				self._tipos.append(tipo_valor(simbolo))
			case 15:  # <referencia> ::= id [ ...   (base do vetor usada numa expressão)
				simbolo = self.tabela.marcar_usado(token.lexeme, token.position)
				self._exige_vetor(simbolo, token.position)
				self._vetores.append((simbolo, token.position))

			# ---------- REFERÊNCIA COMO ALVO (lvalue) -- marca "inicializado" ----------
			case 16:  # <referencia_alvo> ::= id   (alvo de atribuição/leitura)
				simbolo = self.tabela.marcar_inicializado(token.lexeme, token.position)
				self._nao_funcao(simbolo, token.position)
				self._alvo = (simbolo, False, token.position)
			case 17:  # <referencia_alvo> ::= id [ ...   (vetor como alvo)
				simbolo = self.tabela.marcar_inicializado(token.lexeme, token.position)
				self._exige_vetor(simbolo, token.position)
				self._alvo = (simbolo, True, token.position)

			# ---------- CHAMADA DE SUB-ROTINA ----------
			case 18:  # <chamada> ::= id ( ...   (nome da função sendo chamada)
				simbolo = self.tabela.marcar_usado(token.lexeme, token.position)
				if simbolo.modalidade != Modalidade.FUNCAO:
					raise SemanticError("'%s' não é uma função" % simbolo.nome, token.position)
				self._chamadas.append((simbolo, token.position))

			# ---------- FIM DO PROGRAMA ----------
			case 19:  # fim de <programa>
				self.tabela.finalizar()

			# ---------- TIPOS: OPERANDOS ----------
			case 20:  # depois de qualquer literal (lit_*, true, false)
				self._tipos.append(tipo_literal(token.lexeme))
			case 21:  # depois do ']' em <referencia> -- v[i] vale o tipo do elemento
				simbolo, pos = self._vetores.pop()
				self._exige_indice_int(pos)
				self._tipos.append(simbolo.tipo)
			case 22:  # depois de cada argumento de <lista_argumentos>
				self._tipos.pop()   # ponytail: aridade/tipo dos argumentos não é conferido
			case 23:  # <exp10> ::= <chamada>  -- função usada como valor
				simbolo, pos = self._ultima_chamada
				if simbolo.tipo == "void":
					raise SemanticError(
						"função '%s' é void e não pode ser usada em expressão" % simbolo.nome, pos)
				self._tipos.append(simbolo.tipo)
			case 24:  # depois do ')' de <chamada>
				self._ultima_chamada = self._chamadas.pop()

			# ---------- TIPOS: OPERADORES ----------
			case 25:  # depois de qualquer operador (binário ou unário)
				self._operadores.append((token.lexeme, token.position))
			case 26 | 33 | 34 | 35 | 36 | 37 | 38 | 39 | 40:  # fim de um nível binário de <exp>
				direita, esquerda = self._tipos.pop(), self._tipos.pop()
				op, pos = self._operadores.pop()
				try:
					self._tipos.append(tipo_binario(op, esquerda, direita))
				except ValueError:
					raise SemanticError(
						"operador '%s' não se aplica a %s e %s"
						% (op, _nome_tipo(esquerda), _nome_tipo(direita)), pos) from None
			case 27:  # fim de <exp9> ::= <op_neg> <exp9>
				operando = self._tipos.pop()
				op, pos = self._operadores.pop()
				try:
					self._tipos.append(tipo_unario(op, operando))
				except ValueError:
					raise SemanticError(
						"operador '%s' não se aplica a %s" % (op, _nome_tipo(operando)), pos) from None

			# ---------- TIPOS: CONSUMIDORES DE EXPRESSÃO ----------
			case 28:  # fim de <atribuicao>
				tipo_exp = self._tipos.pop()
				simbolo, indexado, pos = self._alvo
				destino = simbolo.tipo if indexado else tipo_valor(simbolo)
				if destino is None:
					simbolo.tipo = tipo_exp   # sem anotação: a 1ª atribuição define o tipo
				elif not compativel(destino, tipo_exp):
					raise SemanticError(
						"tipo incompatível na atribuição: '%s' é %s e recebe %s"
						% (simbolo.nome, destino, _nome_tipo(tipo_exp)), pos)
			case 29:  # depois do ']' em <referencia_alvo>
				self._exige_indice_int(self._alvo[2])
			case 30:  # condição de if/while/for/do-while
				tipo_exp = self._tipos.pop()
				if tipo_exp is not None and tipo_exp != "bool":
					raise SemanticError("condição deve ser bool, mas é %s" % tipo_exp, token.position)
			case 31:  # depois de cada <exp> do write -- qualquer tipo serve
				self._tipos.pop()
			case 32:  # return <exp>
				tipo_exp = self._tipos.pop()
				funcao = self.tabela.buscar(self._funcao_atual)
				if funcao.tipo == "void":
					raise SemanticError(
						"função '%s' é void e não pode retornar valor" % funcao.nome, token.position)
				if not compativel(funcao.tipo, tipo_exp):
					raise SemanticError(
						"função '%s' retorna %s, mas o return devolve %s"
						% (funcao.nome, funcao.tipo, _nome_tipo(tipo_exp)), token.position)

			case _:
				raise RuntimeError("ação semântica desconhecida: %d" % action)

	# ------------------------------------------------------------------
	# Auxiliares
	# ------------------------------------------------------------------

	def _finalizar_declarador(self):
		modalidade = Modalidade.VETOR if self._vetor_pendente else Modalidade.VARIAVEL
		simbolo = self.tabela.inserir(
			self._nome_pendente, self._tipo_pendente, modalidade,
			inicializado=self._inic_pendente, posicao=self._pos_pendente,
		)
		self._grupo.append(simbolo)

		# 'var a, b, c : int;' -- o tipo ESCRITO no último nome vale para os nomes
		# anteriores da mesma declaração sem tipo e sem '= valor'. Tipo inferido do
		# valor ('var q = 5') nunca se propaga.
		if self._propaga and self._anotado_pendente:
			for anterior in self._grupo[:-1]:
				if anterior.tipo is None and not anterior.inicializado:
					anterior.tipo = simbolo.tipo

	def _finalizar_parametro(self):
		modalidade = Modalidade.VETOR if self._vetor_param_pendente else Modalidade.PARAMETRO
		# parâmetro sempre "tem valor" -- é recebido na chamada da função
		self.tabela.inserir(
			self._nome_param_pendente, self._tipo_pendente, modalidade,
			inicializado=True, posicao=self._pos_param_pendente,
		)

	def _exige_vetor(self, simbolo, posicao):
		if simbolo.modalidade != Modalidade.VETOR:
			raise SemanticError("'%s' não é vetor e não pode ser indexado" % simbolo.nome, posicao)

	def _nao_funcao(self, simbolo, posicao):
		if simbolo.modalidade == Modalidade.FUNCAO:
			raise SemanticError("função '%s' usada como variável" % simbolo.nome, posicao)

	def _exige_indice_int(self, posicao):
		tipo_indice = self._tipos.pop()
		if tipo_indice is not None and tipo_indice != "int":
			raise SemanticError("índice de vetor deve ser int, mas é %s" % tipo_indice, posicao)

	def _patch_tipo_retorno(self, tipo: str):
		"""A função já foi inserida (ação 9) com tipo=None como 'placeholder',
		porque o tipo de retorno só é conhecido depois dos parâmetros. Agora
		que sabemos, corrigimos o campo 'tipo' do símbolo já existente --
		buscando pelo nome enquanto AINDA estamos dentro do escopo da função
		(buscar() sobe a pilha e encontra a função no escopo global de fora)."""
		simbolo = self.tabela.buscar(self._funcao_atual)
		simbolo.tipo = tipo
