"""Testa a propagação do tipo na lista de declaração SEM precisar do WebGALS:
chama as ações na mesma ordem em que o parser as chamaria. Rode: python teste_propagacao.py"""
from dataclasses import dataclass
from Semantico import Semantico

@dataclass
class T:
	lexeme: str
	position: int = 0

def rodar(seq):
	s = Semantico(propagar_tipo=True)
	for n, lex in seq: s.execute_action(n, T(lex))
	return {x.nome: x.tipo for x in s.tabela.historico}

# var a, b, c: int;
assert rodar([(41,"var"),(1,"a"),(5,","),(1,"b"),(5,","),(1,"c"),(3,"int"),(5,"int")]) == {"a":"int","b":"int","c":"int"}
print("OK: 'var a, b, c: int' tipa os tres nomes")
# var a; var b: int;   (o tipo nao contamina a declaracao anterior)
assert rodar([(41,"var"),(1,"a"),(5,";"),(41,"var"),(1,"b"),(3,"int"),(5,"int")]) == {"a":None,"b":"int"}
print("OK: o tipo nao vaza para a declaracao anterior")
# sem a acao 41 nas tabelas, a propagacao fica desligada por padrao
import Semantico as M
assert M.Semantico(propagar_tipo=False)._propaga is False
print("OK: propagacao desligavel (padrao = ligada so se as tabelas tem a acao 41)")
