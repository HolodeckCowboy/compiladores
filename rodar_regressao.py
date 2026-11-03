"""Regressão automática da análise semântica.

Roda todos os testes/teste*.txt, compara cada resultado com o arquivo de
mesmo nome em testes/esperado/ e diz PASSOU ou FALHOU (mostrando a diferença).

Uso:   python rodar_regressao.py
Rode SEMPRE depois de mexer na gramática, no Semantico.py ou na
TabelaDeSimbolos.py -- se tudo der PASSOU, nada do que estava validado quebrou.
"""

import difflib
import glob
import os
import sys

from Lexico import Lexico
from Sintatico import Sintatico
from testar_semantica import formatar

PASTA = os.path.dirname(os.path.abspath(__file__))


def normalizar(texto: str) -> str:
	return "\n".join(l.rstrip() for l in texto.replace("\r\n", "\n").strip().split("\n"))


passou = falhou = 0
for caminho in sorted(glob.glob(os.path.join(PASTA, "testes", "teste*.txt"))):
	nome = os.path.basename(caminho)
	arq_esperado = os.path.join(PASTA, "testes", "esperado", nome)
	if not os.path.exists(arq_esperado):
		print("SEM ESPERADO  %s (pule ou crie esperado/%s)" % (nome, nome))
		continue
	fonte = open(caminho, encoding="utf-8").read()
	try:
		obtido = normalizar(formatar(nome, fonte, lambda sem: Sintatico().parse(Lexico(fonte), sem)))
	except Exception as exc:   # erro de programacao: nao derruba a rodada inteira
		falhou += 1
		print("FALHOU   %s  (excecao inesperada: %s: %s)" % (nome, type(exc).__name__, exc))
		continue
	esperado = normalizar(open(arq_esperado, encoding="utf-8").read())
	if obtido == esperado:
		passou += 1
		print("PASSOU   %s" % nome)
	else:
		falhou += 1
		print("FALHOU   %s" % nome)
		for linha in difflib.unified_diff(esperado.split("\n"), obtido.split("\n"),
		                                  "esperado", "obtido", lineterm="", n=1):
			print("    " + linha)

print("\n%d passaram, %d falharam" % (passou, falhou))
sys.exit(1 if falhou else 0)
