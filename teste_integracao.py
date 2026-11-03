"""Simula a sequência de chamadas a execute_action() que o parser REAL faria
ao compilar este programa:

    var a: int, vetor[5];

    function soma(x: int, y: int): int {
       return x + y;
    }

    a = soma(1, 2);
    write(a);
    read(vetor[0]);
    write(vetor[0]);

Isso valida a lógica inteira do Semantico.py SEM precisar regenerar nada no
WebGALS -- simulamos o parser chamando execute_action na ordem em que os
tokens apareceriam, com o número de ação que colocaríamos em cada ponto da
gramática (ver GRAMATICA_ACOES.md).
"""

from dataclasses import dataclass
from Semantico import Semantico
from TabelaDeSimbolos import Modalidade


@dataclass
class TokenFalso:
	lexeme: str
	position: int


def tok(lexeme, pos):
	return TokenFalso(lexeme, pos)


sem = Semantico()

seq = [
	# var a: int, vetor[5];
	(1, tok("a", 4)),
	(3, tok("int", 7)),
	(5, tok(":", -1)),          # fim do declarador "a: int" (sem '=')
	(1, tok("vetor", 13)),
	(2, tok("]", -1)),          # vetor[5] -- marca é_vetor
	(5, tok(";", -1)),          # fim do declarador "vetor[5]" (sem tipo, sem '=')

	# function soma(x: int, y: int): int {
	(9,  tok("soma", 30)),
	(6,  tok("x", 35)),
	(3,  tok("int", 38)),
	(8,  tok(")", -1)),         # fim do parâmetro x: int
	(6,  tok("y", 43)),
	(3,  tok("int", 46)),
	(8,  tok(")", -1)),         # fim do parâmetro y: int
	(3,  tok("int", 52)),       # tipo de retorno
	(11, tok("{", -1)),         # patch do tipo de retorno = int

	#    return x + y;
	(14, tok("x", 65)),         # x usado na expressão
	(14, tok("y", 69)),         # y usado na expressão

	# }
	(13, tok("}", -1)),         # fim da função -- sai do escopo

	# a = soma(1, 2);
	(16, tok("a", 80)),         # 'a' como alvo -- marcar_inicializado
	(18, tok("soma", 84)),      # chamada de soma -- marcar_usado

	# write(a);
	(14, tok("a", 95)),         # 'a' usado dentro do write

	# read(vetor[0]);
	(17, tok("vetor", 105)),    # 'vetor' como alvo (via read) -- marcar_inicializado

	# write(vetor[0]);
	(15, tok("vetor", 120)),    # 'vetor' usado dentro do write

	# fim do programa
	(19, tok("$", -1)),
]

for numero, token in seq:
	sem.execute_action(numero, token)

t = sem.tabela

# --- símbolos esperados no histórico ---
nomes = {s.nome: s for s in t.historico}

assert nomes["a"].tipo == "int"
assert nomes["a"].modalidade == Modalidade.VARIAVEL
assert nomes["a"].usado is True
assert nomes["a"].inicializado is True
print("OK: 'a' -- tipo=int, modalidade=VARIAVEL, usado=True, inicializado=True")

assert nomes["vetor"].tipo is None
assert nomes["vetor"].modalidade == Modalidade.VETOR
assert nomes["vetor"].usado is True
assert nomes["vetor"].inicializado is True
print("OK: 'vetor' -- modalidade=VETOR, usado=True, inicializado=True (sem tipo anotado)")

assert nomes["soma"].tipo == "int"
assert nomes["soma"].modalidade == Modalidade.FUNCAO
assert nomes["soma"].usado is True
assert nomes["soma"].escopo == "global"
print("OK: 'soma' -- tipo de retorno corrigido para int, modalidade=FUNCAO, usado=True")

assert nomes["x"].modalidade == Modalidade.PARAMETRO
assert nomes["x"].tipo == "int"
assert nomes["x"].escopo == "soma"
assert nomes["x"].usado is True
print("OK: 'x' -- parâmetro, tipo=int, escopo='soma', usado dentro do corpo")

assert nomes["y"].usado is True
print("OK: 'y' -- parâmetro, também usado")

# --- nenhum aviso deveria ter sido gerado (tudo foi usado) ---
assert t.avisos == [], f"avisos inesperados: {t.avisos}"
print("OK: nenhum aviso gerado -- todo identificador foi usado")

# --- pilha de escopos deve estar vazia após finalizar() ---
assert t._pilha == []
print("OK: finalizar() fechou o escopo global corretamente")

print("\nSimulação de ponta a ponta (caminho feliz) passou sem erros.\n")

# ===========================================================================
# Cenário 2: duplicidade no mesmo escopo -- "var a: int; var a: float;"
# ===========================================================================
from Errors import SemanticError

sem2 = Semantico()
sem2.execute_action(1, tok("a", 4))
sem2.execute_action(3, tok("int", 7))
sem2.execute_action(5, tok(";", -1))
try:
	sem2.execute_action(1, tok("a", 15))
	sem2.execute_action(3, tok("float", 18))
	sem2.execute_action(5, tok(";", -1))
	assert False, "deveria ter lançado SemanticError"
except SemanticError as e:
	assert "já declarado" in e.message
	print("OK cenário 2: redeclarar 'a' no mesmo escopo lança SemanticError")

# ===========================================================================
# Cenário 3: usar identificador fora do escopo da função -- vazamento
# ===========================================================================
# function f() { var local: int; }
# write(local);   <- 'local' não deveria ser visível aqui fora
sem3 = Semantico()
sem3.execute_action(9, tok("f", 0))          # entra na função f
sem3.execute_action(1, tok("local", 15))
sem3.execute_action(3, tok("int", 22))
sem3.execute_action(5, tok(";", -1))
sem3.execute_action(10, tok("{", -1))        # sem tipo de retorno -> void
sem3.execute_action(13, tok("}", -1))        # sai da função f
try:
	sem3.execute_action(14, tok("local", 40))  # write(local) fora de f
	assert False, "deveria lançar SemanticError -- 'local' não é visível aqui"
except SemanticError as e:
	assert "não declarado" in e.message
	print("OK cenário 3: variável local de função não vaza para o nível global")

# ===========================================================================
# Cenário 4: declarado e nunca usado -- vira aviso, não erro
# ===========================================================================
sem4 = Semantico()
sem4.execute_action(1, tok("inutil", 4))
sem4.execute_action(3, tok("int", 7))
sem4.execute_action(5, tok(";", -1))
sem4.execute_action(19, tok("$", -1))  # fim do programa -- finaliza escopo global
avisos4 = sem4.tabela.avisos
assert any("inutil" in a and "nunca usado" in a for a in avisos4)
print("OK cenário 4: variável global nunca usada gera aviso (não trava a compilação)")

# ===========================================================================
# Cenário 5: usado possivelmente sem valor inicial -- vira aviso
# ===========================================================================
# var n: int;        (sem '=')
# write(n);           <- usa n sem nunca ter atribuído/lido valor
sem5 = Semantico()
sem5.execute_action(1, tok("n", 4))
sem5.execute_action(3, tok("int", 7))
sem5.execute_action(5, tok(";", -1))     # sem '=' -> inicializado=False
sem5.execute_action(14, tok("n", 20))    # usado dentro de write(n)
avisos5 = sem5.tabela.avisos
assert any("n" in a and "sem valor inicial" in a for a in avisos5)
print("OK cenário 5: usar variável sem inicializar gera aviso de possível lixo de memória")

# ===========================================================================
# Cenário 6: read() inicializa -- NÃO deveria soar o aviso do cenário 5
# ===========================================================================
sem6 = Semantico()
sem6.execute_action(1, tok("n", 4))
sem6.execute_action(3, tok("int", 7))
sem6.execute_action(5, tok(";", -1))
sem6.execute_action(16, tok("n", 15))    # read(n) -- é alvo, marcar_inicializado
sem6.execute_action(14, tok("n", 25))    # write(n) depois -- agora já tem valor
avisos6 = [a for a in sem6.tabela.avisos if "sem valor inicial" in a]
assert avisos6 == []
print("OK cenário 6: read(n) antes do uso evita o aviso de valor não inicializado")

# ===========================================================================
# Cenário 7: tipos -- var s: string = "a"; var x: int = s * s;
# (checar_tipos=True: não depende do Constants.py já ter as ações 20-40)
# ===========================================================================
sem7 = Semantico(checar_tipos=True)
sem7.execute_action(1, tok("s", 4))
sem7.execute_action(3, tok("string", 7))
sem7.execute_action(20, tok('"a"', 16))
sem7.execute_action(4, tok('"a"', 16))
sem7.execute_action(1, tok("x", 25))
sem7.execute_action(3, tok("int", 28))
sem7.execute_action(14, tok("s", 34))
sem7.execute_action(25, tok("*", 36))
sem7.execute_action(14, tok("s", 38))
try:
	sem7.execute_action(40, tok("s", 38))   # fim do nível * / %
	assert False, "string * string deveria lançar SemanticError"
except SemanticError as e:
	assert "'*'" in e.message and e.position == 36
	print("OK cenário 7: multiplicação de strings é barrada na posição do operador")

# ===========================================================================
# Cenário 8: tipos -- var f: float = 1 + 2;   (int -> float é permitido)
#                     f = true;               (bool -> float não é)
# ===========================================================================
sem8 = Semantico(checar_tipos=True)
sem8.execute_action(1, tok("f", 4))
sem8.execute_action(3, tok("float", 7))
sem8.execute_action(20, tok("1", 15))
sem8.execute_action(25, tok("+", 17))
sem8.execute_action(20, tok("2", 19))
sem8.execute_action(39, tok("2", 19))       # fim do nível + -
sem8.execute_action(4, tok("2", 19))
sem8.execute_action(16, tok("f", 22))
sem8.execute_action(20, tok("true", 26))
try:
	sem8.execute_action(28, tok("true", 26))
	assert False, "bool -> float deveria lançar SemanticError"
except SemanticError as e:
	assert "incompatível" in e.message
	print("OK cenário 8: int em float aceito; bool em float barrado")

print("\nTodos os 8 cenários de integração passaram.")
