"""Mensagens de erro específicas por estado, para os analisadores léxico e sintático.

O GALS gera `SCANNER_ERRORS` com textos genéricos ("Erro identificando lit_hex") e
`PARSER_ERROR` com um texto inútil por estado ("Erro estado 38"). Este módulo substitui
o conteúdo das duas listas **no lugar** (slice assignment), de modo que `Lexico` e
`Sintatico` — que fizeram `from Constants import *` e portanto apontam para os mesmos
objetos — passem a levantar os erros com o texto novo.

Vantagem: `Constants.py` continua intocado e pode ser regerado pelo GALS sem perder nada.
Basta `import mensagens` antes de compilar.

Fonte: tabelas_analise_m2_python_v2.xlsx (aba "Lexica", 54 estados), e para o sintático
a tabela SLR gerada de m2_python_v3.vgls (269 estados e 57 terminais).

Erros semânticos têm texto próprio em Semantico.py / TabelaDeSimbolos.py.
"""

import Constants
from Constants import PARSER_TABLE, SCANNER_ERRORS, PARSER_ERROR, SLRAction, TokenId

# ---------------------------------------------------------------------------
# Léxico — um texto por estado de erro do AFD (aba "Lexica")
# ---------------------------------------------------------------------------

ESCAPES_VALIDAS = r"\n, \t, \r, \\, \" e \'"

# Nota: os estados 37, 38 e 39 (real/binário/hexadecimal incompletos) raramente disparam.
# O scanner faz maximal munch com retrocesso: em "1." ele devolve lit_int "1" e o "." vira
# caractere inválido no estado 0; em "0x" devolve lit_int "0" e "x" vira um id. As mensagens
# ficam aqui porque a tabela prevê os estados, mas o erro costuma aparecer como 0 ou no sintático.

ERROS_LEXICOS = {
	0:  "caractere inválido",
	3:  'literal de string não fechado: esperado " antes do fim da linha',
	6:  "literal de caractere mal formado: esperado um caractere ou uma sequência de escape",
	31: "sequência de escape inválida em literal de string (válidas: %s)" % ESCAPES_VALIDAS,
	33: "literal de caractere não fechado: esperado ' (apenas um caractere é permitido)",
	34: "sequência de escape inválida em literal de caractere (válidas: %s)" % ESCAPES_VALIDAS,
	35: "comentário de bloco não fechado: esperado */",
	37: "literal real mal formado: esperado ao menos um dígito depois do ponto",
	38: "literal binário mal formado: esperado dígitos 0 ou 1 depois de 0b",
	39: "literal hexadecimal mal formado: esperado dígitos hexadecimais depois de 0x",
	47: "comentário de bloco não fechado: esperado */",
	51: "comentário de bloco não fechado: esperado */",
	53: "comentário de bloco não fechado: esperado */",
}

# ---------------------------------------------------------------------------
# Sintático — nomes legíveis dos 57 terminais
# ---------------------------------------------------------------------------

DESCRICAO_TOKEN = {
	"DOLLAR": "o fim do arquivo",
	"t_id": "identificador",
	"t_lit_hex": "literal hexadecimal",
	"t_lit_bin": "literal binário",
	"t_lit_real": "literal real",
	"t_lit_int": "literal inteiro",
	"t_lit_char": "literal de caractere",
	"t_lit_string": "literal de string",
	"t_plus": "'+'", "t_minus": "'-'", "t_mult": "'*'", "t_divide": "'/'",
	"t_modulo": "'%'", "t_equal_to": "'=='", "t_not_equal": "'!='",
	"t_greater_equal": "'>='", "t_less_equal": "'<='", "t_greater_than": "'>'",
	"t_less_than": "'<'", "t_logical_and": "'&&'", "t_logical_or": "'||'",
	"t_logical_not": "'!'", "t_shift_left": "'<<'", "t_shift_right": "'>>'",
	"t_bit_and": "'&'", "t_bit_or": "'|'", "t_bit_xor": "'^'", "t_bit_not": "'~'",
	"t_assign": "'='", "t_semicolon": "';'", "t_colon": "':'", "t_comma": "','",
	"t_lparen": "'('", "t_rparen": "')'", "t_lbracket": "'['", "t_rbracket": "']'",
	"t_lbrace": "'{'", "t_rbrace": "'}'",
}


def descricao(tok):
	"""Nome legível de um terminal; palavras reservadas viram o próprio lexema."""
	if tok.name in DESCRICAO_TOKEN:
		return DESCRICAO_TOKEN[tok.name]
	return "'%s'" % tok.name[2:]  # t_if -> 'if', t_function -> 'function', ...


def _conjunto(*nomes):
	return frozenset(TokenId[n] for n in nomes)


# Grupos de terminais que valem mais como um nome só do que como lista de 20 itens.
# A ordem importa: o primeiro grupo que couber é retirado do conjunto restante.
GRUPOS = [
	("um comando", _conjunto(
		"t_id", "t_if", "t_while", "t_do", "t_return", "t_for", "t_read", "t_write",
		"t_var", "t_lbrace")),
	("uma expressão", _conjunto(
		"t_id", "t_true", "t_false", "t_lit_hex", "t_lit_bin", "t_lit_real", "t_lit_int",
		"t_lit_char", "t_lit_string", "t_minus", "t_logical_not", "t_bit_not", "t_lparen")),
	("um operador", _conjunto(
		"t_plus", "t_minus", "t_mult", "t_divide", "t_modulo", "t_equal_to", "t_not_equal",
		"t_greater_equal", "t_less_equal", "t_greater_than", "t_less_than", "t_logical_and",
		"t_logical_or", "t_shift_left", "t_shift_right", "t_bit_and", "t_bit_or", "t_bit_xor")),
	("um tipo", _conjunto("t_int", "t_float", "t_char", "t_string", "t_bool")),
]

# ---------------------------------------------------------------------------
# Estados de "nível global" e de "nível misto".
#
# São dezenas de estados de redução cujo conjunto esperado é o FOLLOW inteiro:
# a lista derivada sai com 11-14 alternativas soltas e não diz nada. Em vez de
# enumerar os números de estado (que mudam a cada regeração do GALS), eles são
# identificados pela assinatura — o conjunto exato de terminais aceitos.
# ---------------------------------------------------------------------------

NIVEL_GLOBAL = _conjunto(
	"DOLLAR", "t_id", "t_if", "t_while", "t_do", "t_for", "t_read", "t_write",
	"t_function", "t_var", "t_lbrace")

NIVEL_MISTO = _conjunto(
	"DOLLAR", "t_id", "t_if", "t_while", "t_do", "t_return", "t_for", "t_read",
	"t_write", "t_function", "t_var", "t_lbrace", "t_rbrace")

NIVEL_MISTO_ELSE = NIVEL_MISTO | _conjunto("t_else")

ASSINATURAS = {
	NIVEL_GLOBAL:
		"esperado uma declaração ('var'), uma sub-rotina ('function') ou um comando",
	NIVEL_MISTO:
		"esperado um comando, uma declaração ('var'), uma sub-rotina ('function'), "
		"'}' ou o fim do arquivo",
	NIVEL_MISTO_ELSE:
		"esperado um comando, 'else', uma declaração ('var'), uma sub-rotina "
		"('function'), '}' ou o fim do arquivo",
}

# ---------------------------------------------------------------------------
# Estados cuja mensagem derivada ficaria vaga ou perderia o contexto.
# Os números vêm da tabela SLR da aba "SLR1".
# ---------------------------------------------------------------------------

ERROS_SINTATICOS = {
	1:   "esperado o fim do arquivo",
	2:   "esperado o fim do arquivo",
	25:  "esperado o fim do arquivo",
	26:  "esperado o fim do arquivo",
	# --- declaração: var nome[, nome] [: tipo] [= exp] ;
	15:  "esperado o nome da variável depois de 'var'",
	35:  "declarador inválido: esperado '=', '[', ':', ',' ou ';' depois do identificador",
	64:  "declarador inválido: esperado '=', '[', ':', ',' ou ';' depois do identificador",
	60:  "esperado o nome da próxima variável depois de ','",
	62:  "esperado um tipo (int, float, char, string ou bool) depois de ':'",
	120: "vetor precisa de tamanho fixo: esperado um literal inteiro dentro de '[ ]'",
	176: "esperado ']' para fechar o tamanho do vetor",
	# --- sub-rotina: function nome ( params ) [: tipo_retorno] { ... }
	6:   "esperado o nome da sub-rotina depois de 'function'",
	27:  "esperado '(' com a lista de parâmetros da sub-rotina",
	58:  "esperado '(' com a lista de parâmetros da sub-rotina",
	111: "lista de parâmetros inválida: esperado o nome de um parâmetro ou ')'",
	173: "parâmetro inválido: esperado ':', '[', ',' ou ')' depois do nome",
	202: "parâmetro inválido: esperado ':', '[', ',' ou ')' depois do nome",
	198: "esperado ':' com o tipo de retorno ou '{' para abrir o corpo da sub-rotina",
	201: "esperado o tipo do parâmetro (int, float, char, string ou bool) depois de ':'",
	229: "esperado ']': parâmetro vetor é declarado como 'nome[] : tipo'",
	226: "esperado o tipo de retorno: 'void', int, float, char, string ou bool",
	# --- condicional e laços
	20:  "esperado '(' com a condição do 'if'",
	21:  "esperado '(' com a condição do 'while'",
	22:  "esperado '(' com o cabeçalho do 'for'",
	44:  "esperado o identificador da inicialização do 'for'",
	45:  "esperado 'while' para fechar o laço 'do ... while (...);'",
	102: "esperado '(' com a condição do 'do ... while'",
	194: "esperado 'then' depois da condição do 'if'",
	195: "esperado 'do' depois da condição do 'while'",
	166: "esperado a condição do 'for' depois do primeiro ';'",
	221: "esperado '{': o corpo do 'then' precisa ser um bloco entre chaves",
	245: "esperado o identificador da pós-operação do 'for'",
	246: "esperado ';' para fechar o laço 'do ... while (...);'",
	255: "esperado '{': o corpo do 'else' precisa ser um bloco entre chaves",
	# --- entrada e saída
	17:  "esperado '(' depois de 'read'",
	18:  "esperado '(' depois de 'write'",
	37:  "esperado uma variável ou posição de vetor dentro de 'read'",
	158: "esperado uma variável ou posição de vetor depois de ','",
}


# A parte de ação da tabela tem uma coluna por terminal (TokenId sem o EPSILON);
# depois dela vêm as colunas de GOTO dos não-terminais.
TERMINAIS = [t for t in TokenId if t.value > 0]


def esperados(estado):
	"""Terminais aceitos pelo estado, na ordem em que aparecem na tabela."""
	linha = PARSER_TABLE[estado][:len(TERMINAIS)]
	return [TokenId(i + 1) for i, cmd in enumerate(linha) if cmd[0] != SLRAction.ERROR]


def mensagem_sintatica(estado):
	"""Mensagem específica do estado; deriva da tabela quando não há texto curado."""
	if estado in ERROS_SINTATICOS:
		return ERROS_SINTATICOS[estado]

	restantes = set(esperados(estado))
	if not restantes:
		return "construção inválida neste ponto"
	if frozenset(restantes) in ASSINATURAS:
		return ASSINATURAS[frozenset(restantes)]

	partes = []
	for nome, grupo in GRUPOS:
		if grupo <= restantes:
			partes.append(nome)
			restantes -= grupo
	partes += [descricao(t) for t in sorted(restantes, key=lambda t: t.value)]

	if len(partes) == 1:
		return "esperado %s" % partes[0]
	return "esperado %s ou %s" % (", ".join(partes[:-1]), partes[-1])


def aplicar():
	"""Troca o conteúdo das listas do GALS pelas mensagens deste módulo, no lugar."""
	SCANNER_ERRORS[:] = [
		ERROS_LEXICOS.get(estado, texto) for estado, texto in enumerate(SCANNER_ERRORS)
	]
	PARSER_ERROR[:] = [mensagem_sintatica(estado) for estado in range(len(PARSER_ERROR))]


aplicar()


if __name__ == "__main__":
	assert Constants.PARSER_ERROR[194] == "esperado 'then' depois da condição do 'if'"
	assert Constants.PARSER_ERROR[120].startswith("vetor precisa")
	# assinaturas de nível
	assert Constants.PARSER_ERROR[0] == ASSINATURAS[NIVEL_GLOBAL]
	assert Constants.PARSER_ERROR[59] == ASSINATURAS[NIVEL_MISTO]
	assert Constants.PARSER_ERROR[109] == ASSINATURAS[NIVEL_MISTO_ELSE]
	# derivados da tabela, sem curadoria
	assert Constants.PARSER_ERROR[8] == "esperado ';'"
	assert Constants.PARSER_ERROR[36] == "esperado uma expressão"
	assert Constants.PARSER_ERROR[219] == "esperado uma expressão ou ')'"
	assert Constants.PARSER_ERROR[56] == "esperado '}'"
	assert Constants.PARSER_ERROR[57] == "esperado um comando ou '}'"
	assert Constants.PARSER_ERROR[265] == "esperado um comando"
	assert Constants.SCANNER_ERRORS[38].startswith("literal binário mal formado")
	assert Constants.SCANNER_ERRORS[0] == "caractere inválido"
	# estados sem erro léxico próprio mantêm o texto original (vazio)
	assert Constants.SCANNER_ERRORS[1] == ""
	for estado in range(len(Constants.PARSER_ERROR)):
		print(estado, Constants.PARSER_ERROR[estado])
