"""Ferramenta de teste para a análise semântica.

Uso:
    python testar_semantica.py meu_teste.txt

Mostra: erro OU sucesso, os avisos e a tabela de símbolos. A função
`formatar` é compartilhada com rodar_regressao.py.
"""

import sys
import mensagens  # noqa: F401 -- ativa as mensagens de erro customizadas
from Lexico import Lexico
from Sintatico import Sintatico
from Semantico import Semantico
from Errors import AnalysisError


def formatar(nome: str, fonte: str, executar) -> str:
	"""`executar(sem)` deve rodar a análise usando o Semantico recebido."""
	linhas = ["--- %s ---" % nome]
	sem = Semantico(fonte)
	try:
		executar(sem)
		linhas.append("OK: compilou sem erro")
	except AnalysisError as e:
		linha = fonte.count("\n", 0, max(e.position, 0)) + 1
		linhas.append("ERRO (linha %d): %s" % (linha, e.message))

	if sem.tabela.avisos:
		linhas.append("Avisos:")
		linhas += ["  - " + a for a in sem.tabela.avisos]
	if sem.tabela.historico:
		linhas.append("Tabela de simbolos:")
		linhas += ["  " + l for l in sem.tabela.linhas_tabela()]
	return "\n".join(linhas) + "\n"


def testar(fonte: str, nome: str = "programa"):
	print(formatar(nome, fonte, lambda sem: Sintatico().parse(Lexico(fonte), sem)))


if __name__ == "__main__":
	if len(sys.argv) > 1:
		with open(sys.argv[1], encoding="utf-8") as f:
			testar(f.read(), sys.argv[1])
	else:
		print("Uso: python testar_semantica.py arquivo.txt")
